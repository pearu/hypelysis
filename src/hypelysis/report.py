#!/usr/bin/env python3
"""Run report: what was called, how long it took, what was decided.

This reports on the machinery — calls, wall time, cost, per-term outcomes. The
study's own findings live in its foundation and escalation records.

Two renderings of the same figures: the file keeps exact numbers, because it is
the record; the terminal gets aligned columns and human units, because it is
read at a glance.

Usage: python -m hypelysis.report <study-dir>     (or: hypelysis <study-dir> report)
Writes <study-dir>/RUN-REPORT.md and returns the terminal rendering.
"""
import json
import os
import sys
import textwrap
from collections import defaultdict

from . import provenance

TOKEN_KEYS = ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens")
# A term is settled when its last decision ended it; a retry means the run is
# still working on it, and counting that as settled would overstate progress.
SETTLED = ("accept", "defer", "escalate", "prerequisites")


def gather(out: str) -> dict:
    """Everything the report says, read once from the study's logs."""
    def rows(name):
        p = os.path.join(out, "log", name)
        if not os.path.exists(p):
            return []
        return [json.loads(l) for l in open(p) if l.strip()]

    calls = rows("rounds.jsonl")
    by_role = defaultdict(list)
    costs = defaultdict(float)
    toks = defaultdict(lambda: defaultdict(int))
    for c in calls:
        role = c["role"].split(":")[0]
        by_role[role].append(c["seconds"])
        m = c.get("meta") or {}
        if m.get("cost_usd"):
            costs[role] += m["cost_usd"]
        for k in TOKEN_KEYS:
            toks[role][k] += m.get(k) or 0

    outcome, attempts = {}, {}
    for d in rows("decisions.jsonl"):
        attempts[d["term"]] = d["attempt"] + 1
        outcome[d["term"]] = d["decision"]

    state = {}
    sp = os.path.join(out, "state.json")
    if os.path.exists(sp):
        state = json.load(open(sp))
    cp = os.path.join(out, "candidates.json")
    candidates = json.load(open(cp)) if os.path.exists(cp) else []
    rp = os.path.join(out, "candidates-raw.json")
    raw = json.load(open(rp)) if os.path.exists(rp) else []
    invocations = rows("invocations.jsonl")
    runs = [r for r in invocations if r.get("command") == "run"]
    latest = runs[-1] if runs else (invocations[-1] if invocations else None)
    return {"study": out, "machine_choices": state.get("machine_choices") or [],
            "candidates": candidates, "raw_candidates": len(raw),
            "queued": len(state.get("queue_lane1") or []) + len(state.get("queue_lane2") or []),
            "phase": state.get("phase"),
            "calls": calls, "by_role": by_role, "costs": costs,
            "toks": toks, "outcome": outcome, "attempts": attempts,
            "code": latest, "settings": (latest or {}).get("settings") or {},
            "versions": {provenance.describe(r) for r in runs}}


def _tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _dur(s: float) -> str:
    if s >= 3600:
        return f"{s / 3600:.1f}h"
    if s >= 120:
        return f"{s / 60:.0f}m"
    return f"{s:.0f}s"


def _setting(v):
    """A models map reads better as role:model pairs than as a dict repr."""
    if isinstance(v, dict):
        return " ".join(f"{k}:{x}" for k, x in v.items())
    return v


def _terms(data: dict) -> str:
    """What the study is working through: how many terms it found, how far it
    has got, and what is left."""
    cands = data["candidates"]
    bits = []
    if cands:
        mech = sum(1 for c in cands if c.get("lane") != "people")
        found = f"{len(cands)} candidates ({mech} mechanism, {len(cands) - mech} people)"
        if data["raw_candidates"] and data["raw_candidates"] != len(cands):
            found += f", merged from {data['raw_candidates']} raw"
        bits.append(found)
    tally = defaultdict(int)
    for v in data["outcome"].values():
        tally[v] += 1
    settled = {k: v for k, v in tally.items() if k in SETTLED}
    if settled:
        bits.append(f"{sum(settled.values())} settled (" +
                    ", ".join(f"{v} {k}" for k, v in sorted(settled.items())) + ")")
    in_flight = sum(v for k, v in tally.items() if k not in SETTLED)
    if in_flight:
        bits.append(f"{in_flight} in progress")
    if data["queued"]:
        bits.append(f"{data['queued']} still queued")
    elif cands and data["outcome"]:
        bits.append("queue empty")
    return "; ".join(bits)


def _table(headers, rows, aligns=None, indent="  ") -> list:
    """Columns wide enough for their content, numbers to the right."""
    if not rows:
        return []
    aligns = aligns or ["<"] + [">"] * (len(headers) - 1)
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows))
              for i, h in enumerate(headers)]
    def line(cells):
        return (indent + "  ".join(f"{str(c):{a}{w}}" for c, a, w
                                   in zip(cells, aligns, widths))).rstrip()
    return [line(headers)] + [line(r) for r in rows]


def text(data: dict) -> str:
    """The terminal rendering: aligned, human units."""
    lines = [f"Run report — {data['study']}"]
    if data["code"] or data["settings"]:
        lines.append("")
    if data["code"]:
        lines.append(f"code      {provenance.describe(data['code'])}")
    if data["settings"]:
        s = ", ".join(f"{k}={_setting(v)}" for k, v in data["settings"].items())
        lines += textwrap.wrap(s, width=76, initial_indent="settings  ",
                               subsequent_indent="          ")
    if data["candidates"] or data["outcome"]:
        lines.append(f"terms     {_terms(data)}")
    if len(data["versions"]) > 1:
        lines += ["", f"WARNING: advanced by {len(data['versions'])} different versions "
                  "of the code;", "         see log/invocations.jsonl before comparing "
                  "these numbers", "         with another study's."]

    rows, tot_s, tot_cost = [], 0.0, 0.0
    tot_tok = defaultdict(int)
    for role, secs in sorted(data["by_role"].items()):
        t = data["toks"][role]
        tot_s += sum(secs)
        tot_cost += data["costs"].get(role, 0.0)
        for k in TOKEN_KEYS:
            tot_tok[k] += t[k]
        rows.append([role, len(secs), _dur(sum(secs)), _dur(sum(secs) / len(secs)),
                     _dur(max(secs)), _tokens(t["output_tokens"]),
                     _tokens(t["cache_write_tokens"]), _tokens(t["cache_read_tokens"]),
                     f"${data['costs'].get(role, 0.0):.2f}"])
    if rows:
        rows.append(["all", len(data["calls"]), _dur(tot_s),
                     _dur(tot_s / max(len(data["calls"]), 1)), "",
                     _tokens(tot_tok["output_tokens"]),
                     _tokens(tot_tok["cache_write_tokens"]),
                     _tokens(tot_tok["cache_read_tokens"]), f"${tot_cost:.2f}"])
        lines += ["", "worker calls"]
        body = _table(["role", "calls", "total", "mean", "max", "out tok",
                       "cache-w", "cache-r", "cost"], rows)
        lines += body[:-1] + ["  " + "-" * (len(body[0]) - 2), body[-1]]

    unowned = [m for m in data["machine_choices"] if m["mode"] == "machine-selected"]
    if unowned:
        lines += ["", f"WARNING: {len(unowned)} owner-level choice(s) were made by the "
                  "run itself,", "         not by the study owner (--keep-going); see "
                  "adjudications.md:"]
        lines += [f"           {m['term']}: {m['chosen'][:60]}" for m in unowned]
    if data["outcome"]:
        tally = defaultdict(int)
        for v in data["outcome"].values():
            tally[v] += 1
        lines += ["", f"decisions — {len(data['outcome'])} terms: " +
                  ", ".join(f"{v} {k}" for k, v in sorted(tally.items()))]
        lines += _table(["term", "attempts", "outcome"],
                        [[t, data["attempts"][t], data["outcome"][t]]
                         for t in data["outcome"]],
                        aligns=["<", ">", "<"])
    return "\n".join(lines) + "\n"


def markdown(data: dict) -> str:
    """The file rendering: exact numbers, kept as the record."""
    lines = ["# Run report", "", f"Study: `{data['study']}`"]
    if data["code"]:
        lines += ["", f"Code: {provenance.describe(data['code'])}"]
    if data["settings"]:
        lines.append("Settings: " + ", ".join(f"{k}={v}" for k, v in data["settings"].items()))
    if data["candidates"] or data["outcome"]:
        lines.append(f"Terms: {_terms(data)}")
    if len(data["versions"]) > 1:
        lines += ["", f"**This study was advanced by {len(data['versions'])} different "
                  "versions of the code**; see log/invocations.jsonl before comparing its "
                  "numbers with another study's."]
    unowned = [m for m in data["machine_choices"] if m["mode"] == "machine-selected"]
    if unowned:
        lines += ["", f"**{len(unowned)} owner-level choice(s) in this study were made by "
                  "the run, not by its owner** (`--keep-going`); see adjudications.md.", ""]
        for m in unowned:
            lines.append(f"- {m['term']}: {m['chosen']}")
    lines += ["", "## Worker calls", "",
              "| role | calls | total s | mean s | max s | out tok | cache-w | cache-r | cost $ |",
              "|---|---|---|---|---|---|---|---|---|"]
    total, total_cost = 0.0, 0.0
    for role, secs in sorted(data["by_role"].items()):
        total += sum(secs)
        total_cost += data["costs"].get(role, 0.0)
        t = data["toks"][role]
        lines.append(f"| {role} | {len(secs)} | {sum(secs):.0f} | "
                     f"{sum(secs)/len(secs):.0f} | {max(secs):.0f} | {t['output_tokens']} | "
                     f"{t['cache_write_tokens']} | {t['cache_read_tokens']} | "
                     f"{data['costs'].get(role, 0.0):.2f} |")
    lines += ["", f"**{len(data['calls'])} calls, {total:.0f}s total worker time, "
              f"${total_cost:.2f} recorded cost.**", ""]
    if data["outcome"]:
        counts = defaultdict(int)
        for v in data["outcome"].values():
            counts[v] += 1
        lines += ["## Decisions", "",
                  f"terms processed: {len(data['outcome'])} — " +
                  ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())), "",
                  "| term | attempts | outcome |", "|---|---|---|"]
        for t in data["outcome"]:
            lines.append(f"| {t} | {data['attempts'][t]} | {data['outcome'][t]} |")
        lines.append("")
    return "\n".join(lines)


def build(out: str) -> str:
    """Write RUN-REPORT.md and return the terminal rendering."""
    data = gather(out)
    open(os.path.join(out, "RUN-REPORT.md"), "w").write(markdown(data))
    return text(data)


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print(__doc__)
        return 2
    print(build(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

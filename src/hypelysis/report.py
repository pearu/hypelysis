#!/usr/bin/env python3
"""Run report: what was called, how long it took, what was decided.

This reports on the machinery — calls, wall time, cost, per-term outcomes. The
study's own findings live in its foundation and escalation records.

Usage: python -m hypelysis.report <study-dir>     (or: hypelysis <study-dir> report)
Writes <study-dir>/RUN-REPORT.md and returns it.
"""
import json
import os
import sys
from collections import defaultdict

from . import provenance


def build(out: str) -> str:
    def rows(name):
        p = os.path.join(out, "log", name)
        if not os.path.exists(p):
            return []
        return [json.loads(l) for l in open(p) if l.strip()]

    calls = rows("rounds.jsonl")
    decisions = rows("decisions.jsonl")

    by_role = defaultdict(list)
    for c in calls:
        by_role[c["role"].split(":")[0]].append(c["seconds"])

    costs = defaultdict(float)
    toks = defaultdict(lambda: defaultdict(int))
    for c in calls:
        m = c.get("meta") or {}
        r = c["role"].split(":")[0]
        if m.get("cost_usd"):
            costs[r] += m["cost_usd"]
        for k in ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens"):
            toks[r][k] += m.get(k) or 0
    invocations = rows("invocations.jsonl")
    lines = ["# Run report", "", f"Study: `{out}`"]
    if invocations:
        runs = [r for r in invocations if r.get("command") == "run"]
        lines += ["", f"Code: {provenance.describe(runs[-1] if runs else invocations[-1])}"]
        settings = (runs[-1] if runs else invocations[-1]).get("settings") or {}
        if settings:
            lines.append("Settings: " + ", ".join(f"{k}={v}" for k, v in settings.items()))
        codes = {provenance.describe(r) for r in runs}
        if len(codes) > 1:
            lines += ["", f"**This study was advanced by {len(codes)} different versions of "
                      "the code**; see log/invocations.jsonl before comparing its numbers "
                      "with another study's."]
    lines += ["", "## Worker calls", "",
             "| role | calls | total s | mean s | max s | out tok | cache-w | cache-r | cost $ |",
             "|---|---|---|---|---|---|---|---|---|"]
    total, total_cost = 0.0, 0.0
    for role, secs in sorted(by_role.items()):
        total += sum(secs)
        total_cost += costs.get(role, 0.0)
        t = toks[role]
        lines.append(f"| {role} | {len(secs)} | {sum(secs):.0f} | "
                     f"{sum(secs)/len(secs):.0f} | {max(secs):.0f} | {t['output_tokens']} | "
                     f"{t['cache_write_tokens']} | {t['cache_read_tokens']} | {costs.get(role, 0.0):.2f} |")
    lines += ["", f"**{len(calls)} calls, {total:.0f}s total worker time, "
              f"${total_cost:.2f} recorded cost.**", ""]

    if decisions:
        outcome = defaultdict(int)
        attempts = defaultdict(int)
        for d in decisions:
            attempts[d["term"]] = d["attempt"] + 1
            outcome[d["term"]] = d["decision"]
        counts = defaultdict(int)
        for v in outcome.values():
            counts[v] += 1
        lines += ["## Decisions", "",
                  f"terms processed: {len(outcome)} — " +
                  ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())), "",
                  "| term | attempts | outcome |", "|---|---|---|"]
        for t in outcome:
            lines.append(f"| {t} | {attempts[t]} | {outcome[t]} |")
        lines.append("")

    report = "\n".join(lines)
    open(os.path.join(out, "RUN-REPORT.md"), "w").write(report)
    return report


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print(__doc__)
        return 2
    print(build(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

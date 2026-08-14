#!/usr/bin/env python3
"""Run report: what was called, how long it took, what was decided.

Usage: python3 pipeline/runreport.py <study-out-dir>
Writes <study-out-dir>/RUN-REPORT.md and prints it.
"""
import json
import os
import sys
from collections import defaultdict

out = sys.argv[1]


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
lines = ["# Run report", "", f"Study: `{out}`", "", "## Worker calls", "",
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
print(report)

#!/usr/bin/env python3
"""Mechanical checks on a foundation file (the pipeline's own, per rulebook.md).

Usage: check.py <foundation.md>   or   check.py -   (stdin)
Exit 0 iff clean; violations on stdout, one per line.
"""
import re
import sys

text = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
problems = []
entries = re.split(r'^### ', text, flags=re.M)[1:]
seen = []
for block in entries:
    name = block.splitlines()[0].strip()
    order = ["Kind", "Given", "Statement", "Because", "Uses", "Notation", "Note"]
    found = re.findall(r'^(Kind|Given|Statement|Because|Uses|Notation|Note):', block, re.M)
    if found != sorted(found, key=order.index):
        problems.append(f"{name}: field order {found}")
    fields = dict(re.findall(r'^(Kind|Given|Statement|Because|Uses|Notation|Note): ?(.*(?:\n(?![A-Z#]).*)*)',
                             block, re.M))
    kind = fields.get("Kind", "").strip()
    if kind not in ("base", "defined"):
        problems.append(f"{name}: Kind must be base|defined, got {kind!r}")
    if not fields.get("Statement", "").strip():
        problems.append(f"{name}: missing Statement")
    if kind == "base" and not fields.get("Because", "").strip():
        problems.append(f"{name}: base entry missing Because")
    if kind == "defined":
        uses = fields.get("Uses", "").strip()
        if not uses:
            problems.append(f"{name}: defined entry missing Uses")
        elif uses.lower() != "everyday language only":
            for u in [x.strip() for x in uses.split(",")]:
                if u and u not in seen:
                    problems.append(f"{name}: uses {u!r}, which is not an earlier entry")
    if name in seen:
        problems.append(f"{name}: duplicate entry")
    seen.append(name)
print("\n".join(problems))
sys.exit(1 if problems else 0)

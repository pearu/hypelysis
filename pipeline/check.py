#!/usr/bin/env python3
"""Mechanical checks on a foundation file (the pipeline's own, per rulebook.md).

Usage: check.py <foundation.md> [--note-cap N]   or   check.py - [--note-cap N]
Exit 0 iff clean; violations on stdout, one per line.
--note-cap N: a Note longer than N sentences is a violation (bloat guard).
"""
import re
import sys

note_cap = None
if "--note-cap" in sys.argv:
    i = sys.argv.index("--note-cap")
    note_cap = int(sys.argv[i + 1])
    del sys.argv[i:i + 2]
text = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
problems = []
entries = re.split(r'^### ', text, flags=re.M)[1:]
seen = []
for block in entries:
    name = block.splitlines()[0].strip()
    order = ["Kind", "Given", "Statement", "Because", "Uses", "Notation",
             "Defers", "Open", "Finding", "Note"]
    found = re.findall(r'^(Kind|Given|Statement|Because|Uses|Notation|Open|Defers|Finding|Note):',
                       block, re.M)
    if found != sorted(found, key=order.index):
        problems.append(f"{name}: field order {found} — required order {order}")
    fields = dict(re.findall(r'^(Kind|Given|Statement|Because|Uses|Notation|Open|Defers|Finding|Note):'
                             r' ?(.*(?:\n(?![A-Z#]).*)*)',
                             block, re.M))
    kind = fields.get("Kind", "").strip()
    if kind not in ("base", "defined"):
        problems.append(f"{name}: Kind must be base|defined, got {kind!r}")
    stmt = fields.get("Statement", "").strip()
    if not stmt:
        problems.append(f"{name}: missing Statement")
    elif len(re.findall(r'[.!?](?:\s|$)', stmt)) > 3:
        problems.append(f"{name}: Statement exceeds three sentences")
    note = fields.get("Note", "").strip()
    if note_cap and len(re.findall(r'[.!?](?:\s|$)', note)) > note_cap:
        problems.append(f"{name}: Note exceeds {note_cap} sentences — keep only "
                        "normative declarations (openness, semantics); move "
                        "commentary and author-facing findings out of the entry")
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

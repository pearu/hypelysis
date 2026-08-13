#!/usr/bin/env python3
"""Verify the pipeline's worker-visible texts carry no vocabulary from the
subject document or from the manual study — the independence contract.

Scans rulebook.md and roles/*.md against a banned-term list. The list may be
built by reading the manual study; the scanned files must never contain it.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BANNED = [
    # the subject document's coinages
    "frame", "cog", "op", "guard", "gate", "track", "intelligence hub",
    "nebari", "nebi", "organizational memory", "validation strategy",
    "accountability plane", "marketplace",
    # the manual study's coinages
    "alphabet", "tokenizer", "token", "scoring", "sampler", "assembly",
    "model step", "model run", "checked run", "run specification",
    "check specification", "attribution", "succession", "provenance",
    "binding", "carrier", "organisational ledger", "primitive",
]
hits = []
for path in [os.path.join(HERE, "rulebook.md")] + sorted(glob.glob(os.path.join(HERE, "roles/*.md"))):
    low = open(path).read().lower()
    for term in BANNED:
        if re.search(rf'\b{re.escape(term)}\b', low):
            hits.append(f"{os.path.basename(path)}: {term!r}")
print("\n".join(sorted(set(hits))) or "leakage check: clean")
sys.exit(1 if hits else 0)

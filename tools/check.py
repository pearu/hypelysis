#!/usr/bin/env python3
"""Integrity checker for a hypelysis study — every mechanical guarantee in one place.

Usage:  python3 tools/check.py [study-dir]        (default: studies/inthub-whitepaper)

Checks, per RULES.md:
  citations     every Xn[term] bracket anywhere in the study matches its ledger's heading
  numbering     each prefix's entries are numbered 1..n with no gap
  field-order   entry fields appear in the RULES.md entry-format order
  forward-refs  no core field (Given/Definition/Notation/Depends) cites a later entry
  bridge        the one-way rule: no companion citations in the base ledger
  coverage      every base-ledger entry is cited in its Examples section, if one exists
  history       the translation carries no journey-narrative phrasing
Exit code 0 iff everything passes.
"""
import re
import sys
import os

STUDY = sys.argv[1] if len(sys.argv) > 1 else 'studies/inthub-whitepaper'
BASE, COMPANION = 'definitions.md', 'organisational-definitions.md'
BASE_KINDS, COMP_KINDS = 'PD', 'QO'
TRANSLATION = 'whitepaper-translation.md'
FIELD_ORDER = ['Assumed meaning', 'Why left undefined', 'Given', 'Definition',
               'Notation', 'Depends on', 'Added', 'Also called', 'Notes']
HISTORY_PHRASES = ['now defined', 'no longer', 'since this section', 'have all closed',
                   'now mostly', 'now statable', 'extension recorded', 'names now',
                   'first written', 'demoted', 'was withdrawn']

failures = []


def fail(msg):
    failures.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg):
    print(f"  ok    {msg}")


def read(name):
    path = os.path.join(STUDY, name)
    return open(path).read() if os.path.exists(path) else None


def headings(text, kinds):
    return {f"{k}{n}": t.strip()
            for k, n, t in re.findall(rf'^### ([{kinds}])(\d+) — (.+)$', text, re.M)}


base, comp = read(BASE), read(COMPANION)
terms = dict(headings(base, BASE_KINDS))
if comp:
    terms.update(headings(comp, COMP_KINDS))

# citations — scan every markdown file in the study
for name in sorted(os.listdir(STUDY)):
    if not name.endswith('.md'):
        continue
    text = read(name)
    bad = [f"{k}{n}[{t}]" for k, n, t in
           re.findall(r'\b([PDQO])(\d+)\[([^\]]+)\]', text)
           if terms.get(f"{k}{n}") != t]
    if bad:
        fail(f"{name}: stale citations {bad}")
else:
    if not any('stale citations' in f for f in failures):
        ok("citations: every bracket matches its heading, across all study files")

# numbering
for text, kinds in ((base, BASE_KINDS), (comp, COMP_KINDS)):
    if text is None:
        continue
    for kind in kinds:
        nums = sorted(int(n) for k, n, _ in
                      re.findall(rf'^### ({kind})(\d+) — (.+)$', text, re.M))
        if nums != list(range(1, len(nums) + 1)):
            fail(f"{kind}-numbering not contiguous: {nums}")
        else:
            ok(f"numbering: {kind}1..{kind}{len(nums)} contiguous")

# field order and forward references
for text, kinds, label in ((base, BASE_KINDS, BASE), (comp, COMP_KINDS, COMPANION)):
    if text is None:
        continue
    for block in re.split(r'^### ', text, flags=re.M)[1:]:
        m = re.match(rf'([{kinds}])(\d+) — ', block)
        if not m:
            continue
        eid = m.group(1) + m.group(2)
        fields = [f for f in re.findall(r'^\*\*([A-Za-z ]+)\.\*\*', block, re.M)
                  if f in FIELD_ORDER]
        if fields != sorted(fields, key=FIELD_ORDER.index):
            fail(f"{eid}: field order {fields}")
        if m.group(1) in 'DO':  # definitions only — primitives have no deps
            core = block.split('**Also called.**')[0].split('**Notes.**')[0]
            core = core[core.index('\n'):]
            for k, n in re.findall(rf'\b([{kinds}])(\d+)\[', core):
                if k == m.group(1) and int(n) >= int(m.group(2)):
                    fail(f"{eid}: forward reference to {k}{n} in a core field")
ok("field order and forward references checked")

# one-way bridge
if comp:
    rev = re.findall(rf'\b([{COMP_KINDS}])(\d+)\[', base)
    if rev:
        fail(f"bridge violated: companion citations in {BASE}: {rev}")
    else:
        ok("bridge: one-way, no companion citations in the base ledger")

# Examples coverage
if '## Examples' in base:
    ex = base[base.index('## Examples'):]
    for stop in ('## Figure', '## Revision log'):
        if stop in ex:
            ex = ex[:ex.index(stop)]
    missing = [f"{k}[{t}]" for k, t in headings(base, BASE_KINDS).items()
               if not re.search(rf'\b{k}\[', ex)]
    if missing:
        fail(f"Examples coverage gaps: {missing}")
    else:
        ok("Examples: every base-ledger entry materialized")

# history phrasing in the translation
tr = read(TRANSLATION)
if tr:
    hits = [p for p in HISTORY_PHRASES if p in tr.lower()]
    if hits:
        fail(f"{TRANSLATION}: journey-narrative phrasing {hits}")
    else:
        ok("translation: no journey-narrative phrasing")

print(f"\n{'FAILED: ' + str(len(failures)) + ' problem(s)' if failures else 'PASS: all checks clean'}")
sys.exit(1 if failures else 0)

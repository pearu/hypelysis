#!/usr/bin/env python3
"""Render a study's theory as graphs — parsed from the ledgers, never drawn by hand.

Two SVGs, written into the study directory, regenerated so they cannot go stale:

  theory-graph.svg   every entry of both ledgers, edges = declared Depends-on;
                     the one-way bridge shown as dashed edges into the base ledger
  paper-map.svg      the source document's vocabulary mapped onto both ledgers,
                     parsed from the translation's dictionary table

Usage:  python3 tools/make_graphs.py [study-dir]     (default: studies/inthub-whitepaper)
"""
import re
import os
import sys

STUDY = sys.argv[1] if len(sys.argv) > 1 else 'studies/inthub-whitepaper'

def spath(name):
    return os.path.join(STUDY, name)

NAVY, TEAL, LIGHT, INK = "#1b2a4a", "#0e7c7b", "#d5e8f0", "#222222"
MUTED, PAPER = "#6b7280", "#8a6d1f"
SANS = "DejaVu Sans,Helvetica,sans-serif"

# ---------------------------------------------------------------- parsing
def parse_ledger(path, kinds):
    entries = {}
    text = open(path).read()
    for block in re.split(r'^### ', text, flags=re.M)[1:]:
        m = re.match(rf'([{kinds}])(\d+) — (.+)', block)
        if not m:
            continue
        eid = m.group(1) + m.group(2)
        dep_m = re.search(r'\*\*Depends on\.\*\*(.*?)(?=\n\*\*|\Z)', block, re.S)
        deps = re.findall(r'\b([PDQO]\d+)\[', dep_m.group(1)) if dep_m else []
        entries[eid] = dict(term=m.group(3).strip(), deps=deps,
                            kind=m.group(1), num=int(m.group(2)))
    return entries

MECH = parse_ledger(spath('definitions.md'), 'PD')
ORG  = parse_ledger(spath('organisational-definitions.md'), 'QO')
ALL  = {**MECH, **ORG}

def depth(eid, seen=()):
    e = ALL[eid]
    local = [d for d in e['deps'] if d in ALL]
    if not local:
        return 0
    return 1 + max(depth(d) for d in local)

# ---------------------------------------------------------------- svg bits
def fit(s, maxw, size, min_size=7.5):
    while len(s) * size * 0.52 > maxw and size > min_size:
        size -= 0.5
    return size

class SVG:
    def __init__(self):
        self.parts, self.defs = [], set()
    def marker(self, colour):
        self.defs.add(colour)
        return f"url(#m{colour[1:]})"
    def text(self, x, y, s, size=11, fill=INK, anchor="middle", weight="normal"):
        self.parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}">{s}</text>')
    def node(self, x, y, w, h, eid, term, kind):
        filled = kind in 'PQ'
        colour = NAVY if kind in 'PD' else TEAL
        fill, fg = (colour, 'white') if filled else ('white', colour)
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" '
            f'fill="{fill}" stroke="{colour}" stroke-width="1.6"/>')
        self.text(x + w/2, y + 13, eid, 9.5, fg, weight="bold")
        self.text(x + w/2, y + h - 8, term, fit(term, w - 10, 10), fg)
    def edge(self, x1, y1, x2, y2, colour, width=1.1, dash=None, opacity=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{colour}" stroke-width="{width}" opacity="{opacity}"{d} '
            f'marker-end="{self.marker(colour)}"/>')
    def write(self, path, w, h, title):
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
                f'width="{w}" height="{h}">', '<defs>']
        for c in self.defs:
            head.append(f'<marker id="m{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
        head += ['</defs>', f'<rect width="{w}" height="{h}" fill="white"/>',
                 f'<text x="{w/2}" y="26" text-anchor="middle" font-family="{SANS}" '
                 f'font-size="16" font-weight="bold" fill="{NAVY}">{title}</text>']
        open(path, 'w').write('\n'.join(head + self.parts) + '\n</svg>\n')
        print(f"wrote {path}")

# ---------------------------------------------------------------- graph 1
BW, BH, PITCH, VGAP = 128, 32, 178, 62

def column_layout(entries, x0, top):
    cols = {}
    for eid in entries:
        cols.setdefault(depth(eid), []).append(eid)
    pos = {}
    for d, ids in sorted(cols.items()):
        ids.sort(key=lambda e: (ALL[e]['kind'], ALL[e]['num']))
        for i, eid in enumerate(ids):
            pos[eid] = (x0 + d * PITCH, top + i * VGAP)
    return pos

# organisational on top, the machinery beneath it: the bridge edges point down
# into what the upper ledger is built on.
svg = SVG()
ORG_TOP = 84
org_pos = column_layout(ORG, 50, ORG_TOP)
MECH_TOP = max(y for _, y in org_pos.values()) + BH + 96
mech_pos = column_layout(MECH, 50, MECH_TOP)
pos = {**mech_pos, **org_pos}

svg.text(50, ORG_TOP - 20, "organisational-definitions.md — persons, obligations, history",
         12.5, TEAL, anchor="start", weight="bold")
svg.text(50, MECH_TOP - 20, "definitions.md — the machinery",
         12.5, NAVY, anchor="start", weight="bold")

for eid, e in ALL.items():
    x, y = pos[eid]
    for dep in e['deps']:
        if dep not in pos:
            continue
        dx, dy = pos[dep]
        if eid in ORG and dep in MECH:            # the one-way bridge, downward
            svg.edge(x + BW/2, y + BH, dx + BW/2, dy - 3, TEAL,
                     width=1.1, dash="5,4", opacity=0.55)
        else:
            into_p = ALL[dep]['kind'] in 'PQ'
            colour = TEAL if eid in ORG else NAVY
            svg.edge(x, y + BH/2, dx + BW + 3, dy + BH/2, colour,
                     width=0.9 if into_p else 1.3,
                     opacity=0.25 if into_p else 0.8)
for eid, e in ALL.items():
    x, y = pos[eid]
    svg.node(x, y, BW, BH, eid, e['term'], e['kind'])

H1 = max(y for _, y in pos.values()) + BH + 58
W1 = max(x for x, _ in pos.values()) + BW + 60
svg.text(50, H1 - 16, "filled = primitive · outlined = definition · dashed = the one-way "
         "bridge, pointing down into what the upper ledger is built on · edges point at "
         "what an entry depends on", 10.5, MUTED, anchor="start")
svg.write(spath("theory-graph.svg"), W1, H1, "The two ledgers, by declared dependency")

# ---------------------------------------------------------------- graph 2
tr = open(spath('whitepaper-translation.md')).read()
dict_txt = tr[tr.index('## 1. The dictionary'):]
dict_txt = dict_txt[:dict_txt.index('\n---')]
SUPPLEMENT = {'context': ['D2']}
rows = []
for line in dict_txt.splitlines():
    if not line.startswith('| ') or line.startswith('| :') or line.startswith('| the paper'):
        continue
    cells = [c.strip() for c in line.strip('|').split('|')]
    term = re.sub(r'\s*\(.*?\)\s*', ' ', cells[0]).strip().strip('"')
    cited = re.findall(r'\b([PDQO]\d+)\b', line)
    cited = [c for c in dict.fromkeys(cited) if c in ALL]
    for key, extra in SUPPLEMENT.items():
        if cells[0].startswith(key):
            cited += extra
    rows.append((term, cited))

svg2 = SVG()
RY, RH = 64, 44
mech_cited = list(dict.fromkeys(c for _, cs in rows for c in cs if c in MECH))
org_cited  = list(dict.fromkeys(c for _, cs in rows for c in cs if c in ORG))
PX, MX, OX = 60, 560, 900
svg2.text(PX, 50, "the whitepaper says", 12, PAPER, anchor="start", weight="bold")
svg2.text(MX, 50, "mechanical", 12, NAVY, anchor="start", weight="bold")
svg2.text(OX, 50, "organisational", 12, TEAL, anchor="start", weight="bold")

tpos = {}
for i, (term, _) in enumerate(rows):
    y = RY + i * RH
    tpos[term] = y
    svg2.parts.append(f'<rect x="{PX}" y="{y}" width="230" height="30" rx="15" '
        f'fill="#faf6e9" stroke="{PAPER}" stroke-width="1.4"/>')
    svg2.text(PX + 115, y + 19, term, fit(term, 214, 11.5), PAPER)

def entry_col(cited, x, colour):
    epos = {}
    n = len(cited)
    total = len(rows) * RH
    for i, c in enumerate(cited):
        y = RY + i * (total - 30) / max(n - 1, 1)
        epos[c] = y
        svg2.node(x, y, BW, BH, c, ALL[c]['term'], ALL[c]['kind'])
    return epos

mpos = entry_col(mech_cited, MX, NAVY)
opos = entry_col(org_cited, OX, TEAL)
edges = 0
for term, cs in rows:
    if not cs:
        svg2.text(PX + 300, tpos[term] + 19, "outside both ledgers", 10, MUTED, anchor="start")
        continue
    for c in cs:
        col, colour = (mpos, NAVY) if c in mpos else (opos, TEAL)
        x2 = MX if c in mpos else OX
        svg2.edge(PX + 292, tpos[term] + 15, x2 - 4, col[c] + BH/2, colour,
                  width=1.0, opacity=0.5)
        edges += 1
H2 = RY + len(rows) * RH + 40
svg2.write(spath("paper-map.svg"), 1120, H2, "The whitepaper's vocabulary, mapped onto the theory")
print(f"graph 1: {len(ALL)} entries, {sum(len(e['deps']) for e in ALL.values())} edges | "
      f"graph 2: {len(rows)} paper terms, {len(mech_cited)}+{len(org_cited)} entries, {edges} edges")

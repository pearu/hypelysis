#!/usr/bin/env python3
"""Generate study/concept-map.svg — how the whitepaper's concepts relate.

The paper's two figures show the layer stack and the validation lifecycle.
Neither shows what connects to what, nor what crosses the Hub perimeter.
This one is organised around the boundary, because that is where the
architecture's central claim — sovereignty — is actually decided.

Three crossings are drawn, and they are not equivalent:
  * artifacts   Frames/Cogs/Ops/Guards, both ways, packaged by Nebi
  * evidence    Tracks never; anonymized aggregates may (S6.1)
  * inference   a `kind: context` Cog sends context out on every call (S4.4)

Palette matches tools/make_diagrams.py. No dependencies; emits SVG so it
stays vector-sharp in the PDF (WeasyPrint renders SVG natively).
"""

NAVY, TEAL, LIGHT, INK = "#1b2a4a", "#0e7c7b", "#d5e8f0", "#222222"
MUTED, RED, AMBER = "#6b7280", "#a03232", "#b45309"

W, H = 1180, 790
NW, NH = 168, 58
SANS = "DejaVu Sans,Helvetica,sans-serif"

out = []
def add(s): out.append(s)

def txt(x, y, s, size=13, fill=INK, anchor="middle", weight="normal", style="normal"):
    add(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{SANS}" '
        f'font-size="{size}" font-weight="{weight}" font-style="{style}" fill="{fill}">{s}</text>')

def node(x, y, label, sub=None, size=20):
    add(f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="9" fill="{LIGHT}" '
        f'stroke="{NAVY}" stroke-width="2.5"/>')
    txt(x+NW/2, y+NH/2+(0 if sub is None else -1), label, size, NAVY, weight="bold")
    if sub:
        txt(x+NW/2, y+NH/2+18, sub, 12.5, INK)

def arrow(x1, y1, x2, y2, colour=TEAL, dash=None, width=2.5, both=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    st = f' marker-start="url(#a{colour[1:]})"' if both else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
        f'stroke-width="{width}"{d} marker-end="url(#a{colour[1:]})"{st}/>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add('<defs>')
for c in (TEAL, NAVY, RED, AMBER, MUTED):
    add(f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
add('</defs>')
add(f'<rect width="{W}" height="{H}" fill="white"/>')

# ---- external model endpoint, above the Hub -----------------------------
add(f'<rect x="292" y="24" width="270" height="76" rx="10" fill="#fff7ed" '
    f'stroke="{AMBER}" stroke-width="2.5"/>')
txt(427, 54, "External model API", 17, AMBER, weight="bold")
txt(427, 78, "someone else&#8217;s infrastructure", 12.5, AMBER)

# ---- Hub boundary -------------------------------------------------------
add(f'<rect x="35" y="150" width="820" height="560" rx="16" fill="none" '
    f'stroke="{NAVY}" stroke-width="3" stroke-dasharray="10,7"/>')
txt(55, 180, "INTELLIGENCE HUB", 17, NAVY, anchor="start", weight="bold")
txt(55, 200, "your infrastructure, your governance perimeter", 13, MUTED, anchor="start")

FX, FY = 70, 266
CX, CY = 330, 266
OX, OY = 590, 266
GX, GY = 590, 396
TX, TY = 590, 526
KX, KY = 330, 526
MX, MY = 70, 526

# ---- agent bracket ------------------------------------------------------
add(f'<rect x="{CX-14}" y="{CY-18}" width="{OX+NW+14-(CX-14)}" height="{NH+36}" rx="10" '
    f'fill="none" stroke="{TEAL}" stroke-width="2" stroke-dasharray="5,5"/>')
txt(CX+(OX+NW-CX)/2, CY-32,
    'an <tspan font-weight="bold">agent</tspan> = a Cog engaged through an Op, '
    'given identity and memory by the Hub', 13.5, TEAL, style="italic")

node(FX, FY, "Frame", "context, owned")
node(CX, CY, "Cog", "the AI worker")
node(OX, OY, "Op", "the workflow")
node(GX, GY, "Guard", "checks")
node(TX, TY, "Gate", "decides")
node(KX, KY, "Track", "the evidence")
node(MX, MY, "Organizational", "Memory", size=15)

# ---- work path and accountability loop ----------------------------------
arrow(FX+NW, FY+NH/2, CX-6, CY+NH/2);   txt((FX+NW+CX)/2, FY+NH/2-9, "orients", 13, TEAL)
arrow(CX+NW, CY+NH/2, OX-6, OY+NH/2);   txt((CX+NW+OX)/2, CY+NH/2-9, "used by", 13, TEAL)
arrow(OX+NW/2, OY+NH, GX+NW/2, GY-6);   txt(OX+NW/2+52, OY+NH+32, "declares", 13, TEAL)
arrow(GX+NW/2, GY+NH, TX+NW/2, TY-6);   txt(GX+NW/2+42, GY+NH+32, "verdict", 13, TEAL)
arrow(TX-6, TY+NH/2, KX+NW+6, KY+NH/2); txt((TX+KX+NW)/2, TY+NH/2-9, "recorded in", 13, TEAL)
arrow(KX-6, KY+NH/2, MX+NW+6, MY+NH/2); txt((KX+MX+NW)/2, KY+NH/2-9, "feeds", 13, TEAL)
arrow(MX+NW/2, MY-6, FX+NW/2, FY+NH+6); txt(MX+NW/2-52, (MY+FY+NH)/2, "improves", 13, TEAL)

# ---- CROSSING 1: inference ----------------------------------------------
arrow(CX+NW/2, CY-52, 427, 106, colour=AMBER, dash="7,5", both=True)
txt(600, 138, 'if the Cog is <tspan font-weight="bold">kind: context</tspan>, '
    'your context crosses on every call', 13, AMBER, anchor="start")

# ---- CROSSING 2: artifacts ----------------------------------------------
add(f'<rect x="975" y="286" width="200" height="180" rx="12" fill="{NAVY}"/>')
txt(1075, 364, "MARKETPLACE", 20, "white", weight="bold")
txt(1075, 392, "other Hubs", 13, LIGHT)
arrow(862, 352, 970, 352, colour=NAVY)
arrow(970, 390, 862, 390, colour=NAVY)
txt(916, 333, "Frames &#183; Cogs", 12.5, NAVY)
txt(916, 420, "Ops &#183; Guards", 12.5, NAVY)
txt(1075, 488, "packaged and moved by Nebi", 12.5, MUTED, style="italic")

# ---- CROSSING 3: evidence — blocked, except aggregates ------------------
add(f'<line x1="{KX+NW/2}" y1="{KY+NH}" x2="{KX+NW/2}" y2="676" stroke="{RED}" '
    f'stroke-width="2.5" stroke-dasharray="6,5"/>')
add(f'<line x1="{KX+NW/2-17}" y1="652" x2="{KX+NW/2+17}" y2="686" stroke="{RED}" stroke-width="3.5"/>')
add(f'<line x1="{KX+NW/2+17}" y1="652" x2="{KX+NW/2-17}" y2="686" stroke="{RED}" stroke-width="3.5"/>')
txt(KX+NW/2+36, 675, "Tracks never leave the Hub", 13.5, RED, anchor="start", weight="bold")

arrow(KX+NW+8, KY+NH+34, 898, KY+NH+34, colour=MUTED, dash="4,4", width=2)
txt(903, KY+NH+38, "anonymized aggregates may", 12, MUTED, anchor="start")

add('</svg>')
open("concept-map.svg", "w").write("\n".join(out))
print("wrote concept-map.svg")

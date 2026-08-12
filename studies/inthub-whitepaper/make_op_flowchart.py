#!/usr/bin/env python3
"""Render an Op as a flowchart — from its declared structure, not by hand.

The point is not the picture. The point is that an Op already declares its
Guards, its Gates and their predicates (whitepaper S5.6), which is enough to
*generate* this diagram for any Op. Draw one by hand and you have illustrated
an example; generate it from the declaration and you have a way to see any Op,
including one a colleague installed and you have never read.

Emits two files, from the same renderer:
  op-flowchart-generic.svg   the shape every Op has
  op-flowchart-vendor.svg    the paper's running example, substituted in

Usage:  python make_op_flowchart.py
"""

NAVY, TEAL, LIGHT, INK = "#1b2a4a", "#0e7c7b", "#d5e8f0", "#222222"
MUTED, RED, AMBER, GREEN = "#6b7280", "#a03232", "#b45309", "#166534"
SANS = "DejaVu Sans,Helvetica,sans-serif"

# ---------------------------------------------------------------- the model
# An Op, as much of it as a flowchart needs. Mirrors the S5.6 manifest:
# stages carry Guards; each stage ends at a Gate with a predicate and a
# consequence drawn from the closed vocabulary in S5.2.
GENERIC = dict(
    title="Any Op — the shape",
    subtitle="what every Op does, whatever the work is",
    trigger="a person, a schedule, or another Op",
    frames="the Frames in scope",
    stages=[
        dict(band="PRE-FLIGHT", ask="Is this Op allowed to run at all?",
             items=["permission Guard", "required-Frame Guard", "data-authorization Guard"],
             gate="any pre-flight Guard fails", fail="refuse — the Op never starts"),
        dict(band="IN-FLIGHT", ask="Is the work staying inside policy?",
             items=["the Cogs do the work", "policy · privacy · confidence Guards"],
             gate="a bound is exceeded", fail="pause, escalate, or stop"),
        dict(band="POST-RUN", ask="Is the result fit to act on?",
             items=["schema · source-grounding · consensus Guards", "expert sampling"],
             gate="the result is not trusted", fail="revise, review, or discard"),
    ],
    outcome="the action is taken",
    continuous="CONTINUOUS — drift and regression Guards watch across runs",
)

VENDOR = dict(
    title="Vendor Fraud Review",
    subtitle="the paper's running example — the same shape, filled in",
    trigger="an accounts-payable analyst clicks one button",
    frames="company policy · procurement rules · fraud methodology",
    stages=[
        dict(band="PRE-FLIGHT", ask="Is this analyst allowed to review this vendor?",
             items=["permission Guard", "required-Frame Guard", "data-source authorization"],
             gate="not authorized", fail="refuse — the Op never starts"),
        dict(band="IN-FLIGHT", ask="Is anything leaking, is confidence holding?",
             items=["invoice extraction → vendor risk → anomaly summary",
                    "tool-use · sensitive-data · confidence Guards"],
             gate="sensitive_data_detected", fail="stop and escalate"),
        dict(band="POST-RUN", ask="Is the finding safe to act on?",
             items=["schema · source-grounding · consensus Guards", "expert sampling"],
             gate="confidence &lt; 0.80  ·  disagreement &gt; 0.25  ·  vendor_risk == high",
             fail="human review, expert review, or approval"),
    ],
    outcome="the vendor is flagged — never by the machine alone",
    continuous="CONTINUOUS — drift Guards watch quality across runs",
)

# The closed set a Gate may choose from (S5.2). This is the generalisable part:
# Ops differ in their Guards and thresholds; the decision vocabulary does not.
GATE_OUTCOMES = ["continue", "pause", "request human approval", "escalate to an expert",
                 "retry with a different Cog", "run more validation", "stop"]


def fit(s, maxw, size, min_size=8.5, max_lines=2):
    """Greedy wrap + shrink so arbitrary Op text stays inside its box.

    The renderer must cope with whatever an Op declares, so text is measured
    (approximately — 0.52em average advance for DejaVu Sans) rather than
    assumed to fit. Shrinks a step at a time, then wraps, then shrinks again.
    """
    def wide(t, sz): return len(t) * sz * 0.52
    words = s.split(" ")
    while True:
        lines, cur = [], ""
        for w in words:
            trial = w if not cur else cur + " " + w
            if wide(trial, size) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur); cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines or size <= min_size:
            return size, lines[:max_lines]
        size -= 0.5


# ---------------------------------------------------------------- rendering
W = 1120
SPINE = 470          # centre of the main column
BW = 400             # band width; band height grows with its item count
GAP = 34


def render(op, path):
    o, y = [], 0
    def add(s): o.append(s)

    def txt(x, yy, s, size=13, fill=INK, anchor="middle", weight="normal", style="normal"):
        add(f'<text x="{x}" y="{yy}" text-anchor="{anchor}" font-family="{SANS}" '
            f'font-size="{size}" font-weight="{weight}" font-style="{style}" fill="{fill}">{s}</text>')

    def txtfit(x, yy, s, maxw, size=13, fill=INK, anchor="middle", weight="normal",
               style="normal", max_lines=2):
        size, lines = fit(s, maxw, size, max_lines=max_lines)
        y0 = yy - (len(lines)-1) * (size*0.62)
        for i, ln in enumerate(lines):
            txt(x, y0 + i*size*1.24, ln, size, fill, anchor, weight, style)

    def arrow(x1, y1, x2, y2, colour=NAVY, dash=None, width=2.5):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
            f'stroke-width="{width}"{d} marker-end="url(#m{colour[1:]})"/>')

    y = 30
    txt(SPINE, y + 8, op["title"], 22, NAVY, weight="bold"); y += 30
    txt(SPINE, y + 8, op["subtitle"], 13.5, MUTED, style="italic"); y += 46

    # trigger
    add(f'<rect x="{SPINE-BW/2}" y="{y}" width="{BW}" height="46" rx="23" fill="white" '
        f'stroke="{NAVY}" stroke-width="2.5"/>')
    txtfit(SPINE, y + 28, op["trigger"], BW-28, 13.5, NAVY)
    y += 46

    # frames rail
    add(f'<rect x="52" y="{y+24}" width="196" height="52" rx="9" fill="{LIGHT}" '
        f'stroke="{TEAL}" stroke-width="2"/>')
    txt(150, y + 45, "FRAMES", 12.5, TEAL, weight="bold")
    txtfit(150, y + 62, op["frames"], 178, 10.5, INK, max_lines=3)
    arrow(250, y + 50, SPINE - BW/2 - 6, y + 50, TEAL, dash="5,4", width=2)

    track_top = y + 20
    for st in op["stages"]:
        arrow(SPINE, y, SPINE, y + GAP - 6)
        y += GAP

        bh = 60 + 16*len(st["items"])
        add(f'<rect x="{SPINE-BW/2}" y="{y}" width="{BW}" height="{bh}" rx="9" '
            f'fill="{LIGHT}" stroke="{NAVY}" stroke-width="2.5"/>')
        txt(SPINE - BW/2 + 14, y + 21, st["band"], 12.5, NAVY, anchor="start", weight="bold")
        txt(SPINE - BW/2 + 14, y + 39, st["ask"], 12, MUTED, anchor="start", style="italic")
        for i, it in enumerate(st["items"]):
            txtfit(SPINE - BW/2 + 14, y + 58 + i*16, "• " + it, BW-34, 11.5, INK,
               anchor="start", max_lines=1)
        y += bh

        # gate diamond
        arrow(SPINE, y, SPINE, y + GAP - 6)
        y += GAP
        cy, hw, hh = y + 44, 116, 44
        add(f'<polygon points="{SPINE},{cy-hh} {SPINE+hw},{cy} {SPINE},{cy+hh} {SPINE-hw},{cy}" '
            f'fill="white" stroke="{NAVY}" stroke-width="2.5"/>')
        txt(SPINE, cy - 12, "GATE", 12.5, NAVY, weight="bold")
        txtfit(SPINE, cy + 10, st["gate"], 176, 10.5, INK, max_lines=2)

        # fail branch, to the right
        arrow(SPINE + hw, cy, SPINE + hw + 96, cy, RED)
        add(f'<rect x="{SPINE+hw+100}" y="{cy-22}" width="240" height="44" rx="8" '
            f'fill="#fdf3f3" stroke="{RED}" stroke-width="2"/>')
        txtfit(SPINE + hw + 220, cy + 5, st["fail"], 224, 11.5, RED)
        txt(SPINE + hw + 48, cy - 8, "fail", 11, RED)

        y = cy + hh
        txt(SPINE + 16, y + 22, "pass", 11, GREEN, anchor="start")

    # outcome
    arrow(SPINE, y, SPINE, y + GAP - 6)
    y += GAP
    add(f'<rect x="{SPINE-BW/2}" y="{y}" width="{BW}" height="46" rx="23" fill="#f0fdf4" '
        f'stroke="{GREEN}" stroke-width="2.5"/>')
    txtfit(SPINE, y + 28, op["outcome"], BW-78, 13.5, GREEN, weight="bold")
    y += 46

    # track rail down the right-hand side
    tx = 1000
    add(f'<rect x="{tx-52}" y="{track_top}" width="104" height="{y-track_top}" rx="10" '
        f'fill="{NAVY}" opacity="0.93"/>')
    for i, ch in enumerate("TRACK"):
        txt(tx, track_top + 40 + i*26, ch, 17, "white", weight="bold")
    txt(tx, track_top + 40 + 5*26 + 18, "every", 10.5, LIGHT)
    txt(tx, track_top + 40 + 5*26 + 32, "stage", 10.5, LIGHT)
    txt(tx, track_top + 40 + 5*26 + 46, "recorded", 10.5, LIGHT)

    # continuous band
    y += 34
    add(f'<rect x="60" y="{y}" width="{tx+52-60}" height="40" rx="9" fill="#f4f6f9" '
        f'stroke="{TEAL}" stroke-width="2" stroke-dasharray="6,4"/>')
    txtfit((60 + tx + 52)/2, y + 25, op["continuous"], tx-60, 12.5, TEAL)
    y += 40

    # the closed vocabulary a Gate chooses from
    y += 26
    txt(60, y, "A Gate always chooses from the same seven:", 12, MUTED, anchor="start", weight="bold")
    y += 18
    txt(60, y, "  ·  ".join(GATE_OUTCOMES), 12, MUTED, anchor="start")
    y += 26

    head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {y}" width="{W}" height="{y}">',
            '<defs>']
    for c in (NAVY, RED, TEAL, GREEN):
        head.append(f'<marker id="m{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                    f'markerHeight="7" orient="auto-start-reverse">'
                    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
    head.append('</defs>')
    head.append(f'<rect width="{W}" height="{y}" fill="white"/>')
    open(path, "w").write("\n".join(head + o) + "\n</svg>\n")
    print(f"wrote {path}")


render(GENERIC, "op-flowchart-generic.svg")
render(VENDOR, "op-flowchart-vendor.svg")

# Planting spec — the calibration document

You will write a fictional technology whitepaper: 1,200–1,800 words of plausible,
enthusiastic vendor prose about an invented product category. It must read like a real
document — confident tone, an executive summary, sections, a sprinkle of invented market
figures and analyst quotes. Invent all names fresh; do not reuse vocabulary from any real
product or paper you know.

Plant exactly these six defects, weaving them naturally into the prose:

- **P1 — load-bearing, never defined.** The document's central coined noun (the product
  category itself works well): used at least ten times, carrying the argument, defined
  nowhere — every occurrence assumes the reader already knows what it is.
- **P2 — a name that smuggles.** A coined feature whose *name* asserts a guarantee, while a
  single quiet sentence elsewhere in the document concedes the guarantee does not always
  hold. The name and the concession must never appear in the same section.
- **P3 — a derivable claim sold as independent.** Three claims: A and B stated plainly, and
  C — which follows logically from A and B together — presented in a different section as a
  separate, headline selling point, with no acknowledgment that it follows.
- **P4 — people dressed as mechanism.** A claim phrased as a property of the system ("the
  platform ensures…", "by construction…") whose actual support, visible on a careful read,
  is an organisational process: a review board, a certification step, staff judgment.
- **P5 — groundless.** One specific quantified claim (a percentage, a multiplier) supported
  by nothing anywhere in the document — no source, no reasoning, no related material.
- **P6 — a circular pair.** Two coined terms, each defined in the document, where each
  definition leans on the other and nothing else breaks the circle.

Everything else in the document should be ordinary, defensible filler: real-sounding but
fictional numbers with invented sources attached, generic architecture talk, adoption
stories. The defects must not be adjacent to each other or marked in any way.

Output JSON only:
{"document": "<the full document, markdown>",
 "plants": {"P1": "<the term>",
            "P2": {"name": "<the feature name>", "concession": "<the quiet sentence>"},
            "P3": {"A": "<claim>", "B": "<claim>", "C": "<the derivable headline claim>"},
            "P4": "<the mechanical-sounding sentence and the organisational support>",
            "P5": "<the groundless quantified claim>",
            "P6": ["<term one>", "<term two>"]}}

# Spec — the clean calibration document

You will write a fictional technology whitepaper: 1,200–1,800 words about an invented product
category, in a confident, professional vendor voice — executive summary, sections, invented
market figures with named (fictional) sources. Invent all names fresh; reuse no vocabulary
from real products or papers you know, and none from any document about data custody,
escrow, or field-level governance.

This document must contain NO planted defects. Hold it to this discipline throughout:

- Every coined term is defined precisely at or before its first use, in one sense, and used
  in only that sense thereafter. No term's meaning is ever assumed.
- Every quantified claim carries its (fictional) source AND one sentence on how the number
  was obtained.
- No claim is presented as independent if it follows from other claims made; where one thing
  follows from others, the document says "it follows that".
- Every feature name promises exactly what its description delivers — no name asserts a
  guarantee the text qualifies elsewhere.
- Where a property rests on an organisational process (a review step, a certification, staff
  judgment), the document says so plainly rather than phrasing it as a mechanism.
- Where a question is genuinely open (edge cases, boundaries), the document states it as
  open rather than papering over it.

The result should read like an unusually honest vendor paper — enthusiastic but exact.

Output JSON only:
{"document": "<the full document, markdown>",
 "discipline_notes": "<one paragraph: where you were most tempted to cut a corner and how
you avoided it>"}

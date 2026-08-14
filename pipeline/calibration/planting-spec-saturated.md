# Spec — the saturated calibration document

You will write a fictional technology whitepaper: 1,200–1,800 words about an invented product
category, in a confident vendor voice. Invent all names fresh; reuse no vocabulary from real
products, from data-custody/escrow documents, or from agricultural lighting.

This document must be DEFECTIVE THROUGHOUT — every load-bearing sentence should fail careful
reading, while still sounding professionally plausible on a skim. Saturate it with:

- Coined terms never defined anywhere, used constantly and load-bearingly.
- At least one circular chain of three or more terms, each "defined" via the next.
- Central terms used in three or more incompatible senses without acknowledgment.
- Pairs of claims in different sections that contradict each other outright.
- Quantified claims with no source, or with sources that the text elsewhere undermines.
- Feature names asserting guarantees the text quietly retracts or never supports.
- At least two references to definitions or sections that do not exist ("as defined above",
  "see the formal treatment in §9" where there is no §9).
- Mechanism-sounding claims whose only support, on any careful read, is nothing at all.

The skim-plausibility matters: headings, structure, and tone must stay professional. The rot
is in the load-bearing joints, not the surface.

Output JSON only:
{"document": "<the full document, markdown>",
 "defect_catalogue": [{"type": "...", "example": "<short quote>"}]}

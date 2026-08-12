# The method

Hypelysis reads a technical document by refusing to use its vocabulary until each word has
earned a definition. The output is a small theory, an executable example, and a translation of
the document into the theory — with everything that refuses to translate named and located.
The gap between what a document says and what its words can do is the finding.

*Lysis* is Greek for dissolution — the *-lysis* of analysis, hydrolysis, electrolysis. The
document is dissolved into the theory; what goes into solution is machinery; the residue is
people. Both phases are kept.

## The artifacts of a study

A study is a directory under `studies/`, holding, in the order they are built:

1. **A base ledger** (`definitions.md`) — primitives and definitions for the document's
   *mechanical* content: what its systems actually do, built from first principles under
   [RULES.md](RULES.md). Nothing enters without the study owner's per-entry approval; every
   change is logged; rejections are kept with their reasons.
2. **An examples section and companion script** — one running system, small enough to track
   by hand, materializing every entry; the script asserts every claim, so `python3 examples.py`
   is the theory's test suite. Non-examples fence the meanings: the degenerate cases are
   findings, not failures.
3. **A companion ledger** (`organisational-definitions.md`) — for the terms the base ledger's
   primitives cannot reach: persons, obligations, history. Its primitives are the *bindings* —
   facts that carriers (signatures, logs, registries) can evidence but never establish. The
   bridge is one-way: the companion may cite the base, never the reverse.
4. **A translation** — the document restated term by term in the two ledgers' vocabulary:
   a dictionary, the document's load-bearing claims each tagged *confirmed*, *sharpened*, or
   *corrected*, and a list of claims testable against real systems.
5. **Graphs** — generated from the ledgers and the translation by `tools/make_graphs.py`,
   never drawn by hand, so they cannot go stale.

## The practices that make it work

- **Names smuggle claims.** "Vocabulary" implies words, "owner" implies control, "generation
  step" implied generation. Expect to be wrong about a name before being wrong about a
  concept; when a name overclaims, rename and record the old name as *Also called*.
- **Defer with a trigger.** A concept enters when something needs it, and the need is written
  down at the moment of deferral. Admission is judged on what it simplifies, not on how often
  it was deferred.
- **The are-you-sure audit.** When the theory stabilizes, walk every entry in order under one
  question. What surfaces is rarely a wrong definition — it is wordings that left load-bearing
  cases to charity, parameters carried silently, and commentary claiming more than its entry
  earns.
- **Formulas audit prose; code audits both.** Writing an entry as a type exposes what the
  sentence absorbed; implementing it exposes what both hid. Keep all three renderings and let
  them disagree loudly.
- **Deliverables carry state, not story.** A reader needs the current theory to make
  decisions; the journey lives in the revision logs, where every change, correction, and
  rejection is kept with its reasoning.
- **Check mechanically.** `tools/check.py` verifies what the rules promise: citations match
  headings, numbering is contiguous, no forward references, the bridge is one-way, the
  examples cover every entry. The checks exist because everything they test rotted at least
  once while unwatched.

## Starting a new study

Make a directory under `studies/`. Copy nothing. Begin with the document's most load-bearing undefined
word, propose the primitives it needs, and let the owner approve entries one at a time.
The base ledger of an existing study may *look* reusable — resist until the new document
demands the same entries, then decide deliberately.

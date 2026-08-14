# Rulebook

You are helping build a *foundation* for reading one document: a list of terms whose meanings
are settled before the document's own claims are examined. The foundation is how the document
gets read on its merits — no word of the document may do work in the analysis until it has an
entry here, or is shown to be everyday language.

## Entries

An entry is one term. Two kinds:

- **base** — a term used without a statement of meaning beyond a short assumed reading. Every
  base entry carries one line saying why it is safe to leave unexplained: the assumed reading
  must be one that any careful reader would share. Base terms are the floor; keep them few,
  and never use base status to dodge a hard question — if a term is contested or carries the
  document's argument, it needs a defined entry.
- **defined** — a term whose statement uses only entries that already exist, plus everyday
  language. No entry may use a term that appears later in the list. A definition that needs
  something not yet present is out of order or premature: reorder, or defer.

Format, exactly:

```
### <term>
Kind: base | defined
Given: <optional — what the entry is relative to, named so the Statement can use the names>
Statement: <one to three sentences; for base, the assumed reading>
Because: <base only — why leaving it unexplained is safe>
Uses: <defined only — comma-separated earlier terms; or "everyday language only">
Notation: <optional — the statement in symbols; an aid, never the meaning>
Defers: <optional — one clause per document-loaded word used here without an entry: the word,
        and the future need that would justify one; semicolon-separated>
Open: <optional — one clause per question the entry deliberately leaves unsettled or excludes;
      semicolon-separated>
Finding: <optional — one clause per fact about the document this entry surfaces;
         semicolon-separated>
Note: <optional — residual commentary none of the fields above can carry>
```

A **Given** names the things an entry is relative to, so the Statement can refer to them by
short names instead of nesting descriptions; two instances can then be told apart by what
they are given. A **Notation** restates the entry in symbols. Where a notation and its
Statement disagree, the Statement governs — the notation is wrong. Every symbol and reading
device a notation uses is declared in a notation table in the foundation before first use;
nothing is smuggled.

**Defers**, **Open**, and **Finding** are declaration fields: each holds telegraphic clauses
("`<field>: <sequence of words>`"), semicolon-separated, not essay sentences — a clause states
the declaration and, where one exists, its trigger or source, and nothing else. A clause in
Open or Defers is a decision made visible: a check that restates one is describing the entry,
not objecting to it. An openness inherited from an earlier entry is a clause naming its source
("inherited from 'custody horizon'"), not a re-argument. A later entry that *needs* a deferred
meaning is still incomplete (rule 1) — deferral shields the declaring entry, never its
dependents.

## Discipline

1. **A word is an entry, base, or everyday — and everyday language is the medium, not a
   dependency.** Every statement is written in words that will never all be entries; that is
   how language works, not a defect. A word needs an entry only when the DOCUMENT loads it —
   its coinages, its counted units, the words carrying its argument. Domain vocabulary used
   in its ordinary sense ("schema", "value", "named") is the medium. If a statement leans on
   a word the document loads and no entry supplies, the proposal is incomplete.
2. **Names are claims.** A term's name must not promise more than its statement delivers.
   When it does, choose a plainer name and record the document's word in a Note.
3. **Prefer defining over declaring base** — but a base term is the right choice when every
   candidate definition introduces more unexplained words than it removes, or when the plain
   reading is more reliably shared than any construction.
4. **Defer with a reason.** When a term is not yet needed, do not add it; record what future
   need would justify it. At entry level, that record is a Defers clause: the word, and the
   need that would call for its entry.
5. **Changes are logged.** Any revision to an existing entry must not contradict the entries
   that came before it, and every entry after it must be re-checked. Keep rejected changes on
   record with the reason they failed.
6. **Two lanes.** Terms about what the described system *does* (its mechanisms) form the first
   lane. Terms about *people* — who owns, who approves, who answers, what is remembered over
   time — form a second lane, built after the first. Second-lane entries may use first-lane
   entries; never the reverse.
7. **Redundant renderings are welcome, and disciplined.** Notations, worked examples, and
   figures restate entries for human perception; they never replace the Statement. The
   redundancy is also a detector: renderings that disagree expose defects the prose absorbed,
   so keeping an entry's statement, its notation, and its worked example in agreement is a
   check, not a chore. Figures, where used, are generated from the entries rather than drawn
   free-hand, so they cannot drift.
8. **Statements must be checkable.** Where an entry can be illustrated by a small worked
   example, it should be; an example that cannot be worked by hand signals a vague entry.

## The aim

The foundation exists to produce feedback for the document's authors: which of their terms
never receive workable meanings, which of their claims follow from other claims, which claims
rest on the people lane while sounding mechanical, which names promise more than the text
delivers, and which claims have no support at all. Precision in the foundation is what makes
that feedback fair.

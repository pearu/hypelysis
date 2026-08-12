# Organisational definitions

A ledger of definitions Pearu has approved as **complete**, for the terms `definitions.md`
marks *organisational* — those whose content involves persons, obligations, or history. Its
purpose is to finish the translation of the whitepaper: `definitions.md` holds what the
machinery does; this ledger holds what organisations add around it; the two together should
leave no whitepaper term untranslated.

**Governance.** The rules, clarifications, and entry format of `../../RULES.md` govern this
file unchanged, as they do `definitions.md`. Nothing enters without explicit per-entry
approval.

**Prefixes.** Primitives are `Q1, Q2, …` and definitions are `O1, O2, …`, so that citations
never collide with `definitions.md`'s `Pn`/`Dn`. The citation convention carries over:
`Qn[term]`, `On[term]` — for instance `Q1[person]`.

**The bridge is one-way.** An entry here may depend on entries of `definitions.md` — its
texts, sets, functions, and numbers are how organisational facts get mechanical carriers — but
no entry of `definitions.md` may ever depend on an entry here. `definitions.md` stays
self-contained; this ledger is built on top of it.

**What this ledger must respect.** Per `../../RULES.md`'s clarification that defines
*organisational*:
carriers translate, bindings do not. Where an entry reaches a binding — the point at which an
artifact is tied to a person by nothing further — that binding is a primitive here, stated
honestly, not dressed up as a mechanism.

---

## Candidates

From the translation's residue, worked through under the protocol. The list is empty: every
candidate has become an entry or been resolved below.

Resolved without becoming entries: *identity* — constituted by Q3[succession] rather than
defined, since two texts are states of one artifact exactly by being items of one succession;
*pastness* — being an earlier item of a history (O4[version] Notes); *hierarchy* — the
arrangement of delegation viewed as a comparison on persons and groups, whose properties
(transitivity, tree-shape) belong to the organisation as P5[less than]'s order properties
belong to the set; *reporting* — Q4[obligation] with a delivery-shaped description, a
composite in a role; *accountability* — Q1[person]'s second clause is the capacity and
Q2[attribution] its assignment, so the whitepaper's "accountable to a named human" is
O2[owner] with a non-empty group; *inheritance* — mechanically, text composition with union
of declared checks; organisationally, scope nesting (O6[scope] Notes); *trust* — expectation that the bindings
hold — attribution, succession, compliance — grounded in carriers and history: the
whitepaper's outcome word, never its mechanism, sayable in the ledger's vocabulary whenever
needed.

---

## Primitives

### Q1 — person
**Assumed meaning.** Someone who can act and be answerable for what they did.
**Why left undefined.** Any definition — a legal person, a rational agent, a bearer of
rights — imports a body of theory larger than this ledger to remove one word. "Someone who can
act and be answerable" is reliably the same idea for every reader.
**Added.** 2026-08-12
**Notes.** The two clauses are both load-bearing, and the second does the discriminating work:
an AI worker acts, but is not answerable — which is the entire reason the whitepaper places a
named human behind every artifact, and why *accountable* cannot bottom out in a Cog. Who
counts as a person in a deployment is decided by the organisation's own context — a legal
question, not this ledger's — the same move P2[symbol] makes in letting the set decide what a
symbol is.

### Q2 — attribution
**Assumed meaning.** That a person stands behind a text: they answer for it.
**Why left undefined.** Every candidate definition describes a carrier — a signature, a name
written into the file, a row in a registry — and each carrier is again a text, whose tie to
the person is the very thing being defined. The regress ends only at the binding itself, and
the preamble requires bindings to be stated as primitives, not dressed up as mechanisms.
**Added.** 2026-08-12
**Notes.** Attribution is not authorship: one can stand behind a text one did not write —
approval and adoption are attributions, and the whitepaper's Frame owners need not be its
authors. It is not a function: many persons may stand behind one text and one person behind
many (contrast P4[function]). A set of two-item sequences ⟨identifier, text⟩ can *record*
attributions — that is what a registry is — but the record is a carrier, and the tie of
identifier to person is this primitive again. An attribution is a fact at a moment; transfer
and revocation need history, which this ledger does not yet have. A group standing behind a
text *as a unit*, rather than through its members, is deliberately not covered — it becomes
its own primitive if the whitepaper's accountability turns out to need committees that answer
collectively. Attribution is to the text as content, and a text is one thing wherever it
occurs (P6[same as]): whoever stands behind a text stands behind its content, not behind
every act of inscribing it — another's identical inscription is another's deed. This grain is
the whitepaper's own: an expert stands behind a Guard's content wherever it is installed,
which is what makes standing-behind exchangeable (§6.1). Its shadow is replay — a carrier
over short common content binds too little context — and practice answers by writing
uniqueness into the content itself, nonces and context fields: the assembly's delimiter
lesson in another key.

### Q3 — succession
**Assumed meaning.** That the items of a sequence of texts are the states of one artifact,
each holding until the next.
**Why left undefined.** Two bindings in one, and neither is derivable from the texts: that the
texts belong to *one* thing, and that their order is the order in which they held. Any
evidence offered for either — a log, a set of timestamps, a chain of hashes — is another text,
whose faithfulness is the thing being assumed. The regress ends at the binding, as with
Q2[attribution].
**Added.** 2026-08-12
**Notes.** Stated in proposition form so that definitions can use it as a condition — the move
P5[less than] and P6[same as] make in the mechanical ledger. Not the ordinary English "in
succession", which means merely *consecutively* and is true of every sequence: what is assumed
here is that the items are states of **one artifact**, in the order those states held.
Identity through change needs no separate entry, but not because it is derived: "one
artifact" is part of what this primitive assumes, and the ledger has no access to "same
artifact" except through membership in one succession. A repository does not contain an
artifact plus its history; the history is the artifact.

### Q4 — obligation
**Assumed meaning.** That a person must bring about what a text describes, and answers for it
if it is not brought about.
**Why left undefined.** The deontic *must* cannot be built from what either ledger holds: it
is not a text (writing "must" obliges no one), not a function, and not an attribution — a
person can stand behind a text without being obliged by it. Every candidate definition — a
rule written somewhere, an agreement, a threat of consequence — is a carrier whose bindingness
is the thing being defined. The regress ends at the binding, as with Q2[attribution] and
Q3[succession].
**Added.** 2026-08-12
**Notes.** Operands: a person and a text, the text *describing* what must be brought about —
and the reading of the description is a convention outside both ledgers, exactly as
"determines" is for D10[model specification]. Whether what was done satisfies the description
is a further binding — call it compliance — settled by neither the deed nor the text. The
second clause ties the notion to Q1[person]: an obligation is what makes non-performance
something to answer for. A group is obliged through its members, as with Q2[attribution];
collective obligation is deferred on the same trigger. A prohibition is an obligation whose
described state is an absence — that no private data is released — carried by the description
as all content is; the whitepaper's Policy Guards are mostly of this shape.

### Q5 — permission
**Assumed meaning.** That a person may bring about what a text describes: doing so is not, by
itself, something to answer for.
**Why left undefined.** The tempting definition — permitted is what is not forbidden — needs
negation over deeds and a closed catalogue of the forbidden, machinery neither ledger has; and
in organisations permission is not the absence of prohibition anyway but the presence of a
grant, which presupposes this notion rather than defining it.
**Added.** 2026-08-12
**Notes.** The duality with Q4[obligation] is deliberately routed through answerability, not
negation: obligation makes *not doing* answerable; permission makes *doing* unanswerable.
(This is the shape of Hohfeld's duty and privilege — an outside anchor, named as outside.)
Permission covers the deed, not its manner: how something permitted was done can still be
answered for. Granting and revoking — bringing it about that another person is permitted — are
deeds like any other, described by texts about permissions; that self-reference is what makes
delegation definable rather than primitive.

---

## Definitions

### O1 — group
**Definition.** A set of persons.
**Depends on.** P3[set], Q1[person]
**Added.** 2026-08-12
**Notes.** The first bridge crossing: the set is the mechanical ledger's, the members are this
ledger's. A group of one is a group, so the whitepaper's recurring "a human or a group of
humans" (§4.3) collapses to "a group" with no loss. Whether a group of none exists is the
zero-items question again, deliberately open in both ledgers; nothing here creates one, and an
empty owner — a text no one is behind — is exactly the situation the whitepaper exists to
prevent for its governed artifacts.

### O2 — owner
**Given.** a text t
**Definition.** A group, each of whose members stands behind t.
**Depends on.** D2[text], O1[group], Q2[attribution]
**Added.** 2026-08-12
**Notes.** Because every shippable artifact is a text, one definition covers the whitepaper's
four marketplace classes at once — Frames, Guards, Op manifests, model specifications — and
the Hub's registry rows besides. Nothing here gives every text an owner, and that is by
design: most texts — a typed prompt, a generated output — have no one behind them, and should
not. Should the group of none be admitted, it qualifies vacuously, and the empty owner reads
as ownerlessness: "t's only owner is empty" and "no one stands behind t" say the same thing,
so the zero-items question has no stake here. The whitepaper's requirement that its artifacts
be owned — §4.3's *Owned* row, §6.1's "named, accountable owner" — is a policy about those
texts, enforced in carriers such as registries, and is therefore checkable rather than true;
the paper's own gloss supports answerability as the core, pricing an artifact by "who stands
behind it". Of the deferrals this entry once carried, two have discharged: *management* —
the right to change the text and gatekeep changes (§7.5) — is Q5[permission] over that deed,
and *transfer* is statable through O3[history] and O4[version], the owner of one version and
of the next being free to differ. What remains is *uniqueness*: nothing makes an owner *the*
owner; that a text has exactly one is policy.

### O3 — history
**Definition.** A sequence of texts whose items stand in succession.
**Depends on.** D2[text], P1[sequence], Q3[succession]
**Added.** 2026-08-12
**Notes.** Most sequences of texts are not histories, and whether one is cannot be read off
the sequence — the restriction is Q3[succession]'s binding, assumed rather than checked; a
carrier such as a hash chain can make forging a *record* of succession costly, but cannot
make the record true. The carrier–binding split at its cleanest: the sequence is fully
mechanical — a git chain, a registry's rows — and translates completely; that it faithfully
records one artifact's states does not. A history is append-shaped by its meaning rather than
by any rule here: rewriting an earlier item does not change what held, it produces a different
record of succession — a claim, not a mechanism, and exactly what the whitepaper's audit story
needs to be able to say.

### O4 — version
**Given.** a history h
**Definition.** An item of h.
**Depends on.** P1[sequence], O3[history]
**Added.** 2026-08-12
**Notes.** A text in a role, as D4[token] is a symbol in a role. *Earlier* and *later* among
versions come free from P1[sequence]'s order; *pastness* is being an earlier item. The
whitepaper's "versioned" property (§4.3, §4.5) translates as: there exists a history whose
items are the artifact's states — an organisational fact, carried by whatever maintains the
record. Transfer of ownership is statable with no further machinery: the owner of one version
and of the next may differ.

### O5 — delegation
**Given.** persons p and q, and a text t
**Definition.** That p is permitted to bring about that q is permitted what t describes.
**Depends on.** D2[text], Q1[person], Q5[permission]
**Added.** 2026-08-12
**Notes.** A permission about a permission — no new primitive, as Q5[permission]'s Notes
promised. Revocation is the same shape with an ending in the described deed, and the
description carries that content the way all descriptions do: by convention, outside the
ledgers. Nothing here makes delegation transitive or exclusive; what an organisation's grants
add up to is a property of that organisation.

### O6 — scope
**Definition.** A text that determines a group.
**Depends on.** D2[text], O1[group]
**Added.** 2026-08-12
**Notes.** The criterion, not the collection: the determined group varies as people come and
go while the scope stays the same text — exactly as D10[model specification]'s set of models
varies by machine while the specification stands. Determination rests on a reading convention
plus facts on the ground, as it does for every specification. The whitepaper's scope kinds —
organization, department, team, project, role, relationship (§4.3) — are all such texts. A
Frame *applies within* its scope when each member of the determined group is obliged as the
Frame describes for them — Q4[obligation] composed, needing no entry of its own until
something wants the name. Nesting is membership between determined groups: s lies within s′
when every member of the group the one determines is a member of the group the other does.
The whitepaper's other use of the word — credentials "scoped" (§4.2) — is not this scope but
a permission with a narrower describing text, and needs no entry.

### O7 — provenance
**Given.** a history h
**Definition.** That someone stands behind each version of h.
**Depends on.** Q1[person], Q2[attribution], O3[history], O4[version]
**Added.** 2026-08-12
**Notes.** The first defined *condition* — a proposition built from prior entries,
Q2[attribution] taken across O4[version]s — which the Clarification on primitives licenses
for use exactly as the primitive conditions are used. The whitepaper's thesis now has a
formal reading: "provenance is the product" (§6.1) prices this condition together with
Q3[succession] itself — and both are bindings, so what a marketplace actually moves is
*records claiming provenance*: the record translates completely, being texts, while the
claimed fact never does. A signature chain raises the cost of forging the record; nothing
establishes the fact. That is why provenance cannot be generated, cannot be faked from inside
the loop, and can be the product — the whitepaper's §6.1 argument, derived rather than
quoted. Provenance here is custody, not derivation: that a version was produced from other
texts is recordable mechanically — D17[run specification] holds exactly that — and is the
other half of what practice calls provenance; the two halves meet in a record, and only this
half is bindings.

### O8 — approval
**Given.** a person p and a text t
**Definition.** A text that p stands behind, describing a permission of what t describes.
**Depends on.** D2[text], Q1[person], Q2[attribution], Q5[permission]
**Added.** 2026-08-12
**Notes.** The runtime picture — halt until a human presses ok — decomposes: the halt is a
computation blocking on an unsupplied input, exactly as it blocks on draws, and is no part of
the function; the pressed symbol is data entering where draws enter (D20[checked run] Notes);
and what makes the event an *approval* is neither of these but the attribution — the bit
binds no one, the text behind which p stands does, and that binding is what the whitepaper's
approval Gates exist to produce. A refusal is not the absence of an approval but its own
artifact — a text p stands behind describing that the deed is *not* permitted, an
absence-shaped description as in Q4[obligation]'s Notes — which is why audit practice records
refusals, not just consents. Q2[attribution]'s grain applies with force: an approval must
name what it approves distinctively, or it approves too much — the reason real approval
records reference the artifact by hash, uniqueness written into content.

### O9 — retention
**Given.** a person p and a history h
**Definition.** That p must bring about that h is kept, and extended only in succession.
**Depends on.** Q1[person], Q3[succession], Q4[obligation], O3[history]
**Added.** 2026-08-12
**Notes.** The whitepaper's `retain_for: 7_years` (§5.6) and §3.4's retention policies.
Durations are beyond both ledgers — "seven years" is carried by the description's convention,
since succession gives order and not distance. The "extended only in succession" clause is
O3[history]'s append-shape made someone's duty.

---

## Revision log

Every change to an existing entry under R5, with the re-verification result.

### 2026-08-12 — migrated to the hypelysis repository — **accepted**

**Change.** The governance pointer moved from `definitions.md`'s rules sections to the
repository-level `../../RULES.md`, where they now live for every study. Nothing else changed.

**R5/R7.** Structural, not semantic. **Passes.**

### 2026-08-12 — audit closures: Q3 reworded, Q4 and O7 extended — **accepted**

**Change.** Three closures from the are-you-sure audit. Q3[succession]'s Notes claimed
identity through change was "constituted rather than presupposed" while the assumed meaning
itself uses "one artifact" — an overclaim; the Notes now say the true, weaker thing: identity
needs no separate entry because the ledger has no access to "same artifact" except through
membership in one succession. Q4[obligation] gains the prohibition reading — an obligation
whose described state is an absence — the whitepaper's most common Guard shape.
O7[provenance] declares its deliberate exclusion: custody, not derivation, the latter being
mechanically recordable in D17[run specification].

**The audit, closed.** Thirty-nine entries across both ledgers, examined in order under one
question. Outcome: P1 and P4 amended (the single item; no-value inputs outside the domain),
D8/D9 corrected under R9 (the number set named), Q2's grain declared, and the three closures
above; everything else confirmed under pressure. The pattern of what surfaced: wordings that
left load-bearing cases to charity, parameters carried silently, and commentary claiming more
than its entry earns — never a definition wrong outright.

**R5/R7.** Notes are commentary throughout; no assumed meaning or definition changed beyond
P1/P4/D8/D9, each logged in the mechanical ledger. **Passes.**

### 2026-08-12 — Q2[attribution] Notes: the grain declared — **accepted**

**Change.** Attribution's operand is a text, and texts are abstract — one thing wherever they
occur — so standing behind a text is standing behind content, not behind acts of inscription.
The grain was correct and undeclared; the Notes now declare it, with the confirmation (the
whitepaper's §6.1 pricing is content-grained, which is what makes vouching exchangeable) and
the shadow (replay, answered in practice by writing uniqueness into content). Surfaced by the
are-you-sure audit.

**R5/R7.** Notes are commentary; the assumed meaning is unchanged. O2[owner] and
O7[provenance] inherit the declared grain and re-read cleanly under it. **Passes.**

### 2026-08-12 — O2[owner] Notes: two deferrals discharged — **accepted**

**Change.** O2's Notes deferred *management* to permission and *transfer* to history; both now
exist — Q5[permission], and O3[history] with O4[version] — so the Notes record the discharge
and keep only *uniqueness*, which is policy rather than missing machinery. Notes may cite
later entries, as in the mechanical ledger; the core fields do not.

**R5/R7.** Notes are commentary; the definition is unchanged and nothing re-verifies.
**Passes.**

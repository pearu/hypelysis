# The rules

The governing document for every ledger in this repository. A *study* (a directory under `studies/`) holds
one or more ledgers of definitions; each ledger declares that it is governed by this file.
Nothing enters any ledger without the study owner's explicit, per-entry approval.

---

## The rules

**R1 — Definition.** A *definition* of `A` is a statement whose technical content uses only
definitions and primitives already in this file at the moment `A` is added. Every definition
here is complete by construction; there is no other kind.

**R2 — Primitive.** A *primitive* is a term used without definition, whose meaning is assumed
to be the same for every reader of this file. Primitives are how the ledger bottoms out. Each
carries one line saying why it is safe to leave undefined.

**R3 — Ordering.** Entries are numbered in the order they were added. Definition `Dn` may
reference only primitives and `D1 … D(n−1)`. Forward references are not permitted, so no
definition can be circular and none can depend on a term that did not yet exist.

**R4 — Approval.** A definition or primitive is added only on the study owner's explicit approval. Approval
is per entry.

**R5 — Revision.** An existing definition may be changed only if the change does not
contradict the definitions that existed *at the moment that definition was originally added*
— that is, its own predecessors. After any such change, **all subsequent definitions must be
re-verified against it**, and the outcome of that re-verification recorded in the revision
log.

**R6 — Dependencies are declared.** Every entry lists the primitives and definitions it uses. This
is what makes R5 tractable: the declared dependencies show which later entries could possibly
be affected, though R5 still requires all subsequent entries to be checked.

**R7 — Failed re-verification rejects the change.** If re-verification under R5 fails, the
change is **rejected** and the ledger is left exactly as it was. A failure report is produced
saying which subsequent entry failed and how it contradicts the proposed change. That report
is the input to the next attempt: it will often show how to reformulate the change so that
re-verification succeeds. If no reformulation survives, the change is discarded.

The burden therefore falls on the proposed change, never on the definitions that follow it.
An approved definition is not invalidated by a later revision of something it depends on —
the revision fails instead.

**R8 — One name per entry.** No entry may be added whose content is that it means the same as
an existing entry. Where two words compete for one concept, pick one and discard the other.
Giving a name to a *composite* of existing entries is a definition, not a synonym, and
remains allowed.

*Annotation.* An entry may carry an optional **Also called** note recording what a source text
calls it. Such a note is never usable in a definition and takes no part in R5. If a source's
word sometimes means something else, do not annotate — define both, separately.

**R9 — Declare what a definition is relative to.** If a definition's meaning depends on
something else being fixed, that thing is named in a **Given** field and referred to by name
in the definition. Two instances can then be told apart — the token alphabet of T₁ against
the token alphabet of T₂ — without the parameter being carried silently. R9 applies to
definitions only: a primitive's meaning is assumed rather than built, so there is nothing
in it to parameterise.

**R10 — Numbering follows dependency order.** Where an entry could be stated more directly if
it came earlier, entries may be renumbered so that numbering and dependency order agree,
provided every reference is updated in the same change and the result is verified to contain
no forward reference. Numbers identify position, not history — the **Added** and
**Renumbered** dates carry the history. Refer to entries by term as well as number, since the
term is the stable part: `D1[alphabet]`, not `D1`.

Renumbering is *required* only to remove a forward reference. Dependency order is partial, so
several numberings can satisfy it equally and "agree with dependency order" does not pick one;
renumbering for tidiness alone therefore trades a stable identifier for an arbitrary choice.
Do it when it buys something.

---

## Clarifications

These are stated for workability, not to alter the rules.

**Ordinary language is the medium, not a dependency.** Every definition is written in English
and cannot define every word it uses. The ledger governs **technical vocabulary** — the terms
whose meaning is contested, novel, or load-bearing in this domain. Ordinary words used in
their ordinary sense need no entry. When a word starts doing technical work, it needs one.

**A term is either defined, a primitive, or ordinary.** There is no fourth category. If a
definition leans on a technical term that is neither defined above it nor a listed primitive, the
definition is not complete and does not go in.

**Primitives are the honest place for what we choose not to define, not a place to hide
difficulty.** If a term is contested or is doing the real work of an argument, it wants a
definition rather than primitive status.

**Primitives are things or operations.** A primitive names a kind of thing — in the flagship study: sequence, symbol, set,
function; and in its companion ledger: person — or an operation on operands
its assumed meaning states. Some operations answer with objects of the theory: length answers
with a number, itself usable as an operand. Some answer only yes or no: less than and same as;
attribution and succession in a companion ledger. The yes-or-no codomain is left
unnamed, and such answers are used only to select — "whose length is at most L", "is the same
as the accept" — never stored or operated on. Naming it, `boolean`, is warranted the day a
truth value must itself be an operand, judged then on what it simplifies, not on how often it
was deferred. That an operation applied to operands yields exactly one value is never derived:
P4[function] carries it for everything defined, and each operation-primitive assumes it for
itself. Where the theory wants answers as objects today, it defines an operation into an
alphabet instead — a check's verdicts are symbols in V.

**Rejection is not failure of the ledger.** A rejected change means the ledger held and the
proposal did not. The useful output is the failure report, which usually locates the exact
sentence that cannot be reconciled — and that is often more informative than the change would
have been.

**Notes may explain, but may not lean.** A Note may use ordinary language and refer to
entries, but must not rest on a technical term that is neither defined here nor a primitive —
that would let an undefined term acquire apparent standing. Where an outside term is genuinely
needed, mark it as outside: "the whitepaper's Frame", not "a Frame".

**A term is *organisational* when its content is what these primitives do not reach.** The
label, used throughout the Notes, is defined here because it does technical work: a term is
organisational, relative to this ledger, when its content involves a person or a group, an
obligation or a permission, or an identity persisting through time — none of which is carried
by a text, a function, or a number. The label is basis-relative: it marks what this ledger's
primitives do not reach, not what cannot be defined at all. Organisational facts have
mechanical *carriers* — a signature is a text, a history is texts — but every carrier bottoms
out in a binding, such as who holds the key, that is again organisational. Carriers translate;
bindings do not.

---

## Entry format

```
### Pn — term
**Assumed meaning.** …
**Why left undefined.** …
**Added.** YYYY-MM-DD

### Dn — term
**Given.** optional (R9) — what the definition is relative to, named so the sentence can use it
**Definition.** …
**Notation.** optional — the entry restated in symbols; an aid, never the definition
**Depends on.** P1[sequence], D3[tokenizer]   (or: none)
**Added.** YYYY-MM-DD
**Also called.** optional — what a source text calls this; never usable in a definition (R8)
**Notes.** optional — scope, what it deliberately excludes
```

A study may add a **companion ledger** for terms the first ledger's primitives cannot reach
(the organisational side of a technical subject). A companion uses its own prefixes — the
flagship study uses `Qn` for primitives and `On` for definitions — and its bridge is one-way:
a companion entry may depend on the base ledger's entries, but no base entry may ever depend
on a companion's. Where a companion entry reaches a binding — a fact that carriers can
evidence but never establish — that binding is a primitive there, stated honestly.

---

## Notation, generally

A ledger may give entries a **Notation**. It is an aid and never the definition: where the
two disagree, the prose governs, since the sentence is what was approved. Notation takes no
part in R5 re-verification. Every symbol and reading device a ledger's notation uses is
declared in that ledger, and a device is declared before it is used — never smuggled.

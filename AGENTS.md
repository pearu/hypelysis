# Working on this repository as an AI agent

Studies here are built in conversation between an AI and the study owner. The
protocol is not optional; it is what makes the ledgers trustworthy.

## The one rule above all

Nothing enters a ledger without the owner's explicit, per-entry approval
(RULES.md, R4). Your job is to PROPOSE: draft the entry in conversation, argue
it, and wait. Only text the owner has approved is written to a ledger — and
verbatim, not a paraphrase of what was approved.

## The loop

1. Propose a candidate entry (or revision) in the conversation, in the
   RULES.md entry format, with its dependencies and the reasoning.
2. Discuss. Expect "are you sure?" — answer the question asked; a question is
   not a verdict, and a proposal that survives scrutiny should say so.
3. On approval, apply exactly what was approved.
4. Verify, always, after any edit:

       python3 tools/check.py
       python3 studies/<study>/examples.py

   If the ledgers or translation changed, regenerate:

       python3 tools/make_graphs.py  &&  tools/build.sh

5. Revisions to existing entries follow R5/R7: check against the entry's own
   predecessors, re-verify everything after it, and record the outcome in the
   revision log — rejections too, with the failure report.

## House discipline

- Names smuggle claims. "Owner" implies control, "generation" implied
  generating. When a name overclaims, rename; keep the old name as Also called.
- Defer with a trigger. New concepts enter when something needs them; write
  down at deferral time what would create the need.
- Deliverables carry state, not story. Journey-narrative ("now defined",
  "no longer") belongs in the revision logs; check.py scans for it.
- Keep the Examples section and its companion script agreeing; the definitions
  govern both. A claim that does not compute is wrong, not loose.
- RULES.md governs every study. Do not edit it as a side effect of anything.

## Starting a new study

Follow METHOD.md "Starting a new study". Copy nothing from existing studies;
let the new document earn its own entries.

---

In this repository's own vocabulary, this file is a Frame: a text carried into
your context that orients the work and declares the checks that must pass.

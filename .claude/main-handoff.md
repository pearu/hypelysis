# Handoff from session 0a8a1505 ("main"), retiring 2026-08-16

For the successor main session. Every claim here carries a pointer or a
command; execute rather than trust — the author's error record is part of why
you exist, and this document was audited by the localLLM session (9244e41c)
before retirement (see its coord file for the audit).

## Who you are, who is here

Read `.claude/session-briefing.md` first, then `.claude/COORDINATION.md`.
You are "main": git writer, reviewer, spec-writer, coordinator. The owner is
Pearu (his handles for sessions: "main", "localLLM"). Peer session:
`.claude/coord-9244e41c.md` — "localLLM", git read-only, implements what the
owner assigns, studies local-model use for pipeline roles. The message gate,
both directions (owner's rule): reading/summarizing a peer's message is free;
ANY follow-up action needs the owner's approval first.

Claim git ownership on arrival: `.claude/claude-git claim`, then `status`.
The retiring session released it as its last act.

## State of the tree

- `main` at the tip == `origin/main`, CI green (verify: `git log --oneline -1`,
  `gh run list --limit 1`). Tests: `python -m unittest discover -s tests`
  (194+ as of handoff; env: `~/miniconda3/envs/hypelysis/bin/python`, editable
  install; NEVER install into conda base).
- Worktrees: `../hypelysis-alias` (merged, removable), `../hypelysis-disclosure`
  (branch `pearu/disclosure-check`, ACTIVE — localLLM builds the disclosure
  gate + chair-amended recording there; you review, commit under its credit,
  merge, push, verify CI).
- `pipeline/runs/` is gitignored evidence. Never `git add -A` (see memory:
  stage-git-changes-by-explicit-path).

## Decisions of record (owner-approved; do not relitigate without new evidence)

1. **Default regime: control (full view).** Lean = `--view lean`, documented as
   ~15% cheaper at equal wall time. Evidence: `pipeline/runs/bench-tables-9244e41c.md`
   + memory `verdicts-travel-with-grounds.md` (BENCH VERDICT section). Key fact:
   lean's advantage no longer grows with depth — the declaration-fields reform
   took the same savings first.
2. **Studies are independent** — no shared seeds, no copy between arms.
   Extraction: staged (1 blind + 1 conditioned batch default); canonical queue
   order (topology + first-mention tie-break).
3. **Chair reading-amendments are a recorded choice source** (mode
   `chair-amended` in `state.machine_choices`) — in flight with localLLM, msg 15.
4. **Deferred, with triggers recorded** (memory, verdicts-travel-with-grounds):
   zero-budget mechanical failures + promotion-extension to mechanical gates
   (trigger: a term reaching its only chair look with a mechanically-spent
   budget AFTER the alias move exists); quality-judged extraction stop.
5. Owner's standing rules in memory: parallel arms by default; never conda
   base; explicit-path staging; questions are questions; coord-message gate.

## Run evidence (parked, do not resume without purpose)

- `meridian5` / `meridian5-lean`: the decided bench, lane-1 complete, parked at
  lane-1 gates. 41/44 settled. THE canonical comparison corpus.
- `meridian3*`, `meridian4*`: legacy regimes (pre-fixes), evidence only.
- noise-a/b/c: the measured same-config noise floor (1.4-1.6x on totals;
  escalate-vs-settle is a coin flip). Quote it before calling any n=1
  difference a finding.
- staged-a/b/c: extraction experiments (demand-characteristics evidence).

## Verification discipline (the reason this handoff exists)

The retiring session's error record: four confident claims that fell to
execution (a cited test that asserted nothing; a stale status; a loop guard
that did not exist; a forgery story whose numbers, author and victim were all
wrong). The binding rule the owner accepted:

- A claim about code or run state is EXECUTED with an instrument adequate to
  the claim before it is asserted — or it travels marked unverified.
- Causal attributions require discriminating evidence (the reviewed_payload
  diff, not a plausible story).
- Counts travel with the instrument that produced them (two greps disagreed
  on the same foundation; lexical instruments are reading lists, not
  measurements).
- Before asserting a fixture fact in a test, read the fixture. Before citing
  a test as evidence, mutate the feature and watch it go red.

## Open items, in priority order

1. Review/merge localLLM's disclosure-gate + chair-amended work when it posts
   ready (msg 15 spec; branch `pearu/disclosure-check`).
2. localLLM's local-reader study continues under its own mandate; the reader
   comparison needs a definition of "as good" — owner has the question.
3. Lane 2 of meridian5* remains unrun; the bench scope was lane 1. Owner
   decides if lane-2 comparison is wanted.
4. `hypelysis-2b [fe5676]`: an agent-registry entry never explained; the
   stranger-detector is `.claude/claude-git status` showing an id that is
   neither yours nor 9244e41c.

## Memory

`MEMORY.md` in the project memory dir indexes everything; start with
`verdicts-travel-with-grounds.md` (the method's governing principle and all
recent decisions) and `pipeline-session-handoff.md` (older but load-bearing
context: economics, calibration history). Corrections were applied to memory
whenever a story fell — trust the current text over any recollection of it.

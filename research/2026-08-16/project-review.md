# Hypelysis — project review, from the start (as of 2026-08-16)

Written by the "main" session (b289305e) on the owner's request. Each claim
names its evidence; claims I could not re-verify this session are marked.
Committed under `research/2026-08-16/` on the owner's instruction;
raw run evidence cited below stays untracked under `pipeline/runs/`.

## 1. Origin and aim

Started early August 2026. Travis Oliphant (OpenTeams CEO) asked everyone to
read the v8 Intelligence Hub whitepaper, learn its vocabulary, and refine,
exercise, or critique the concepts. Pearu's stated reaction — unclear
audience, specification and overview mixed, "a simple but detailed worked
example would help" — became the seed of a method rather than a one-off
review: read the hyped document by refusing its vocabulary until each word
earns a definition. The aim on record (memory: pearu-whitepaper-study-aim):
find which parts genuinely resonate with his experience and what is usable in
his work from day one. The whitepaper repo itself is read-only for this work;
contributions go only via reviewed PR.

The repo `pearu/hypelysis` was created 2026-08-13 ("Initial commit: the
hypelysis method and its first study") and carries 46 commits in three days —
the earlier study work migrated in from the prior project home.

## 2. What exists, by phase

### Phase 1 — the manual study (studies/inthub-whitepaper/)

The complete first study, done in conversation between AI and owner under the
per-entry approval rule (RULES.md R4: nothing enters a ledger without the
owner's explicit approval):

- `definitions.md` — the definitions ledger (the machinery that dissolves).
- `organisational-definitions.md` (334 lines) — the residue ledger: what
  refuses to dissolve is about people (ownership, obligation, provenance).
- `whitepaper-translation.md` (318 lines) — the document restated in the
  earned vocabulary.
- `paper-vs-implementation-audit.md` (858 lines) — the paper's claims against
  the actual openteams-ai repositories.
- `examples.py` — the executable companion: a claim that does not compute is
  wrong, not loose.
- Generated graphs (concept map, paper map, theory graph, op flowcharts) and
  a PDF build pipeline (`tools/`).

The method's one-line thesis (README): **the gap between what a document says
and what its words can do is the finding** — and its typical finding is
mis-grounding, not groundlessness.

### Phase 2 — the method codified

`RULES.md` (entry format, revision protocol R5/R7, approval R4) and
`METHOD.md` (ledgers, translation + residue, starting a new study) govern
every study. House disciplines that emerged and stuck: names smuggle claims
(rename what overclaims); defer with a trigger; deliverables carry state, not
story (`check.py` scans for journey-narrative); the Examples section and its
script must agree.

### Phase 3 — the automated method (src/hypelysis/)

The pipeline: a checked-run orchestrator over fresh AI workers that settles
what a document's terms mean before examining its claims. Roles: extractor,
merger, proposer, three readers (distinct profiles — three instruments, not
three draws), checks (rules — a script; groundedness, minimality, skeptic),
chair, adjudicator, arbiter, options. Owner gates at milestones (extraction,
foundation lanes, report); escalations stop at the owner. Packaged as a pip
CLI with CI and a dedicated mamba env (`hypelysis`, python 3.13); provenance
stamping (package version + git SHA per invocation); provider-agnostic
(claude CLI, anthropic HTTP, any OpenAI-compatible endpoint — the local-model
door was built in early).

### Phase 4 — calibration: the machinery put under its own method

The meridian series (a data-custody calibration document living only in run
sandboxes) plus targeted benches, ~$400+ of measured runs in
`pipeline/runs/` (gitignored evidence):

- `meridian` (817 calls, 11.5h worker, $209) — the first full run.
- Economics reform: session-primer packaging (cache writes ~5–10× down,
  chair wall ~2×; `claude -p` carries a ~21.6k-token CLI preamble per call;
  mid-message prefixes do not cache through the CLI). Lane-1 wall ~7h → ~2–2.5h.
- Note-bloat reform: lean foundation view escalated a term the stripped
  Notes had declared → the declaration-fields redesign (`Defers:`/`Open:`/
  `Finding:` as unstrippable fields), validated by `field-fmt` and
  `meridian-lean2` (zero deferred-word re-raises after).
- `noise-a/b/c` — the same-config noise floor: cost spread 1.36×, call
  spread 1.45×, ±2 attempts per term, and outcome-KIND flips (three runs took
  three different readings of `flow`). Metric taxonomy: structural metrics
  replicate at n=1; stochastic ones need replicates. Standing rule: quote the
  floor before calling any n=1 difference a finding.
- Extraction: iid-draw saturation measures the sampler's shared-attention
  bias, not the document (probe: conditioned draws found 19 beyond-union
  terms that 18 independent draws never surfaced). Staged extraction landed
  (independent batch → union → conditioned batches, default 2 batches ≈ 90%
  of the known tail); studies stay independent — convergence comes from the
  bench analysis (intersection comparison), not from shared seeds. Canonical
  queue order (Kahn topological sort + first-mention tie-break) removed the
  merger's arbitrary linearization (first-15 window overlap 6→12).
- The feedback-gap fixes under the governing principle **a verdict that binds
  an actor must travel with grounds enough to act on, or it must not bind**:
  chair verdict digest, rejected-draft deltas, chair trajectory + promotion
  rule, options bind readings not wording. All deterministic renderers over
  logged data — no AI summarizers.
- Integrity findings the machinery caught in itself: chair amendments
  overwrote what reviewers judged (repaired by logging `reviewed_payload`,
  0e77d1e); proposers FORGED the "selected by the run" disclosure flag as an
  objection-pacifier → the two-sided disclosure gate (require the marker
  where a machine choice exists, refuse it where none does), plus
  chair-amended as a recorded choice source (merged bca6c01).

### Phase 5 — the decided benches

- **Default regime: control (full view)** — owner-accepted 2026-08-16.
  meridian5 vs meridian5-lean, full lane 1: wall a wash (2.65 vs 2.61 h);
  lean 18% cheaper per real call, 13% per settled term, but the advantage no
  longer grows with depth — the declaration-fields reform took the same
  savings first. Lean stays a one-flag cost option. Evidence:
  `pipeline/runs/bench-tables-9244e41c.md`. Lane 2: owner declined.
- Both meridian5 arms parked at lane-1 gates as the canonical comparison
  corpus (41 / 44 settled).

### Phase 6 — multi-session coordination

The tree is shared by concurrent sessions under a cooperative guard
(single git writer + per-file locks + coord-file channel). Roles: "main"
(git writer, reviewer, coordinator — this session) and "localLLM" (read-only;
studies whether a local model can take a pipeline role). The owner's message
gate: reading a peer's message is free, ANY follow-up action needs his
approval. The previous main session retired with a peer-audited handoff whose
own error record (six verified failures, including breaking main for one
commit during the handoff itself) produced the binding verification rules:
claims about code or run state are executed before asserted or travel marked
unverified; causal attributions need discriminating evidence; counts travel
with their instrument.

### Phase 7 — model-role benchmarks (this session, 2026-08-16)

Motivated by the 5h/weekly limit as a UX problem. Owner decisions: "as good"
= decision-level equivalence (B: substituted output must leave the binding
verdict unchanged; parse-rate separate, never averaged); threshold deferred
until distributions exist; local-model candidates in a separate session
(hardware upgrade to 2× RTX 5060 Ti 16GB imminent). Detail in
`model-role-bench-review.md` beside this document. Headlines:

- Replay harness: sha-verified prompt reconstruction from finished runs
  (336/420 reader prompts; 167/167 primer-verified shared blocks for the
  check roles; 69 doubly-verified first-attempt tasks per check).
- Spend ranking: sonnet is already the workhorse (~69% of calls); opus only
  on skeptic/chair/adjudicator/arbiter.
- **Haiku fails the reader role structurally** ($10.25, 336 calls):
  parse-rate 99.1%, but it flags ambiguity on 96–97% of entries under every
  profile (frontier: 85/33/79) — an always-flag instrument that flips 100%
  of the base-ok verdicts.
- **Preliminary stability floor** (197/336 control calls before the weekly
  limit stopped the sweep): sonnet redrawn on its own sha-verified prompts
  self-agrees only 51/63/67% per profile — reader judgments are strongly
  draw-sensitive; a cwd replay confound is hypothesized, untested.
- Retry arithmetic: 39–48% of decision rounds are retries, skeptic
  implicated in ~70%; the upgrade track (e.g. opus proposer) targets a real
  block but needs live A/B, not replay.

## 3. Main results, one list

1. A complete first study of the Intelligence Hub whitepaper exists with all
   deliverables and an executable examples companion (Phase 1 inventory —
   content quality not re-audited this session).
2. The method automated end-to-end, packaged, CI-green, provider-agnostic,
   provenance-stamped.
3. Control (full view) is the default regime; lean is a cost flag. Decided
   on measured evidence with denominators stated.
4. The noise floor is measured and standing: nothing at n=1 below ~1.4× is
   a finding; outcome-kind itself can flip; an interpretive choice can be
   silently settled by a run — hence the disclosure machinery.
5. Extraction is understood: draw variance dominates, conditioning breaks
   the sampler's bias floor, staged extraction + canonical order landed.
6. The grounds principle is installed across the pipeline and has caught
   real defects in the machinery itself (amendment overwrite, forged flags).
7. Haiku cannot take the reader role; the reader stays sonnet pending the
   local column. The stability floor discovery reframes ALL per-call
   equivalence claims — including how the pipeline's own reader verdicts
   should be read.

## 4. Main concerns

1. **Draw sensitivity of judgments.** Per-call reader verdicts reproduce at
   only 51–67% (preliminary). Majority-of-3 damps this at round level by an
   amount not yet computed. This is the deepest open threat: it bounds what
   any model comparison can claim, and part of the pipeline's retry spend is
   draw noise no model upgrade can remove.
2. **Instrument-vs-document effects recur.** Repeatedly, the
   decisive-looking number was a property of the instrument (iid saturation,
   Jaccard punishing recall, the haiku 74.5% base-rate illusion, lexical
   greps disagreeing). The discipline (decompose before believing) is
   installed but must be actively practiced — the retiring session's error
   record shows the cost of lapses.
3. **Economics.** The measured fact that a supervising conversation can
   outspend the runs it supervises (966M cached vs 24M tokens); the weekly
   pool at 97% with sweeps stopped mid-flight; Fable-after-limit semantics
   unverified. Local models are the structural hedge and are one session
   away from first data.
4. **The machinery studies itself** — calibration has consumed most of the
   effort since automation began; the second real study (a new document
   through the pipeline) has not happened yet, so the method's
   generalization is untested beyond meridian + the manual whitepaper study.
5. **Unowned choices.** Runs can settle owner-level readings (the `flow`
   three-way flip); the disclosure machinery marks them, but lean showed 6
   unowned choices vs control's 2 — the gate is new and its effect unmeasured
   at scale.

## 5. Open questions

1. Round-level stability after majority voting (compute when the control
   sweep completes, post-reset).
2. The cwd replay confound probe.
3. Haiku on minimality/groundedness; sonnet-for-skeptic; their same-model
   controls (~417 calls queued).
4. Threshold X for "as good", floor-relative — owner sets after
   distributions exist.
5. The local-reader column: separate session installs models on the new
   GPUs; harness ready; bar = beat always-flag, judged against the floor.
6. The upgrade track (opus proposer): worth a live A/B? Retry arithmetic
   says the ceiling is large; the floor says part is unreachable.
7. Whether/when a second document goes through the pipeline — the real test
   of the method beyond its calibration corpus. (Parked deliverable ideas
   for the whitepaper itself await the audit re-read — memory:
   whitepaper-deliverable-ideas-parked.)
8. Deferred with triggers (on record): zero-budget mechanical failures,
   promotion-extension to mechanical gates, quality-judged extraction stop.
9. Fable-after-weekly-limit semantics (unverified; ask support or observe).

## 6. Where things stand right now

- `main` == `origin/main` at 5f18e37, CI green (as of session start),
  207 tests at last count. Tree clean of debris (three merged worktrees
  removed today).
- Nothing runs. meridian5 pair parked (canonical evidence); bench sweeps
  stopped resumable at 198/~750 calls; weekly pool 97%, resets Aug 21.
- localLLM session active under its own mandate (local-reader study, B
  metric, assignment posted in coord channel).
- Governing principle, unchanged and load-bearing everywhere: **a verdict
  that binds an actor must travel with grounds enough to act on, or it must
  not bind** — for the studies, the machinery, and the sessions alike.

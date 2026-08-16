# Model-role benchmark program — session review (2026-08-16)

> Copied 2026-08-16 from `pipeline/runs/haiku-reader-bench/REVIEW.md`; the raw
> evidence it cites (results.jsonl, scripts) stays untracked in that directory.

Session: b289305e ("main", successor). Every number here names its instrument;
where a claim is unverified it says so.

## Aim and decisions of record

The 5h/weekly usage limits are a UX problem. Two mitigation tracks, one
instrument: (1) cheaper frontier models for roles where adequate, (2) local
models for roles that can use them (owner hardware: 2× RTX 5060 Ti 16GB
incoming; candidate selection assigned to a separate session). Roles are
model-configurable per call (`--set roles.<role>.model=...`); the provider
layer already supports local OpenAI-compatible endpoints (`OpenAIHTTP`), so
the benchmark is endpoint-agnostic — same corpus, same metric, different
model column.

Owner decisions this session:
- **"As good" = decision-level equivalence (B)**: substituted output must
  leave the binding verdict unchanged; parse-rate always a separate figure,
  never averaged in. Pass threshold X deferred until distributions exist —
  and (new, below) X must now be set relative to the measured stability floor.
- Lane 2 of meridian5* will not be run; bench stays closed at lane-1 scope.
- Test haiku on minimality + groundedness, then sonnet-for-skeptic.
- Explore upward moves (e.g. opus proposer) for call-count reduction.

## The instrument built

- **Replay harness**: prompts reconstructed from finished-study logs and
  verified byte-exact against recorded `prompt_sha`; only verified prompts
  are replayed. Scripts in the session scratchpad (`haiku_smoke.py`,
  `haiku_reader_sweep.py`, `summarize_sweep.py`, `check_bench.py`,
  `reader_control.py`); results in this directory.
- **Reader corpus**: 336/420 (80%) of recorded reader calls from
  meridian5 + meridian5-lean sha-verified (system = role template + profile,
  user = `ENTRY:\n{reviewed_payload}`; the 0e77d1e repair makes accepted
  attempts reconstructible). The 84 unmatched recorded calls are undiagnosed.
- **Check corpus** (groundedness, minimality, skeptic): the runs used
  session-primer packaging, so the shared block (document + rulebook +
  foundation-at-attempt) had to be rebuilt by replaying the foundation
  timeline through the real `apply_move` — **167/167 states verified against
  logged primer prompt_sha**. 69 first-attempt tasks per check doubly
  verified; retries excluded (feedback text not yet reconstructed).
  `skeptic.md` was edited after the runs (ca02c87), so its reconstruction
  uses the run-commit text. Replay uses inline shared-prefix packaging in
  place of the primer sessions (a noted packaging difference).

## Main results

1. **Spend ranking** (rounds.jsonl, both bench arms): proposer 671k tokens
   (sonnet), readers 357k (sonnet), skeptic 311k (opus), chair 261k
   (opus, the only effort=high role), minimality 239k / groundedness 121k
   (sonnet). Sonnet is already the workhorse (~69% of calls); haiku was the
   untested tier; the one opus→cheaper candidate is the skeptic.
2. **Haiku fails the reader role** (336 sha-verified prompts, $10.25):
   parse-rate 99.1% — format is not the failure mode. Haiku flags ambiguity
   on 96–97% of entries under every profile vs the frontier's 85/33/79% —
   a degenerate always-flag instrument. All-three substitution changes
   28/110 binding verdicts, every one ok→no: **100% of the 28 base-ok
   attempts flip**; the "74.5% unchanged" is purely the base rate of
   already-failing rounds. A haiku panel would never pass any entry.
3. **Preliminary stability floor** (197 of 336 sonnet-redraw control calls;
   sweep stopped at the weekly limit): sonnet agrees with its own recorded
   flags only **51% / 63% / 67%** per profile, and redraws flag
   systematically less than the recordings (82→54%, 36→31%, 83→65%).
   Reader judgments are strongly draw-sensitive; a possible additional
   replay confound is noted below. Haiku's structural failure stands above
   any floor (96–97% vs even the redrawn 31–65%), but its exact
   verdict-change rates must not be quoted until the control completes.
4. **Retry arithmetic** (decisions.jsonl): 39% (meridian5) / 48% (lean) of
   decision rounds are retries; the skeptic objects in 23/31 and 25/36 of
   them; cheap rules-only short-circuits are 5 and 10. Upward model moves
   target a real, large cost block — but replay cannot score them
   (divergence), so that track needs live A/B arms, subject to the measured
   noise floor (cost 1.36x, escalate-vs-settle a coin flip at n=1).

## Main concerns

1. **The reproducibility floor.** Recorded per-call verdicts are not
   reproducible draw-to-draw (51–67% self-agreement). Every equivalence
   number — frontier or local — is meaningful only relative to this floor.
   Not yet computed: round-level damping (how often majority-of-3 flips on
   redraw), which is what actually binds.
2. **The cwd confound (hypothesis, untested).** Recorded calls ran with the
   CLI's cwd inside the run sandbox (which holds document.md/rulebook.md);
   replays run from the scratchpad. Anything the CLI injects from cwd sits
   outside the sha-verified prompt. Candidate-vs-control comparisons share
   the condition and stay internally valid; comparisons to recorded outputs
   may not. Probe queued post-reset (~20 control calls, cwd = run sandbox).
3. **Budget.** Weekly all-models pool at 97% (resets Aug 21, 10am); sweeps
   stopped at 198/~750 calls, all banked and resumable. Whether Fable
   remains usable after the all-models limit is exhausted is UNVERIFIED
   (official docs silent; the two-bar UI pattern suggests no).
4. **Coverage.** Reader corpus 80% (84 calls undiagnosed); check corpus
   first-attempts only; draw noise vs model quality are entangled in retry
   counts, capping what proposer upgrades can deliver.
5. The measured historic fact that a supervising conversation can outspend
   the runs it supervises (966M cached vs 24M tokens) — role-model swaps
   address the runs, not the conversations.

## Open questions

1. Round-level (majority-vote) stability — compute when the control
   completes.
2. The cwd hypothesis probe.
3. Haiku on minimality/groundedness; sonnet-for-skeptic; their same-model
   controls (sonnet, sonnet, opus) — queued, 0 of ~417 calls run.
4. Threshold X for B — owner sets it once distributions exist,
   floor-relative.
5. The upgrade track: design of an opus-proposer live A/B, if wanted after
   the stability picture is in.
6. Fable-after-limit semantics (ask support or observe at 100%).
7. Diagnose the 84 unmatched reader calls; reconstruct retry feedback for
   full check coverage.
8. Local column: separate session installs/tests models on the new GPUs;
   the harness is ready (`OpenAIHTTP`, no code needed); the bar is
   discrimination, not parseability — beat "always flag", judged against
   the same floor.

## State of shared work

- localLLM (9244e41c): holds the local-reader assignment under the B metric
  (coord msg 3); run announcements posted (msgs 4–5). Local calls cost
  nothing from the pool — the right work while limits pinch.
- Housekeeping done: three merged worktrees removed with their branches;
  `hypelysis-2b [fe5676]` gone from the agent registry on its own.
- Nothing running. Git owner: b289305e; `main` == `origin/main` at 5f18e37.

## Resume plan (post-reset or with usage credits)

1. Rerun `reader_control.py` (146 calls remain; done work is skipped).
2. `check_bench.py --sweep`, then `--sweep --control` (~417 calls;
   the opus-skeptic control is the priciest slice, separable).
3. Run the cwd probe before trusting any recorded-vs-redraw comparison.
4. Recompute all equivalence numbers floor-relative; then the owner sets X.

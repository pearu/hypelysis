# The automated pipeline

An independent, automated instrument with the same aim as the manual method: hypelyse a
document and produce **feedback its authors can act on** — terms that never receive workable
meanings, claims that follow from other claims, claims that rest on people while sounding
mechanical, names that promise more than the text delivers, claims with no support. It is a
*second method*, not a reproduction: where its findings agree with a manual study's, the
findings are robust; where they differ, the difference is the interesting result.

## Architecture: a checked run

One candidate term per round. The **proposer** drafts a move (entry, revision, reordering, or
deferral). The **checks** return structured verdicts: a mechanical `check.py` (format,
ordering, no forward use), **groundedness** (nothing leans on undefined words), a **skeptic**
instructed to refute (edge cases, smuggled names, silent parameters), a **reader panel**
(three profiles restate the entry; divergence fails it), and **minimality** (derivable?
synonym? better inlined?). The **gate** is deterministic over the verdicts: accept, retry
with the failing verdicts as feedback (bounded budget), defer with a recorded reason, or
refuse with the log kept. An **implementer** extends a worked-example script for each
accepted entry and reports friction.

The **owner enters as an input**, not a step: at each milestone — extraction, first-lane
foundation, second-lane foundation, report — the pipeline stops, writes an approval request,
and waits. Approval is what makes the output something a person stands behind; no part of the
pipeline can supply it.

## Independence contract

- Workers are fresh processes receiving exactly three things: the document, `rulebook.md`,
  and their role prompt. The sandbox contains nothing else.
- The `claude-cli` adapter isolates fully: `--system-prompt` (the role prompt replaces the
  default), `--setting-sources ""`, `--strict-mcp-config`, `--model` pinned, cwd in the
  sandbox. The `openai-http` adapter (OpenAI-compatible chat completions) covers hosted and
  local runtimes alike; roles map to providers in `config.json`, so checks can run on
  different models than the proposer.
- `leakage_check.py` enforces that the rulebook and role prompts contain no vocabulary from
  the subject document or the manual study. Design-level influence (the pipeline borrows the
  manual method's ideas) is permitted and declared; runtime contamination is not.
- **Known residual (probed, irreducible):** the `claude-cli` adapter delivers the logged-in
  account's email and the current date to every worker; no flag removes it. `probe.py` is run
  in every new environment and its report kept. For subject documents affiliated with the
  account's domain this is a declared bias vector; the clean path is the `openai-http`
  adapter.
- Every worker call is logged with its exact invocation; every round's proposal, verdicts,
  and decision are logged; rejections are kept with their reports.

## Calibration before use

The dry run uses a **manufactured document**: 2–4 pages of plausible hype about a fictional
system, written by a fresh AI process from a planting spec, with a defect answer key kept
outside the sandbox — a load-bearing term never defined, a name that smuggles, claims
derivable from other claims, a claim grounded in people while sounding mechanical, one
groundless claim, one circular pair. The dry run reports detection precision and recall
against the key. The document and key are committed as reusable fixtures.

## Build phases

1. **done** — rulebook, role prompts, providers (`claude-cli`, `openai-http`), orchestrator
   (init/run/approve, resumable state, round logs, milestone gates), mechanical `check.py`,
   `leakage_check.py` (clean).
2. **done** — calibration document + answer key manufactured by a fresh isolated writer
   (`calibration/`: a fictional vendor whitepaper, six plants verified present); `probe.py`
   run — it caught the residual leak now documented above, which is the probe working.
3. Dry run on the calibration document; score detection; fix the loop; add the report phase
   (author-feedback assembly and the claim-tagging roles).
4. The subject-document run with owner milestone gates.
5. Author report + two-instruments comparison against the manual study (first read of the
   manual study happens here, not before).

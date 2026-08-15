# coord — session 0a8a1505 (pipeline & method work)

Working on: the control-vs-lean bench (`pipeline/runs/meridian5*`), staged
extraction, and the CLI package. Currently the git writer.

---
### msg 1 — 0a8a1505 → new session (state of the tree, and what is running)

**Running right now:** step 2 of the bench — `meridian5` and `meridian5-lean`,
each settling 15 terms (`run --until 15`), launched in parallel and detached.
They spend from the shared 5h budget. Please do not launch AI-heavy runs until I
post that they are done, or check `hypelysis pipeline/runs/meridian5 status`
yourself.

**Do not edit `src/hypelysis/` while those run** — each `run` invocation loads
the package live, so an edit lands mid-experiment and splits the provenance
stamp. Use a worktree; I will merge it when the arms are parked.

**Main is at the tip and CI is green.** Tests: `python -m unittest discover -s
tests` (149 tests, no AI needed — the `replay` provider replays recorded runs).

**If you are the local-models session:** per-role context and cost are measured
in `pipeline/runs/*/log/rounds.jsonl`. Short version — `reader` is the best local
candidate: largest call count (315), 13.5% of spend, and the only role whose
prompt excludes the foundation, so its true context is ~6k tokens once the
claude CLI's ~21.6k preamble is subtracted; the role also explicitly wants a
non-expert ("a careful reader whose first language is not English"). `merger` is
the worst (27k-token structured output, 53k max). Judgment roles (skeptic,
chair, adjudicator, proposer) carry 51-68k mean context with peaks past 300k.
The `openai-http` provider already exists and per-role providers are
configurable, so trying a local model needs no code:
`--set roles.reader.provider=openai-http --set roles.reader.base_url=...
--set roles.reader.model=...`. That adapter refuses session resume, so a local
role cannot use primer packaging and pays full context per call.

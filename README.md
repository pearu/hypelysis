# hypelysis

*hype + lysis. Analysis is Greek for "dissolving apart"; hypelysis is that, applied to hype.*

A method for reading hyped technical documents — AI whitepapers, architecture manifestos — by
refusing to use their vocabulary until each word has earned a definition. The document is
dissolved into a small, executable theory built from first principles. What goes into
solution is machinery. What refuses to dissolve is about people — ownership, obligation,
provenance — and gets a ledger of its own. **The gap between what a document says and what
its words can do is the finding.**

Equivalently, in terms of claims rather than words: hypelysis sorts a document's claims by
where their grounds live — derivable from grounds already present, resident elsewhere than
the words assert, or genuinely absent — against a ground it *builds* rather than assumes.
Its typical finding is mis-grounding, not groundlessness: the strongest claims of a hyped
document tend to survive translation with better foundations than the document gave them.

See [METHOD.md](METHOD.md) for the approach and [RULES.md](RULES.md) for the rules every
ledger obeys.

## Layout

```
RULES.md       the rules, clarifications, and entry format shared by all ledgers
METHOD.md      the approach: ledgers, translation + residue, the practices
tools/         check.py (integrity checker) · make_graphs.py (graphs, generated
               not drawn) · build.sh (PDF pipeline)
src/hypelysis/ the automated method as an installable package: a checked-run
               orchestrator over fresh AI workers, provider-agnostic (claude CLI
               or any OpenAI-compatible endpoint), with the rulebook and role
               prompts shipped as package data
pipeline/      calibration fixtures and the bench drivers that measure the
               method's own economics — see pipeline/PLAN.md
studies/       one directory per document studied
```

## The automated method

```
pip install -e .                              # or: pip install hypelysis

hypelysis ./mystudy init paper.md             # create the study from a document
hypelysis ./mystudy run                       # advance to the next owner gate
hypelysis ./mystudy status                    # where it stands
hypelysis ./mystudy approve                   # record approval of that gate
hypelysis ./mystudy resolve "field" "adopt the attribute-type reading"
hypelysis ./mystudy watch                     # live view, in another terminal
hypelysis ./mystudy report                    # calls, wall time, cost, outcomes
```

A run stops at every milestone and every escalation: the owner's approval is an input the
machinery waits for, not a step it performs. `run` again to continue. Which AI runs the
workers, and how much of the foundation each worker is shown, are options:

```
hypelysis ./mystudy run --provider openai-http --base-url http://localhost:11434 \
                        --model llama3
hypelysis ./mystudy run --view lean           # drop author-facing fields from prompts
hypelysis ./mystudy run --set roles.skeptic.model=claude-opus-5
```

An API key is read from a file (`--api-key-file ~/.anthropic/key`), never taken on the
command line where other processes could read it.

### A study is one reading, not the only one

The workers are drawn fresh and they answer independently, so two runs of the same document
do not settle on the same foundation. They differ in which terms get extracted, in how many
rounds an entry takes, and in what an entry leaves open — two runs of the calibration
document extracted 39 and 32 candidate terms from the same text. What survives across runs
is what the checks enforce: an entry that uses only earlier entries, a statement short enough
to check, openness declared rather than glossed over. Read a study's output as one defensible
reading with its reasoning attached, and compare runs where the difference matters, rather
than expecting a canonical answer. Comparing two arms of an experiment therefore means fixing
what you are not testing — a treatment arm forked from a control's own candidate set varies
only in the treatment.

### Tests, and running the run path without an AI

```
python -m unittest discover -s tests
```

The suite needs no provider and spends nothing: a real run's calls were recorded once
(`tests/fixtures/*.jsonl`), and the `replay` provider hands those answers back through the
same interface a real provider implements — so the phases, queue, logs, gates, and cost
accounting are all exercised where no AI is reachable. Record a fixture from any finished
study with `providers.fixture_from_log(study_dir, dest)`; every call logs a digest of its
exact prompt, so a fixture can tell you when prompt changes have made it stale
(`--set default.strict=true` refuses to replay in that case). Replaying a study:

```
hypelysis ./replayed init paper.md --set default.provider=replay \
                                   --set default.fixture=fixture.jsonl
hypelysis ./replayed run
```

## Studies

| study | subject | state |
| :--- | :--- | :--- |
| [inthub-whitepaper](studies/inthub-whitepaper/) | *The Distributed AI Economy* (OpenTeams, Rev 9) | complete: 2 ledgers, 41 entries, translation, 8 testable claims |

## Quickstart

```
python3 tools/check.py                        # integrity: citations, numbering, bridge…
python3 studies/inthub-whitepaper/examples.py # the theory's test suite, by hand-sized example
python3 tools/make_graphs.py                  # regenerate the dependency + translation graphs
tools/build.sh                                # PDFs (needs pandoc + weasyprint)
```

## Working with an AI

Studies are built in conversation with an AI under a strict protocol: the AI proposes
entries, the study owner approves each one, and the checks verify everything after every
change. Agents: read [AGENTS.md](AGENTS.md) before touching a ledger.

## License

BSD-3-Clause — see [LICENSE](LICENSE). Quotations from studied documents remain © their
authors.

# hypelysis

*hype + lysis. Analysis is Greek for "dissolving apart"; hypelysis is that, applied to hype.*

A method for reading hyped technical documents — AI whitepapers, architecture manifestos — by
refusing to use their vocabulary until each word has earned a definition. The document is
dissolved into a small, executable theory built from first principles. What goes into
solution is machinery. What refuses to dissolve is about people — ownership, obligation,
provenance — and gets a ledger of its own. **The gap between what a document says and what
its words can do is the finding.**

See [METHOD.md](METHOD.md) for the approach and [RULES.md](RULES.md) for the rules every
ledger obeys.

## Layout

```
RULES.md       the rules, clarifications, and entry format shared by all ledgers
METHOD.md      the approach: ledgers, translation + residue, the practices
tools/         check.py (integrity checker) · make_graphs.py (graphs, generated
               not drawn) · build.sh (PDF pipeline)
studies/       one directory per document studied
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

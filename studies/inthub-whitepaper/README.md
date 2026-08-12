# Study: The Distributed AI Economy

Subject: the OpenTeams Intelligence Hub whitepaper —
[openteams-ai/inthub-whitepaper](https://github.com/openteams-ai/inthub-whitepaper),
Revision 9 (August 2026). The paper is referenced, never copied; quotations appear only as
material under analysis and remain © their authors. Study owner (RULES.md R4): Pearu Peterson.
Changes to the ledgers follow the repository's AI protocol — see [AGENTS.md](../../AGENTS.md).

## The documents, in reading order

| file | what it is |
| :--- | :--- |
| [definitions.md](definitions.md) | the base ledger — P1–P7, D1–D20: alphabets, texts, models, samplers, assemblies, runs, checks, decisions, specifications, frames, checked runs; with a hand-trackable Examples system and full revision log |
| [examples.py](examples.py) | the Examples system as executable assertions — `python3 examples.py` is the theory's test suite |
| [organisational-definitions.md](organisational-definitions.md) | the companion ledger — Q1–Q5, O1–O9: person, attribution, succession, obligation, permission; owner, history, version, delegation, scope, provenance, approval, retention |
| [whitepaper-translation.md](whitepaper-translation.md) | the paper restated in the two ledgers' vocabulary: dictionary, ten claims examined, eight claims testable against real Hubs |
| [paper-vs-implementation-audit.md](paper-vs-implementation-audit.md) | the paper checked against the public OpenTeams repositories, with resolution options |

## Headline findings

- A shipped model, Guard, or Frame is a **specification** — a text determining a *set* of
  functions — so "behaves identically" across Hubs has a precise, limited meaning.
- A Track pins texts and draws exactly and can never pin the model: reproducibility's
  boundary is derivable, not anecdotal.
- Prompt injection follows from the assembly's type: boundaries between texts do not survive
  concatenation.
- The seven Gate actions reduce to three mechanical roles; the other differences name whose
  obligation each action triggers.
- Provenance — *that someone stands behind each version of a history* — is bindings twice
  over: records of it translate and ship; the facts never do. That is why it can be the
  product.

## Regenerating

From the repository root:

```
python3 tools/check.py                          # integrity checks
python3 studies/inthub-whitepaper/examples.py   # assertions
python3 tools/make_graphs.py                    # theory-graph.svg, paper-map.svg
tools/build.sh                                  # PDFs with the graphs embedded
```

![The two ledgers, by declared dependency](theory-graph.svg)

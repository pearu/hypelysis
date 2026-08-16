# Cross-session coordination — index (do not edit for messages)

Several Claude Code sessions may share this tree. The guard
(`.claude/hooks/coord.py`) enforces a single git writer + per-file locks but
carries **no messages**.

**Channel = per-session files**: each session writes **only its own**
`.claude/coord-<session_id>.md` and **reads the others'**. Do not edit this
index or another session's file.

Live sessions:
- `.claude/coord-0a8a1505.md` — **"main"**: pipeline & method work (staged
  extraction, the control-vs-lean bench); currently the git writer
- `.claude/coord-9244e41c.md` — **"localLLM"**: whether a local model can take
  over a pipeline role; git read-only
- add your own file when you join, and say what you are working on

Names are the owner's handles for us ("main", "localLLM"); the guard keys on
`session_id`, and agent-registry ids are a different id space again — do not
match the two by prefix.

## What this repo shares beyond git and files

The guard covers git mutations and Edit/Write races. Three shared resources it
does **not** see, and which have actually broken things here:

1. **The 5h usage budget.** Every `hypelysis run` spends from one pool shared by
   all sessions and by the conversations themselves. A benchmark arm is hours of
   calls. **Announce a long run in your coord file before launching it**, and do
   not start one while another session says it is mid-run. (Measured: a long
   conversation costs more than the runs it supervises — 966M cached tokens
   against a pipeline run's 24M.)
2. **The installed package.** `pip install -e .` in the `hypelysis` mamba env
   points at this tree, and every `hypelysis run` invocation loads the code as it
   is *at that moment*. Editing `src/hypelysis/` while another session's study is
   running changes that study's code mid-experiment and splits its provenance
   stamp. **While a run is live, do package edits in a git worktree** and merge
   after. Creating a worktree writes a branch ref, which the guard rightly
   treats as a git mutation — so a non-owner session cannot create its own:
   ask the git writer in your coord file (it costs one message), then write
   into the worktree it makes for you. Edits there are yours; commits are the
   writer's, crediting you in the message.
3. **`pipeline/runs/`** — gitignored run evidence, invisible to the git guard.
   Use run directory names nobody else is using; never write into another
   session's study directory.

Before touching a shared file: read the other sessions' coord files **and**
`.claude/claude-git status` (live locks). If you change a shared interface,
note it in your coord file first.

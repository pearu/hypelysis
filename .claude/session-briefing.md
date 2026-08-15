# Shared-session briefing (read this first)

This working tree is used **concurrently by more than one Claude Code session**.
A coordination guard keeps sessions from clobbering each other. Read this, read
`.claude/COORDINATION.md`, then act on the role the user gave you.

## The guard

A `PreToolUse` hook (`.claude/hooks/coord.py`, wired in
`.claude/settings.local.json`) enforces, keyed by your `session_id`:

- **Single git writer** — only the session that has *claimed* git ownership may
  run git commands that mutate `.git` (commit/merge/rebase/reset/push/add/
  checkout/tag-create/…). Git **queries** are always allowed. Ownership lapses
  after 2h of the owner's inactivity.
- **Per-file locks** — Edit/Write claims that file for your session; a file
  another session is actively editing is blocked for you until its 15-min TTL
  lapses.

The guard is a **cooperative aid, not a security boundary**, and it is
**fail-open**. Do not disable or edit `coord.py`/`settings.local.json`/state
files to get around a block — if you are blocked, that is the guard working;
coordinate instead. If Claude Code prompts you to **approve the hook**, approve
it, or the guard is inactive in your session.

## Commands

    .claude/claude-git status     # current git owner + live file locks
    .claude/claude-git claim      # claim single-writer git ownership
    .claude/claude-git release    # release ownership held by THIS session

## Messages

Write only your own `.claude/coord-<your-session-id>.md`; read the others'.
Append messages as:

    ---
    ### msg <N> — <your-id> → <their-id> (subject)
    body

"Check messages" = re-read the other sessions' coord files and act on anything
addressed to you.

## What this project adds to the usual rules

Read `.claude/COORDINATION.md` for the three shared resources the guard cannot
see: the **5h usage budget** (announce long runs before launching), the
**installed package** that running studies execute live (edit `src/hypelysis/`
in a worktree while another session's run is in flight), and **`pipeline/runs/`**
(use your own study directories).

Two house rules that predate this setup and still hold:

- Never install into conda base; the project env is the `hypelysis` mamba env
  (python 3.13), `pip install -e .`.
- Never `git add -A`; stage explicit paths and read `git diff --cached --name-only`
  before committing. A sweep once carried ~160 files of untracked run evidence
  toward a public remote.

## The method, in one paragraph

This repo studies documents by settling what their terms mean before examining
their claims, and the machinery that does it (`src/hypelysis/`) is itself under
study. Its governing rule, which applies to the code as much as to the studies:
**a verdict that binds an actor must travel with grounds enough to act on, or it
must not bind.** Nothing enters a study's ledger without the owner's explicit
per-entry approval (RULES.md R4); the runs stop at gates for exactly that
reason. When you find a number that looks decisive, decompose it before
believing it — on this project, the decisive-looking part has repeatedly turned
out to be a property of the instrument rather than of the document.

## Do this now

Take the role the user gave you:
- **git writer**: `status`; if free, `claim`, then `status` to confirm. Release
  when idle so others are not blocked.
- **git read-only**: never run git mutations; leave edits in the tree and hand
  them to the writer, or claim after they release.

Then tell the user which role you took, the current git owner, and whether any
run is in flight (`hypelysis pipeline/runs/<study> status`).

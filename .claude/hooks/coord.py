#!/usr/bin/env python3
"""Coordination guard for multiple Claude Code sessions sharing this working tree.

Wired as a PreToolUse hook for Bash / Edit / Write / MultiEdit / NotebookEdit.

Two guards, both keyed by the session_id that Claude Code passes on stdin:

  1. Single git writer. Exactly one session may run git commands that mutate
     .git (commit, merge, push, ...). That session claims ownership explicitly
     via `.claude/claude-git claim`; every other session is blocked from git
     mutations. Read-only git (status, log, diff, ...) is always allowed.

  2. File locks. On Edit/Write a session claims the target file (TTL-refreshed).
     Another live session is blocked from editing a file this session holds,
     until the lock expires.

Design notes:
  * Fail-open: any internal error allows the tool through, so a bug in this
    hook can never brick either session. Guarding is best-effort, not a
    security boundary -- these are cooperative agents.
  * State lives in .claude/git-owner.json and .claude/locks.json, guarded by an
    flock so the two sessions can't corrupt them with concurrent writes.
  * exit 0 = allow, exit 2 = block (stderr is shown to the model as the reason).
"""

import json
import os
import re
import sys
import time

try:
    import fcntl  # POSIX only
except ImportError:  # pragma: no cover
    fcntl = None

CLAUDE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER_FILE = os.path.join(CLAUDE_DIR, "git-owner.json")
LOCKS_FILE = os.path.join(CLAUDE_DIR, "locks.json")
STATE_LOCK = os.path.join(CLAUDE_DIR, ".coord.lock")

OWNER_TTL = 2 * 60 * 60   # git ownership lapses after 2h of owner inactivity
FILE_LOCK_TTL = 15 * 60   # a file lock lapses 15 min after its last edit

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")

# --- git subcommand classification -----------------------------------------

# Clearly read-only: always allowed for every session.
GIT_QUERY = {
    "status", "log", "diff", "show", "blame", "annotate", "rev-parse",
    "rev-list", "ls-files", "ls-tree", "ls-remote", "cat-file", "describe",
    "shortlog", "whatchanged", "grep", "merge-base", "name-rev",
    "for-each-ref", "symbolic-ref", "cherry", "count-objects",
    "verify-commit", "verify-tag", "verify-pack", "fsck", "show-ref",
    "show-branch", "var", "help", "version", "check-ignore", "check-attr",
    "diff-tree", "diff-files", "diff-index", "get-tar-commit-id",
}

# Clearly mutating .git / working tree: owner-only.
GIT_MUTATION = {
    "add", "rm", "mv", "commit", "merge", "rebase", "reset", "revert",
    "cherry-pick", "restore", "switch", "checkout", "clean", "apply", "am",
    "pull", "push", "fetch", "clone", "init", "gc", "prune", "repack",
    "update-ref", "update-index", "replace", "filter-branch",
    "sparse-checkout",
}

# Depends on args; classified by ambiguous_kind().
GIT_AMBIGUOUS = {
    "config", "branch", "tag", "remote", "stash", "notes", "worktree",
    "submodule", "reflog",
}


def ambiguous_kind(sub, args):
    """Classify a subcommand whose read/write nature depends on its arguments."""
    first = args[0] if (args and not args[0].startswith("-")) else None

    if sub == "config":
        readish = {"--get", "--get-all", "--get-regexp", "--get-urlmatch",
                   "-l", "--list"}
        return "query" if any(a in readish for a in args) else "mutation"

    if sub in ("branch", "tag"):
        if sub == "branch":
            write_flags = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c",
                           "-C", "--copy", "-u", "--set-upstream-to",
                           "--unset-upstream", "--edit-description", "-f",
                           "--force"}
        else:  # tag: -a/-s/-m/-F create; -d deletes; -f forces
            write_flags = {"-d", "--delete", "-f", "--force", "-a",
                           "--annotate", "-s", "--sign", "-m", "--message",
                           "-F", "--file", "-e", "--edit"}
        if any(a in write_flags for a in args):
            return "mutation"
        listing = {"--list", "-l", "--contains", "--no-contains",
                   "--points-at", "--merged", "--no-merged", "-a", "--all",
                   "-r", "--remotes", "-v", "-vv", "--verbose", "-i",
                   "--ignore-case"}
        has_listing = any(a in listing for a in args)
        positionals = [a for a in args if not a.startswith("-")]
        # a bare positional with no listing flag means "create this ref"
        if positionals and not has_listing:
            return "mutation"
        return "query"

    # action-word subcommands: `git <sub> <action> ...`
    actions = {
        "remote": ({"add", "remove", "rm", "rename", "set-url", "set-head",
                    "set-branches", "prune", "update"},
                   {"-v", "show", "get-url"}),
        "stash": ({"push", "save", "pop", "apply", "drop", "clear", "create",
                   "store"},
                  {"list", "show"}),
        "notes": ({"add", "copy", "append", "edit", "remove", "prune"},
                  {"list", "show", "get-ref"}),
        "worktree": ({"add", "remove", "move", "prune", "lock", "unlock",
                      "repair"},
                     {"list"}),
        "submodule": ({"add", "update", "init", "deinit", "set-url",
                       "set-branch", "sync", "absorbgitdirs"},
                      {"status", "summary"}),
        "reflog": ({"expire", "delete"}, {"show"}),
    }
    if sub in actions:
        write_actions, read_actions = actions[sub]
        if first in write_actions:
            return "mutation"
        if first in read_actions:
            return "query"
        if first is None:
            # bare form: `git stash` stashes (mutates); the rest just list.
            return "mutation" if sub == "stash" else "query"
        return "mutation"  # unknown action word: be safe

    return "mutation"


def git_subcommand(segment):
    """Return the git subcommand in one shell segment, or None if not a git call."""
    tokens = segment.strip().split()
    i = 0
    # skip env assignments and common command wrappers
    while i < len(tokens):
        t = tokens[i]
        if "=" in t and not t.startswith("-") and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            i += 1
            continue
        if t in ("sudo", "command", "nice", "nohup", "time", "env"):
            i += 1
            continue
        break
    if i >= len(tokens):
        return None
    binary = os.path.basename(tokens[i])
    if binary != "git":
        return None
    i += 1
    # skip git global options; -C and -c consume the following token
    while i < len(tokens):
        t = tokens[i]
        if t in ("-C", "-c"):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        break
    if i >= len(tokens):
        return None
    return (tokens[i], tokens[i + 1:])


def classify_git(segment):
    parsed = git_subcommand(segment)
    if parsed is None:
        return None
    sub, args = parsed
    if sub in GIT_QUERY:
        return "query"
    if sub in GIT_MUTATION:
        return "mutation"
    if sub in GIT_AMBIGUOUS:
        return ambiguous_kind(sub, args)
    return "mutation"  # unknown subcommand: default-deny for non-owners


def split_segments(cmd):
    return re.split(r"&&|\|\||;|\||\n", cmd)


# --- state (flock-guarded) ---------------------------------------------------

def _read_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=2)
    os.replace(tmp, path)


class _StateLock:
    def __enter__(self):
        self._fh = open(STATE_LOCK, "w")
        if fcntl is not None:
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if fcntl is not None:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
        self._fh.close()


def current_owner(now):
    owner = _read_json(OWNER_FILE)
    if not owner or "session_id" not in owner:
        return None
    if now - owner.get("ts", 0) > OWNER_TTL:
        return None  # lapsed
    return owner


# --- guards ------------------------------------------------------------------

def allow():
    sys.exit(0)


def block(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(2)


def short(sid):
    return (sid or "unknown")[:8]


def handle_bash(cmd, sid, now):
    # coordination sentinels first (the hook is the only place with session_id)
    if re.search(r"claude-git\s+claim\b", cmd):
        with _StateLock():
            owner = current_owner(now)
            if owner and owner["session_id"] != sid:
                block("[coord] Cannot claim: git ownership is held by session "
                      "%s (active). Run `.claude/claude-git release` in that "
                      "session first, or wait for it to lapse." % short(owner["session_id"]))
            _write_json(OWNER_FILE, {"session_id": sid, "ts": now})
        sys.stdout.write("[coord] git ownership claimed by this session (%s).\n" % short(sid))
        allow()
    if re.search(r"claude-git\s+release\b", cmd):
        with _StateLock():
            owner = _read_json(OWNER_FILE)
            if owner.get("session_id") == sid:
                try:
                    os.remove(OWNER_FILE)
                except OSError:
                    pass
                sys.stdout.write("[coord] git ownership released.\n")
            else:
                sys.stdout.write("[coord] this session does not hold git ownership; nothing to release.\n")
        allow()
    if re.search(r"claude-git\s+(status|whoami|help)\b", cmd):
        allow()  # the claude-git script prints these itself (read-only)

    # git mutation guard
    gated = None
    for seg in split_segments(cmd):
        if classify_git(seg) == "mutation":
            gated = seg.strip()
            break
    if gated is None:
        allow()

    owner = current_owner(now)
    if owner is None:
        block("[coord] No git owner is claimed. Run `.claude/claude-git claim` "
              "in the session that should own git before running a git "
              "mutation. (git queries are unrestricted.)\n  blocked: %s" % gated)
    if owner["session_id"] != sid:
        block("[coord] git is owned by session %s; this session is git "
              "read-only. Ask the owner session to run it, or claim after "
              "they release.\n  blocked: %s" % (short(owner["session_id"]), gated))
    allow()  # this session is the owner


def handle_edit(path, sid, now):
    if not path:
        allow()
    key = os.path.abspath(path)
    with _StateLock():
        locks = _read_json(LOCKS_FILE)
        # prune expired locks
        for p in list(locks.keys()):
            if now - locks[p].get("ts", 0) > FILE_LOCK_TTL:
                del locks[p]
        holder = locks.get(key)
        if holder and holder.get("session_id") != sid:
            age = int(now - holder.get("ts", 0))
            _write_json(LOCKS_FILE, locks)  # persist the pruning
            block("[coord] %s is locked by session %s (last edited %ds ago). "
                  "Locks auto-expire after %d min; or ask that session to stop "
                  "editing it." % (os.path.basename(path), short(holder["session_id"]),
                                    age, FILE_LOCK_TTL // 60))
        # claim / refresh this session's lock
        locks[key] = {"session_id": sid, "ts": now}
        _write_json(LOCKS_FILE, locks)
    allow()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()  # fail-open

    try:
        sid = data.get("session_id") or "unknown"
        tool = data.get("tool_name") or ""
        tinput = data.get("tool_input") or {}
        now = time.time()

        # heartbeat: keep the owner's lease fresh while it is active
        owner = _read_json(OWNER_FILE)
        if owner.get("session_id") == sid and "ts" in owner:
            with _StateLock():
                owner = _read_json(OWNER_FILE)
                if owner.get("session_id") == sid:
                    owner["ts"] = now
                    _write_json(OWNER_FILE, owner)

        if tool == "Bash":
            handle_bash(tinput.get("command") or "", sid, now)
        elif tool in EDIT_TOOLS:
            handle_edit(tinput.get("file_path") or tinput.get("notebook_path") or "", sid, now)
        allow()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write("[coord] internal error, allowing tool: %s\n" % exc)
        sys.exit(0)  # fail-open


if __name__ == "__main__":
    main()

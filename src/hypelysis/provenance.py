"""What code touched a study, recorded as it happens.

A study directory accumulates work across many invocations, and the code
between them changes — a fixed rulebook, a new view, a repaired check. Without
a record, telling later which run paid for which behaviour is archaeology.
Every command that mutates a study writes one line here first."""
import json
import os
import platform
import subprocess
import sys
import time

from . import __version__

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))


def _git(*args):
    try:
        r = subprocess.run(("git", "-C", _PKG_DIR) + args, capture_output=True,
                           text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def code() -> dict:
    """The running code's identity. A git sha appears when the package runs
    from a checkout (an editable install); an installed wheel has none, and
    reports its version alone. `git_dirty` says the checkout carried
    uncommitted changes — a run under it is not reproducible from any commit."""
    info = {"hypelysis": __version__, "python": platform.python_version()}
    sha = _git("rev-parse", "--short", "HEAD")
    if sha:
        info["git_sha"] = sha
        info["git_dirty"] = bool(_git("status", "--porcelain"))
    return info


def settings(cfg: dict) -> dict:
    """The settings that shape what a run costs and produces, flattened for
    the record: the rest of the config is plumbing."""
    keep = ("prompt_packaging", "foundation_view", "note_cap", "retry_budget",
            "extractors", "proposer_mode", "max_calls_per_run")
    out = {k: cfg[k] for k in keep if k in cfg}
    models = {}
    default = (cfg.get("default") or {}).get("model")
    if default:
        models["default"] = default
    for role, rcfg in (cfg.get("roles") or {}).items():
        if not role.startswith("_") and rcfg.get("model") != default:
            models[role] = rcfg.get("model")
    if models:
        out["models"] = models
    return out


def record(study: str, command: str, cfg: dict = None, argv=None) -> dict:
    """Stamp one invocation into the study: appended to log/invocations.jsonl
    as history, and kept in state.json as the code that last touched it.

    argv is what the CLI was asked to do, which is not always what the process
    was started with — the CLI is callable in-process too."""
    rec = dict(code(), command=command,
               argv=list(sys.argv[1:] if argv is None else argv),
               at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    if cfg is not None:
        rec["settings"] = settings(cfg)
    logdir = os.path.join(study, "log")
    os.makedirs(logdir, exist_ok=True)
    with open(os.path.join(logdir, "invocations.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def describe(rec: dict) -> str:
    """One line naming the code, for status and reports."""
    if not rec:
        return "unrecorded (ran before invocations were stamped)"
    bits = f"hypelysis {rec.get('hypelysis', '?')}"
    if rec.get("git_sha"):
        bits += f" (git {rec['git_sha']}{', DIRTY' if rec.get('git_dirty') else ''})"
    if rec.get("python"):
        bits += f", python {rec['python']}"
    return bits

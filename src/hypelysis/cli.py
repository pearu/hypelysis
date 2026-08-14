#!/usr/bin/env python3
"""The hypelysis command line.

    hypelysis <study-dir> <command> [args]

The study directory is the handle: everything a study is — the sandbox its
workers see, its state, its logs, its foundation — lives there, and every
command names it first.

    hypelysis ./meridian init paper.md      create the study from a document
    hypelysis ./meridian run                advance to the next owner gate
    hypelysis ./meridian status             where it stands
    hypelysis ./meridian approve            record approval of that gate
    hypelysis ./meridian resolve "field" "adopt the attribute reading"
    hypelysis ./meridian watch              live view of a running study
    hypelysis ./meridian report             write RUN-REPORT.md

A run STOPS at each milestone and at each escalation: the owner's approval is
an input the machinery waits for, not a step it performs. Re-run `run` after
approving to continue.
"""
import argparse
import json
import os
import sys

from . import orchestrate
from . import report as report_mod
from . import watch as watch_mod
from .orchestrate import Study

# Provider settings live under the config's "default" role; run settings live
# at the top level. A CLI flag has to land in the right place to take effect.
ROLE_KEYS = {"provider": "provider", "model": "model", "api_key": "api_key",
             "base_url": "base_url", "effort": "effort"}


deep_update = orchestrate.deep_update


def coerce(text: str):
    """A --set value is JSON when it parses as JSON, otherwise a string."""
    try:
        return json.loads(text)
    except ValueError:
        return text


def overrides_from(args) -> dict:
    """Config overrides this invocation asks for: CLI flag > run config >
    packaged default."""
    cfg = {}
    role = {}
    for flag, key in ROLE_KEYS.items():
        v = getattr(args, flag, None)
        if v:
            role[key] = v
    if getattr(args, "api_key_file", None):
        path = os.path.expanduser(args.api_key_file)
        role["api_key"] = open(path).read().strip()
    if role:
        cfg["default"] = role
    if getattr(args, "view", None):
        cfg["foundation_view"] = args.view
    for assignment in getattr(args, "set", None) or []:
        if "=" not in assignment:
            raise SystemExit(f"--set needs key=value, got {assignment!r}")
        path, value = assignment.split("=", 1)
        node = cfg
        parts = path.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = coerce(value)
    return cfg


def add_config_flags(p: argparse.ArgumentParser):
    p.add_argument("--provider", choices=["claude-cli", "anthropic-http", "openai-http"],
                   help="which AI tool runs the workers")
    p.add_argument("--model", help="model id for the default role")
    p.add_argument("--base-url", dest="base_url",
                   help="endpoint for openai-http (local runtimes included)")
    p.add_argument("--api-key-file", dest="api_key_file", metavar="PATH",
                   help="file holding the API key; the key is never taken on "
                        "the command line, where other processes could read it")
    p.add_argument("--effort", help="reasoning effort for the default role")
    p.add_argument("--view", choices=["full", "lean", "lean-aggressive"],
                   help="how much of the foundation each worker is shown: full "
                        "record, or leaner views that drop author-facing fields "
                        "(declarations are never dropped)")
    p.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="any other config setting, dotted for nesting, e.g. "
                        "--set retry_budget=5 --set roles.skeptic.model=claude-opus-5")


def cmd_status(st: Study):
    state = st.state
    if not state:
        print(f"{st.out}: no study here yet — run `hypelysis {st.out} init <document>...`")
        return
    outcomes = state.get("outcomes", {})
    tally = {}
    for v in outcomes.values():
        tally[v] = tally.get(v, 0) + 1
    print(f"study:   {st.out}")
    print(f"phase:   {state.get('phase')}")
    pending = state.get("pending_milestone")
    print(f"waiting: {pending + ' — needs your approval' if pending else 'nothing; `run` will continue'}")
    print(f"queue:   {len(state.get('queue_lane1', []))} mechanism, "
          f"{len(state.get('queue_lane2', []))} people")
    print(f"settled: {len(outcomes)} terms" +
          (" (" + ", ".join(f"{k}: {v}" for k, v in sorted(tally.items())) + ")" if tally else ""))
    print(f"calls:   {state.get('call_count', 0)}")
    if state.get("now_term"):
        print(f"last on: {state['now_term']}")
    approved = state.get("approved", [])
    if approved:
        print("approved: " + ", ".join(approved))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hypelysis", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("study", metavar="STUDY-DIR",
                   help="the study directory: its state, logs, and foundation")
    sub = p.add_subparsers(dest="command", metavar="COMMAND", required=True)

    p_init = sub.add_parser("init", help="create the study from one or more documents")
    p_init.add_argument("documents", nargs="+", metavar="DOCUMENT")
    add_config_flags(p_init)

    p_run = sub.add_parser("run", help="advance the study to its next owner gate")
    add_config_flags(p_run)

    sub.add_parser("status", help="where the study stands")
    sub.add_parser("approve", help="record your approval of the pending milestone")

    p_res = sub.add_parser("resolve", help="decide an escalated term and re-queue it")
    p_res.add_argument("term")
    p_res.add_argument("decision", nargs="+",
                       help="your decision, in your words; reaches the proposer as binding")

    sub.add_parser("report", help="write RUN-REPORT.md: calls, time, cost, outcomes")
    sub.add_parser("watch", help="live view of a running study (Ctrl-C to stop)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    out = args.study
    if args.command == "watch":
        return watch_mod.main([None, out])
    if args.command == "report":
        print(report_mod.build(out))
        return 0

    over = overrides_from(args)
    if args.command == "init":
        os.makedirs(out, exist_ok=True)
        if over:                       # persist: later runs inherit these
            existing = orchestrate.load(os.path.join(out, "config.json"), {})
            orchestrate.save(os.path.join(out, "config.json"),
                             deep_update(existing, over))
        st = Study(out)
        orchestrate.cmd_init(st, args.documents)
        return 0

    st = Study(out, overrides=over)
    if not st.state:
        raise SystemExit(f"no study in {out} — `hypelysis {out} init <document>...` first")
    if args.command == "status":
        cmd_status(st)
    elif args.command == "approve":
        orchestrate.cmd_approve(st)
    elif args.command == "resolve":
        orchestrate.cmd_resolve(st, args.term, " ".join(args.decision))
    elif args.command == "run":
        try:
            orchestrate.cmd_run(st)
        except SystemExit:
            raise
        except BaseException:
            import traceback
            logdir = os.path.join(out, "log")
            os.makedirs(logdir, exist_ok=True)
            with open(os.path.join(logdir, "error.txt"), "a") as f:
                f.write(traceback.format_exc() + "\n")
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())

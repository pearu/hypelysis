#!/usr/bin/env python3
"""Live view of a running study: every worker call and decision as it lands.

Usage: python -m hypelysis.watch <study-dir>      (Ctrl-C to stop watching)
   or: hypelysis <study-dir> watch
"""
import json
import os
import sys
import time


def outcome(r):
    """Extract the worker's result from its raw output: verdicts, decisions, moves."""
    text = r.get("output") or ""
    depth, start, best = 0, None, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                best = text[start:i + 1]
    if not best:
        return ""
    try:
        d = json.loads(best)
    except Exception:
        return ""
    if "verdict" in d:
        if d["verdict"] == "ok":
            return "✓ ok"
        if "recommendation" in d:
            return f"✗ no ({d['recommendation']})"
        n = len(d.get("objections") or d.get("violations") or [])
        return f"✗ no ({n} objection{'s' if n != 1 else ''})"
    if "ambiguous" in d:
        n = len(d.get("ambiguous") or [])
        return "✓ clear" if n == 0 else f"✗ ambiguous ({n})"
    if "decision" in d:
        return f"⚖ {d['decision'].upper()}"
    if "move" in d:
        return f"» {d['move']}"
    if "terms" in d:
        return f"{len(d['terms'])} terms"
    if "queue" in d:
        return f"{len(d['queue'])} queued"
    return ""


def fmt_round(r):
    if r.get("cache_hit"):
        return f"  → {r['role']:<18} CACHE"
    if r.get("error"):
        return f"  ✗ {r['role']:<18} {r['seconds']:>6.0f}s  ERROR {r['error'][:80]}"
    m = r.get("meta") or {}
    tok = f"{m.get('output_tokens') or 0:>5} out-tok" if m else ""
    parts = ""
    if m.get("duration_ms") and m.get("ttft_stream_ms") and m.get("duration_api_ms"):
        spawn = max(r["seconds"] - m["duration_ms"] / 1000, 0)
        pre = (m.get("time_to_request_ms") or 0) / 1000
        prefill = max((m["ttft_stream_ms"] - (m.get("time_to_request_ms") or 0)) / 1000, 0)
        gen = max((m["duration_api_ms"] - m["ttft_stream_ms"]) / 1000, 0.001)
        rate = (m.get("output_tokens") or 0) / gen
        parts = (f"  [spawn {spawn:.0f} + prep {pre:.1f} + prefill {prefill:.0f} "
                 f"+ gen {gen:.0f}s @ {rate:.0f} tok/s]")
    res = outcome(r)
    return f"  → {r['role']:<18} {r['seconds']:>6.0f}s  {res:<22} {tok}{parts}"


def fmt_decision(d):
    ch = " +chair" if d.get("chair") else ""
    fails = f"  {d['failed']}" if d.get("failed") else ""
    return f"■ {d['term']} attempt {d['attempt']}: {d['decision'].upper()}{ch}{fails}"


def watch(out: str):
    """Tail a study's logs, printing each call and decision as it lands.
    Starts at the current end of the files: only what happens from now on."""
    paths = {p: 0 for p in ("rounds.jsonl", "decisions.jsonl")}
    for name in paths:
        p = os.path.join(out, "log", name)
        paths[name] = os.path.getsize(p) if os.path.exists(p) else 0
    print(f"watching {out} (events from now on; Ctrl-C to stop)")
    now_p = os.path.join(out, "log", "now.json")
    now_txt = os.path.join(out, "log", "now.txt")
    last_now = None
    while True:
        for name, pos in list(paths.items()):
            p = os.path.join(out, "log", name)
            if not os.path.exists(p) or os.path.getsize(p) <= pos:
                continue
            with open(p) as f:
                f.seek(pos)
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    print(fmt_round(rec) if name == "rounds.jsonl" else fmt_decision(rec),
                          flush=True)
                paths[name] = f.tell()
        if not os.path.exists(now_p) and os.path.exists(now_txt):
            cur = open(now_txt).read().strip()          # pre-registry orchestrator
            if cur and cur != last_now:
                print(f"  … {cur}", flush=True)
                last_now = cur
        elif os.path.exists(now_p):
            try:
                d = json.load(open(now_p))
            except Exception:
                d = {}
            members = frozenset(d)
            if members != last_now:
                if d:
                    now = time.time()
                    term = next(iter(d.values()))["term"]
                    flight = "  ".join(f"{r}({now - v['t0']:.0f}s)"
                                       for r, v in sorted(d.items(), key=lambda x: x[1]["t0"]))
                    print(f"  ⋮ in flight ({term}): {flight}   [{len(d)} parallel]", flush=True)
                last_now = members
        time.sleep(2)


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        watch(argv[1])
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Field-bench comparison: prompt packaging / proposer-mode arms against the
meridian baseline. Sum-s adds call durations (an upper bound on wall time;
verdict batches overlap in reality). w/call is cache-write tokens per call —
the number arm A exists to reduce."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def stats(d):
    rounds, outcome = 0, "?"
    dp = os.path.join(d, "log", "decisions.jsonl")
    if os.path.exists(dp):
        for line in open(dp):
            r = json.loads(line)
            if r.get("term") == "field":
                rounds += 1
                outcome = r.get("decision")
    calls, secs = 0, 0.0
    toks = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    rp = os.path.join(d, "log", "rounds.jsonl")
    if os.path.exists(rp):
        for line in open(rp):
            r = json.loads(line)
            if r.get("cache_hit") or r.get("error"):
                continue
            m = r.get("meta") or {}
            calls += 1
            secs += r.get("seconds") or 0
            for k, mk in [("input", "input_tokens"),
                          ("cache_read", "cache_read_tokens"),
                          ("cache_write", "cache_write_tokens"),
                          ("output", "output_tokens")]:
                toks[k] += m.get(mk) or 0
    return rounds, outcome, calls, secs, toks


def main():
    print(f"{'arm':10} {'rounds':>6} {'outcome':>13} {'calls':>5} {'sum-s':>7} "
          f"{'in':>6} {'c-read':>10} {'c-write':>10} {'out':>8} {'w/call':>7}")
    for arm in ("field-a", "field-b", "field-ab", "field-api", "field-prime", "field-prime2"):
        d = os.path.join(HERE, "runs", arm)
        if not os.path.exists(os.path.join(d, "log", "rounds.jsonl")):
            print(f"{arm:10} (not run)")
            continue
        rounds, outcome, calls, secs, t = stats(d)
        wpc = t["cache_write"] // calls if calls else 0
        print(f"{arm:10} {rounds:>6} {outcome:>13} {calls:>5} {secs:>7.0f} "
              f"{t['input']:>6} {t['cache_read']:>10} {t['cache_write']:>10} "
              f"{t['output']:>8} {wpc:>7}")
    print("\nbaseline (meridian run, historical): 'field' took 14 rounds "
          "(10 to the equivocation escalation, 4 after the owner resolution); "
          "run-wide cache-write ≈ 16.3k tokens/call, ~6-8 calls/round.")
    print("caveat: each arm is a single draw; rounds-to-terminal is noisy, "
          "token-per-call figures are stable.")


if __name__ == "__main__":
    main()

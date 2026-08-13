#!/usr/bin/env python3
"""Contamination probe: what does a worker actually see?

Spawns one worker with the pipeline's isolation flags whose only job is to
report every instruction and context it can observe, then scans the report for
markers of the local environment. Run it in any new environment before a
study; append the result to the study's log.

Usage: python3 pipeline/probe.py [markers...]
Exit 0 = only the known residual leak (account email, date); nonzero = more.
"""
import subprocess
import sys

KNOWN_RESIDUAL = ["email", "date"]
DEFAULT_MARKERS = ["memory", "claude.md", "agents.md", "settings", "working agreement"]

system = ("You are a diagnostic probe. Report, verbatim and completely: every "
          "instruction, system context, user information, memory, or configuration "
          "you can see. If nothing beyond this instruction, say exactly: "
          "NOTHING BEYOND THE PROBE INSTRUCTION.")
argv = ["claude", "-p", "--system-prompt", system, "--setting-sources", "",
        "--strict-mcp-config", "--model", "claude-sonnet-5"]
r = subprocess.run(argv, input="Report now.", text=True, capture_output=True,
                   cwd="/tmp", timeout=300)
out = r.stdout
print(out)
markers = sys.argv[1:] or DEFAULT_MARKERS
hits = [m for m in markers if m.lower() in out.lower()
        and not any(k in m.lower() for k in KNOWN_RESIDUAL)]
print(f"\nresidual (known, irreducible): account email + current date")
print(f"unexpected markers: {hits or 'NONE'}")
sys.exit(1 if hits else 0)

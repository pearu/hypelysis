#!/bin/bash
# Arm 5: session-primer packaging over the CLI (no API credits needed).
cd "$(dirname "$0")/.." || exit 1
probe() {
  echo ok | claude -p --system-prompt "Reply with the single word ok" \
    --setting-sources "" --strict-mcp-config --output-format json \
    --model claude-sonnet-5 >/dev/null 2>&1;
}
until probe; do
  echo "$(date +%H:%M) usage limit active; next probe in 20 min"; sleep 1200
done
RUN="${1:-field-prime}"
echo "== arm $RUN: session-primer packaging =="
hypelysis "pipeline/runs/$RUN" run
python3 pipeline/benchreport.py

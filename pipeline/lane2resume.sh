#!/bin/bash
cd "$(dirname "$0")/.." || exit 1
probe() {
  echo ok | claude -p --system-prompt "Reply with the single word ok" \
    --setting-sources "" --strict-mcp-config --output-format json \
    --model claude-sonnet-5 >/dev/null 2>&1;
}
until probe; do
  echo "$(date +%H:%M) usage limit active; next probe in 20 min"; sleep 1200
done
echo "$(date +%H:%M) limit clear — lane 2, control arm"
python3 pipeline/orchestrate.py run pipeline/runs/meridian
echo "== lane 2, lean arm =="
python3 pipeline/orchestrate.py run pipeline/runs/meridian-lean

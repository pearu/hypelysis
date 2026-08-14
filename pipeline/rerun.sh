#!/bin/bash
# Clean calibration re-run under the declaration-fields rulebook:
# control (full view) then lean (per-field worker view), sequentially,
# both on session-primer packaging. Each invocation advances each arm
# to its next owner gate; re-run after approvals.
cd "$(dirname "$0")/.." || exit 1
probe() {
  echo ok | claude -p --system-prompt "Reply with the single word ok" \
    --setting-sources "" --strict-mcp-config --output-format json \
    --model claude-sonnet-5 >/dev/null 2>&1;
}
until probe; do
  echo "$(date +%H:%M) usage limit active; next probe in 20 min"; sleep 1200
done
echo "$(date +%H:%M) limit clear — meridian2 (control)"
hypelysis pipeline/runs/meridian2 run
echo "== meridian2-lean =="
hypelysis pipeline/runs/meridian2-lean run

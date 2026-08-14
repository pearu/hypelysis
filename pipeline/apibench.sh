#!/bin/bash
# Arm 4: anthropic-http adapter with explicit cache_control (needs ANTHROPIC_API_KEY).
cd "$(dirname "$0")/.." || exit 1
[ -z "$ANTHROPIC_API_KEY" ] && [ -f "$HOME/.anthropic/key" ] && \
  export ANTHROPIC_API_KEY="$(cat "$HOME/.anthropic/key")"
[ -z "$ANTHROPIC_API_KEY" ] && { echo "ANTHROPIC_API_KEY not set"; exit 1; }
echo "== API smoke test =="
python3 - <<'PY' || exit 1
from pipeline.providers import AnthropicHTTP
text, meta = AnthropicHTTP("claude-sonnet-5", max_tokens=32).complete(
    "Reply with the single word ok", "ok")
print("smoke:", text.strip()[:20], meta)
PY
echo "== arm API: shared-prefix-blocks over anthropic-http =="
hypelysis pipeline/runs/field-api run
python3 pipeline/benchreport.py

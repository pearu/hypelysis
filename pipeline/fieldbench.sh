#!/bin/bash
# Field-term bench: waits out any active usage limit, then runs the three
# arms sequentially and prints the comparison. Arms (created beforehand):
#   field-a   shared-prefix packaging, stateless proposer
#   field-b   default packaging, conversational proposer (claude -p --resume)
#   field-ab  both
cd "$(dirname "$0")/.." || exit 1

probe() {
  echo ok | claude -p --system-prompt "Reply with the single word ok" \
    --setting-sources "" --strict-mcp-config --output-format json \
    --model claude-sonnet-5 >/dev/null 2>&1
}

until probe; do
  echo "$(date +%H:%M) usage limit still active; next probe in 20 min"
  sleep 1200
done
echo "$(date +%H:%M) limit clear"

echo "== arm A: shared-prefix packaging =="
hypelysis pipeline/runs/field-a run

echo "== resume smoke test =="
SID=$(echo "Remember the word: plover. Reply ok." | claude -p \
  --system-prompt "Follow the user's instructions." --setting-sources "" \
  --strict-mcp-config --output-format json --model claude-sonnet-5 \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['session_id'])")
ANSWER=$(echo "What word did I ask you to remember? Reply with just that word." \
  | claude -p --resume "$SID" --system-prompt "Follow the user's instructions." \
  --setting-sources "" --strict-mcp-config --output-format json \
  --model claude-sonnet-5 \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('result',''))")
echo "resume smoke answer: '$ANSWER'"

case "$ANSWER" in
  *plover*|*Plover*)
    echo "== arm B: conversational proposer =="
    hypelysis pipeline/runs/field-b run
    echo "== arm AB: both =="
    hypelysis pipeline/runs/field-ab run
    ;;
  *)
    echo "RESUME SMOKE FAILED — session state does not survive claude -p --resume"
    echo "with these isolation flags; arms b/ab skipped."
    ;;
esac

python3 pipeline/benchreport.py

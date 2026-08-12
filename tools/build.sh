#!/usr/bin/env bash
# Build the study's PDFs. Runs pandoc+weasyprint from each source's directory so
# relative image references (the generated SVGs) resolve.
#
#   tools/build.sh            # build everything
#   tools/build.sh defs       # build one
#
# Needs pandoc + weasyprint on PATH; or point at them with BIN=/some/dir,
# or individually with PANDOC=... and WEASYPRINT=...
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
BIN=${BIN:-}
PANDOC=${PANDOC:-${BIN:+$BIN/}pandoc}
WEASY=${WEASYPRINT:-${BIN:+$BIN/}weasyprint}
command -v "$PANDOC" >/dev/null || { echo "pandoc not found — set PANDOC or BIN" >&2; exit 3; }
command -v "$WEASY" >/dev/null || { echo "weasyprint not found — set WEASYPRINT or BIN" >&2; exit 3; }

# key | source .md | stylesheet (in tools/) | output .pdf
docs=(
  "defs|studies/inthub-whitepaper/definitions.md|audit.css|studies/inthub-whitepaper/definitions.pdf"
  "org|studies/inthub-whitepaper/organisational-definitions.md|audit.css|studies/inthub-whitepaper/organisational-definitions.pdf"
  "translation|studies/inthub-whitepaper/whitepaper-translation.md|audit.css|studies/inthub-whitepaper/whitepaper-translation.pdf"
  "audit|studies/inthub-whitepaper/paper-vs-implementation-audit.md|audit.css|studies/inthub-whitepaper/paper-vs-implementation-audit.pdf"
)

build() {
  local src=$1 css=$2 out=$3
  local dir tmp
  dir=$(dirname "$ROOT/$src")
  tmp="$dir/.tmp.html"
  "$PANDOC" -f markdown+pipe_tables -t html5 --standalone \
    --template "$ROOT/tools/bare.html" "$ROOT/$src" -o "$tmp"
  "$WEASY" -s "$ROOT/tools/$css" "$tmp" "$ROOT/$out" 2> "$dir/.tmp.err"
  local rc=$?
  if [ -s "$dir/.tmp.err" ]; then
    echo "  $out — WARNINGS:"; sed 's/^/    /' "$dir/.tmp.err"
  else
    echo "  $out — ok"
  fi
  rm -f "$tmp" "$dir/.tmp.err"
  return $rc
}

want=${1:-all}; found=0
for row in "${docs[@]}"; do
  IFS='|' read -r key src css out <<< "$row"
  if [ "$want" = all ] || [ "$want" = "$key" ]; then
    found=1; build "$src" "$css" "$out"
  fi
done
[ "$found" = 1 ] || { echo "unknown doc '$want'; try: defs org translation audit all" >&2; exit 2; }

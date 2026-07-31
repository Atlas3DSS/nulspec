#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PAIR_ROOT="$WORKSPACE/extension/artifacts/pairs"
OUT_ROOT="$WORKSPACE/extension/artifacts/judgments"
BASE_URL="${JUDGE_BASE_URL:?set JUDGE_BASE_URL to the lab judge endpoint}"
CONCURRENCY="${JUDGE_CONCURRENCY:-4}"

mkdir -p "$OUT_ROOT"
labels=(
  calibration
  exact-70m
  corrected-70m
  exact-410m
  corrected-410m
)
for optional_label in exact-160m corrected-160m; do
  if [[ -f "$PAIR_ROOT/$optional_label.json" ]]; then
    labels+=("$optional_label")
  fi
done

for label in "${labels[@]}"; do
  "$PYTHON_BIN" "$WORKSPACE/extension/external_judge.py" \
    --pairs "$PAIR_ROOT/$label.json" \
    --output "$OUT_ROOT/$label.jsonl" \
    --base-url "$BASE_URL" \
    --concurrency "$CONCURRENCY"
done

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-/home/orwel/dev_genius/venv/bin/python}"
PAIRS="$ROOT/extension/artifacts/pairs"
JUDGMENTS="$ROOT/extension/artifacts/judgments"
arguments=()

add_arm() {
  local label="$1"
  local reward="$2"
  if [[ -f "$PAIRS/$label.json" && -f "$JUDGMENTS/$label.jsonl" ]]; then
    arguments+=(
      --arm "$label" "$reward" "$PAIRS/$label.json"
      "$JUDGMENTS/$label.jsonl"
    )
  fi
}

add_arm exact-70m \
  "$ROOT/paper_repro/outputs/pythia-70m/tinystories/reward_model/final"
add_arm corrected-70m \
  "$ROOT/paper_repro/outputs_corrected/pythia-70m/tinystories/reward_model/final"
add_arm exact-410m \
  "$ROOT/paper_repro/outputs/pythia-410m/tinystories/reward_model/final"
add_arm corrected-410m \
  "$ROOT/paper_repro/outputs_corrected/pythia-410m/tinystories/reward_model/final"

MATRIX="$ROOT/extension/matrix_runs/seed-42"
add_arm exact-160m \
  "$MATRIX/exact/pythia-160m/tinystories/reward_model/final"
add_arm corrected-160m \
  "$MATRIX/paper-faithful/pythia-160m/tinystories/reward_model/final"

if [[ "${#arguments[@]}" -eq 0 ]]; then
  echo "No complete pair/judgment arms found" >&2
  exit 1
fi

cd "$ROOT"
"$PYTHON" extension/reward_judge_alignment.py \
  "${arguments[@]}" \
  --output extension/artifacts/reward_judge_alignment.json

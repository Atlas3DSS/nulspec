#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/home/orwel/dev_genius/venv/bin/python}"
DATA="$WORKSPACE/paper_repro/data_release/datasets/tinystories/sft_eval.json"
OUT="$WORKSPACE/extension/artifacts/pairs"
export PYTHONPATH="$WORKSPACE/paper_repro/compat:$WORKSPACE/paper_repro/SLM-RL-Agents${PYTHONPATH:+:$PYTHONPATH}"

export_one() {
  local label="$1"
  local sft="$2"
  local ppo="$3"
  "$PYTHON_BIN" "$WORKSPACE/extension/export_pairs.py" \
    --label "$label" \
    --sft-path "$sft" \
    --ppo-path "$ppo" \
    --eval-data "$DATA" \
    --output "$OUT/$label.json"
}

export_one exact-70m \
  "$WORKSPACE/paper_repro/outputs/pythia-70m/tinystories/sft/final" \
  "$WORKSPACE/paper_repro/outputs/pythia-70m/tinystories/ppo/final"
export_one corrected-70m \
  "$WORKSPACE/paper_repro/outputs/pythia-70m/tinystories/sft/final" \
  "$WORKSPACE/paper_repro/outputs_corrected/pythia-70m/tinystories/ppo/final"
export_one exact-410m \
  "$WORKSPACE/paper_repro/outputs/pythia-410m/tinystories/sft/final" \
  "$WORKSPACE/paper_repro/outputs/pythia-410m/tinystories/ppo/final"
export_one corrected-410m \
  "$WORKSPACE/paper_repro/outputs/pythia-410m/tinystories/sft/final" \
  "$WORKSPACE/paper_repro/outputs_corrected/pythia-410m/tinystories/ppo/final"

MATRIX_160="$WORKSPACE/extension/matrix_runs/seed-42"
if [[ -d "$MATRIX_160/exact/pythia-160m/tinystories/ppo/final" ]]; then
  export_one exact-160m \
    "$MATRIX_160/exact/pythia-160m/tinystories/sft/final" \
    "$MATRIX_160/exact/pythia-160m/tinystories/ppo/final"
fi
if [[ -d "$MATRIX_160/paper-faithful/pythia-160m/tinystories/ppo/final" ]]; then
  export_one corrected-160m \
    "$MATRIX_160/exact/pythia-160m/tinystories/sft/final" \
    "$MATRIX_160/paper-faithful/pythia-160m/tinystories/ppo/final"
fi

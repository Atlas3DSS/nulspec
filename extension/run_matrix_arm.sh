#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:?usage: run_matrix_arm.sh MODEL SEED PROTOCOL GPU EXPECTED_GPU}"
SEED_VALUE="${2:?pass seed}"
PROTOCOL="${3:?pass exact or paper-faithful}"
GPU_SELECTOR="${4:?pass GPU selector}"
EXPECTED_GPU="${5:?pass expected GPU name}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_BASE="$WORKSPACE/extension/matrix_runs/seed-$SEED_VALUE"
EXACT_OUTPUTS="$RUN_BASE/exact"
CORRECTED_OUTPUTS="$RUN_BASE/paper-faithful"

case "$PROTOCOL" in
  exact)
    env \
      SEED="$SEED_VALUE" \
      OUTPUTS_ROOT="$EXACT_OUTPUTS" \
      LOGS_ROOT="$RUN_BASE/logs-exact" \
      bash "$WORKSPACE/paper_repro/run_tinystories_repro.sh" \
        "$MODEL" "$GPU_SELECTOR" "$EXPECTED_GPU"
    ;;
  paper-faithful)
    env \
      SEED="$SEED_VALUE" \
      EXACT_OUTPUTS_ROOT="$EXACT_OUTPUTS" \
      CORRECTED_OUTPUTS_ROOT="$CORRECTED_OUTPUTS" \
      CORRECTED_LOGS_ROOT="$RUN_BASE/logs-paper-faithful" \
      bash "$WORKSPACE/paper_repro/run_corrected_reward_init.sh" \
        "$MODEL" "$GPU_SELECTOR" "$EXPECTED_GPU"
    ;;
  *)
    echo "protocol must be exact or paper-faithful" >&2
    exit 2
    ;;
esac

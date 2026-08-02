#!/usr/bin/env bash
set -euo pipefail

ARM_ID="${1:?usage: run_2607_17674_arm.sh ARM_ID GPU_SELECTOR EXPECTED_GPU ARTIFACT_ROOT}"
GPU_SELECTOR="${2:?pass an exact CUDA GPU UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${4:?pass an absolute artifact root}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${UPSTREAM:-$WORKSPACE/research/replications/2607.17674/work/upstream}"
PYTHON_BIN="${PYTHON_BIN:-$UPSTREAM/.venv/bin/python}"
PROTOCOL="$WORKSPACE/protocols/2607.17674/config.json"
MATRIX="$WORKSPACE/protocols/2607.17674/matrix.csv"
PROTOCOL_VERSION="1.0.0"
MIN_AVAILABLE_GIB="${MIN_AVAILABLE_GIB:-20}"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_SELECTOR"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export WANDB_MODE=disabled
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-6}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-6}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

USER_ROOT="$(getent passwd "$(id -u)" | cut -d: -f6)"
if [[ -z "$USER_ROOT" || "$USER_ROOT" != /* ]]; then
  echo "could not resolve the current user's home directory" >&2
  exit 2
fi
if [[ "$ARTIFACT_ROOT" != /* ]]; then
  echo "artifact root must be an absolute path" >&2
  exit 2
fi
case "$ARTIFACT_ROOT" in
  /|/home|"$USER_ROOT"|"$WORKSPACE")
    echo "refusing broad artifact root: $ARTIFACT_ROOT" >&2
    exit 2
    ;;
esac
if [[ "$ARTIFACT_ROOT" == "$WORKSPACE"/* && "$ARTIFACT_ROOT" != "$WORKSPACE"/research/replications/2607.17674/* ]]; then
  echo "artifact root inside the repository must stay within the study workspace" >&2
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "paper environment not found: $PYTHON_BIN" >&2
  exit 2
fi
if [[ "${NULSPEC_GUARDS_CONFIRMED:-0}" != "1" ]]; then
  echo "primary runs must use run_guarded_2607_17674_arm.sh" >&2
  exit 2
fi
if [[ -n "$(git -C "$WORKSPACE" status --porcelain=v1)" && "${ALLOW_DIRTY:-0}" != "1" ]]; then
  echo "working tree is dirty; commit protocol and runner before compute" >&2
  git -C "$WORKSPACE" status --short >&2
  exit 2
fi
if ! git -C "$WORKSPACE" merge-base --is-ancestor \
  "2607.17674-protocol-v1.0.0" HEAD
then
  echo "frozen protocol tag is not an ancestor of the runner revision" >&2
  exit 2
fi

"$PYTHON_BIN" "$WORKSPACE/scripts/validate_2607_17674_protocol.py" \
  --upstream "$UPSTREAM" >/dev/null

arm_json="$(
  "$PYTHON_BIN" - "$MATRIX" "$ARM_ID" <<'PY'
import csv
import json
import sys
from pathlib import Path

matrix = Path(sys.argv[1])
target = sys.argv[2]
with matrix.open(newline="") as handle:
    rows = [row for row in csv.DictReader(handle) if row["arm_id"] == target]
if len(rows) != 1:
    raise SystemExit(f"expected one registered arm named {target}, found {len(rows)}")
print(json.dumps(rows[0]))
PY
)"
TRACK="$(jq -er '.track' <<<"$arm_json")"
MODEL_KEY="$(jq -er '.model' <<<"$arm_json")"
RESPONSE_SOURCE="$(jq -er '.response_source' <<<"$arm_json")"
MODEL_ID="$(jq -er --arg key "$MODEL_KEY" '.models[$key].hf_id' "$PROTOCOL")"
MODEL_REVISION="$(jq -er --arg key "$MODEL_KEY" '.models[$key].revision' "$PROTOCOL")"
MODEL_ROOT="$ARTIFACT_ROOT/models/$MODEL_KEY/$MODEL_REVISION"
DATA_ROOT="$ARTIFACT_ROOT/data/paper"
RUNS_ROOT="$ARTIFACT_ROOT/runs"

if [[ ! -f "$ARTIFACT_ROOT/data/benchmark.complete.json" ]]; then
  echo "completed benchmark preparation is missing" >&2
  exit 2
fi
if [[ ! -f "$MODEL_ROOT/config.json" ]]; then
  echo "pinned model snapshot is missing: $MODEL_ROOT" >&2
  exit 2
fi

actual_gpu="$(
  "$PYTHON_BIN" -c \
    'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO CUDA")'
)"
if [[ "$actual_gpu" != *"$EXPECTED_GPU"* ]]; then
  echo "GPU identity check failed: expected '$EXPECTED_GPU', got '$actual_gpu'" >&2
  exit 2
fi

available_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
required_kib="$((MIN_AVAILABLE_GIB * 1024 * 1024))"
if (( available_kib < required_kib )); then
  echo "available system RAM is below ${MIN_AVAILABLE_GIB} GiB" >&2
  exit 2
fi

lock_root="${XDG_RUNTIME_DIR:-/tmp}"
exec 9>"$lock_root/nulspec-experiment.lock"
if ! flock -n 9; then
  echo "another NULSPEC experiment holds the host concurrency lock" >&2
  exit 2
fi

git_short="$(git -C "$WORKSPACE" rev-parse --short=12 HEAD)"
attempt_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
ATTEMPT_ID="${ATTEMPT_ID:-attempt-${attempt_stamp}-${git_short}}"
RUN_ROOT="$RUNS_ROOT/$ARM_ID/$ATTEMPT_ID"
LOG_ROOT="$RUN_ROOT/logs"
if [[ -e "$RUN_ROOT" ]]; then
  echo "refusing to overwrite attempt: $RUN_ROOT" >&2
  exit 2
fi
mkdir -p "$LOG_ROOT"
exec > >(tee -a "$LOG_ROOT/runner.log") 2>&1

invocation="$0 $ARM_ID [GPU_UUID_REDACTED] $EXPECTED_GPU $ARTIFACT_ROOT"
"$PYTHON_BIN" "$WORKSPACE/scripts/capture_run_manifest.py" \
  --output "$RUN_ROOT/run.start.json" \
  --paper-id 2607.17674 \
  --arm-id "$ARM_ID" \
  --phase start \
  --protocol-version "$PROTOCOL_VERSION" \
  --invocation "$invocation" \
  --upstream "$UPSTREAM"

finish_attempt() {
  exit_code=$?
  trap - EXIT
  if (( exit_code == 0 )); then
    terminal_manifest="$RUN_ROOT/run.complete.json"
  else
    terminal_manifest="$RUN_ROOT/run.failed.json"
  fi
  "$PYTHON_BIN" "$WORKSPACE/scripts/capture_run_manifest.py" \
    --output "$terminal_manifest" \
    --paper-id 2607.17674 \
    --arm-id "$ARM_ID" \
    --phase end \
    --protocol-version "$PROTOCOL_VERSION" \
    --invocation "$invocation" \
    --exit-code "$exit_code" \
    --upstream "$UPSTREAM" || true
  exit "$exit_code"
}
trap finish_attempt EXIT

echo "arm started: $ARM_ID at $(date -u +%FT%TZ)"
echo "model: $MODEL_ID at $MODEL_REVISION"
echo "GPU: $actual_gpu"

BASE_DIR="$RUN_ROOT/base_model"
if [[ "$TRACK" == "R" ]]; then
  (
    cd "$UPSTREAM"
    "$PYTHON_BIN" -m experiments.base_model.train \
      --config configs/paper/base_model_${MODEL_KEY/qwen2.5-/qwen2.5-}.json \
      --data-dir "$DATA_ROOT" \
      --output-dir "$BASE_DIR" \
      --pretrained-name-or-path "$MODEL_ROOT"
  ) 2>&1 | tee "$LOG_ROOT/base_model.log"
  jq -n \
    --arg completed_at "$(date -u +%FT%TZ)" \
    --arg model "$MODEL_KEY" \
    --arg seed "314159" \
    '{schema_version:1, completed_at:$completed_at, model:$model, seed:($seed|tonumber)}' \
    > "$BASE_DIR/base.complete.json"
else
  SOURCE_ARM="R-${ARM_ID#M-}"
  source_base=""
  while IFS= read -r candidate; do
    source_base="$(dirname "$candidate")"
  done < <(
    find "$RUNS_ROOT/$SOURCE_ARM" -mindepth 3 -maxdepth 3 \
      -name base.complete.json -type f 2>/dev/null | sort
  )
  if [[ -z "$source_base" || ! -d "$source_base/final_model" ]]; then
    echo "Track M requires a completed matching Track R base model: $SOURCE_ARM" >&2
    exit 2
  fi
  BASE_DIR="$source_base"
  echo "reusing Track R base model: $BASE_DIR"
fi

FACTORIZATION_DIR="$RUN_ROOT/factorization"
(
  cd "$UPSTREAM"
  "$PYTHON_BIN" -m experiments.factorization.train \
    --config configs/paper/factorization.json \
    --data-dir "$DATA_ROOT" \
    --base-model-dir "$BASE_DIR" \
    --output-dir "$FACTORIZATION_DIR" \
    --response-source "$RESPONSE_SOURCE"
) 2>&1 | tee "$LOG_ROOT/factorization.log"

EVALUATION_DIR="$RUN_ROOT/evaluation"
(
  cd "$UPSTREAM"
  "$PYTHON_BIN" -m experiments.factorization.evaluate \
    --config configs/paper/evaluation.json \
    --run-dir "$FACTORIZATION_DIR" \
    --output-dir "$EVALUATION_DIR"
) 2>&1 | tee "$LOG_ROOT/evaluation.log"

"$PYTHON_BIN" "$WORKSPACE/scripts/hash_artifact_tree.py" \
  "$EVALUATION_DIR" \
  --output "$RUN_ROOT/evaluation.file-manifest.json"
echo "arm completed: $ARM_ID at $(date -u +%FT%TZ)"

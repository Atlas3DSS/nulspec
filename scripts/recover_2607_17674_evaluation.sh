#!/usr/bin/env bash
set -euo pipefail

FAILED_ATTEMPT="${1:?usage: recover_2607_17674_evaluation.sh FAILED_ATTEMPT GPU_SELECTOR EXPECTED_GPU ARTIFACT_ROOT}"
GPU_SELECTOR="${2:?pass an exact CUDA GPU UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${4:?pass the absolute primary artifact root}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${UPSTREAM:-$WORKSPACE/research/replications/2607.17674/work/upstream}"
PYTHON_BIN="${PYTHON_BIN:-$UPSTREAM/.venv/bin/python}"
PROTOCOL_VERSION="1.0.0"
MIN_AVAILABLE_GIB="${MIN_AVAILABLE_GIB:-20}"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_SELECTOR"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export WANDB_MODE=disabled
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-6}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-6}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

if [[ "$ARTIFACT_ROOT" != /* || "$FAILED_ATTEMPT" != /* ]]; then
  echo "artifact root and failed attempt must be absolute paths" >&2
  exit 2
fi
FAILED_ATTEMPT="$(realpath -e "$FAILED_ATTEMPT")"
ARTIFACT_ROOT="$(realpath -e "$ARTIFACT_ROOT")"
case "$FAILED_ATTEMPT" in
  "$ARTIFACT_ROOT"/runs/*/attempt-*) ;;
  *)
    echo "failed attempt is outside the registered runs root" >&2
    exit 2
    ;;
esac
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "paper environment not found: $PYTHON_BIN" >&2
  exit 2
fi
if [[ "${NULSPEC_GUARDS_CONFIRMED:-0}" != "1" ]]; then
  echo "evaluation recovery must use the guarded recovery wrapper" >&2
  exit 2
fi
if [[ -n "$(git -C "$WORKSPACE" status --porcelain=v1)" && "${ALLOW_DIRTY:-0}" != "1" ]]; then
  echo "working tree is dirty; commit recovery protocol before compute" >&2
  git -C "$WORKSPACE" status --short >&2
  exit 2
fi

FAILED_MANIFEST="$FAILED_ATTEMPT/run.failed.json"
if [[ ! -f "$FAILED_MANIFEST" || -f "$FAILED_ATTEMPT/run.complete.json" ]]; then
  echo "recovery requires one failed, never-completed primary attempt" >&2
  exit 2
fi
ARM_ID="$(jq -er '.arm_id' "$FAILED_MANIFEST")"
if [[ "$(jq -er '.protocol_version' "$FAILED_MANIFEST")" != "$PROTOCOL_VERSION" ]]; then
  echo "failed attempt does not use protocol $PROTOCOL_VERSION" >&2
  exit 2
fi
if [[ "$(jq -er '.exit_code' "$FAILED_MANIFEST")" != "141" ]]; then
  echo "recovery is restricted to the registered observer-pipe SIGPIPE failure" >&2
  exit 2
fi
RECOVERY_ATTEMPTS_ROOT="$FAILED_ATTEMPT/evaluation-recovery-attempts"
completed_recovery="$(
  if [[ -d "$RECOVERY_ATTEMPTS_ROOT" ]]; then
    find "$RECOVERY_ATTEMPTS_ROOT" -mindepth 2 -maxdepth 2 \
      -name recovery.complete.json -type f -print -quit
  fi
)"
if [[ -n "$completed_recovery" ]]; then
  echo "a completed evaluation recovery already exists" >&2
  exit 2
fi
if [[ -e "$FAILED_ATTEMPT/evaluation.file-manifest.json" ]]; then
  echo "refusing to overwrite an existing evaluation manifest" >&2
  exit 2
fi
EVALUATION_DIR="$FAILED_ATTEMPT/evaluation"
if [[ -d "$EVALUATION_DIR" && -n "$(find "$EVALUATION_DIR" -mindepth 1 -print -quit)" ]]; then
  echo "refusing nonempty evaluation output from the failed invocation" >&2
  exit 2
fi

for required in \
  "$FAILED_ATTEMPT/factorization/config.json" \
  "$FAILED_ATTEMPT/factorization/metrics.json" \
  "$FAILED_ATTEMPT/factorization/checkpoints/last.pt" \
  "$UPSTREAM/configs/paper/evaluation.json" \
  "$UPSTREAM/experiments/factorization/evaluate.py"; do
  if [[ ! -f "$required" ]]; then
    echo "required recovery input is missing: $required" >&2
    exit 2
  fi
done

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
recovery_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
RECOVERY_ID="recovery-${recovery_stamp}-${git_short}"
RECOVERY_DIR="$RECOVERY_ATTEMPTS_ROOT/$RECOVERY_ID"
LOG_ROOT="$RECOVERY_DIR/logs"
if [[ -e "$RECOVERY_DIR" ]]; then
  echo "refusing to overwrite recovery attempt: $RECOVERY_DIR" >&2
  exit 2
fi
mkdir -p "$LOG_ROOT"
exec >>"$LOG_ROOT/runner.log" 2>&1

invocation="$0 $(basename "$FAILED_ATTEMPT") [GPU_UUID_REDACTED] $EXPECTED_GPU $ARTIFACT_ROOT"
finish_recovery() {
  exit_code=$?
  trap - EXIT
  if (( exit_code == 0 )); then
    terminal_manifest="$RECOVERY_DIR/recovery.complete.json"
  else
    terminal_manifest="$RECOVERY_DIR/recovery.failed.json"
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
trap finish_recovery EXIT

CHECKPOINT_PATH="$(realpath -e "$FAILED_ATTEMPT/factorization/checkpoints/last.pt")"
case "$CHECKPOINT_PATH" in
  "$FAILED_ATTEMPT"/factorization/checkpoints/*) ;;
  *)
    echo "last.pt resolves outside the failed attempt" >&2
    exit 2
    ;;
esac

SOURCE_RECORD="$RECOVERY_DIR/source.json"
"$PYTHON_BIN" - \
  "$SOURCE_RECORD" \
  "$FAILED_ATTEMPT" \
  "$FAILED_MANIFEST" \
  "$CHECKPOINT_PATH" \
  "$UPSTREAM/configs/paper/evaluation.json" \
  "$UPSTREAM/experiments/factorization/evaluate.py" \
  "$RECOVERY_ID" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


output, attempt, failed, checkpoint, config, evaluator = map(Path, sys.argv[1:7])
recovery_id = sys.argv[7]
payload = {
    "schema_version": 2,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "runtime_amendment": "1.0.2",
    "recovery_attempt_id": recovery_id,
    "recovery_reason": "observer_output_transport_sigpipe",
    "scientific_change": False,
    "source_attempt": attempt.name,
    "source_run_failed_sha256": sha256(failed),
    "source_exit_code": json.loads(failed.read_text())["exit_code"],
    "factorization_config_sha256": sha256(attempt / "factorization/config.json"),
    "factorization_metrics_sha256": sha256(attempt / "factorization/metrics.json"),
    "checkpoint_relative_path": checkpoint.relative_to(attempt).as_posix(),
    "checkpoint_sha256": sha256(checkpoint),
    "evaluation_config_sha256": sha256(config),
    "evaluator_source_sha256": sha256(evaluator),
    "command_semantics": {
        "module": "experiments.factorization.evaluate",
        "config": "configs/paper/evaluation.json",
        "run_dir": "factorization",
        "output_dir": "evaluation",
    },
    "preservation": (
        "run.failed.json and the truncated first evaluation log remain immutable; "
        "the recovery appends separately labeled evidence"
    ),
}
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

"$PYTHON_BIN" "$WORKSPACE/scripts/capture_run_manifest.py" \
  --output "$RECOVERY_DIR/recovery.start.json" \
  --paper-id 2607.17674 \
  --arm-id "$ARM_ID" \
  --phase start \
  --protocol-version "$PROTOCOL_VERSION" \
  --invocation "$invocation" \
  --upstream "$UPSTREAM"

echo "evaluation recovery started: $ARM_ID at $(date -u +%FT%TZ)"
(
  cd "$UPSTREAM"
  "$PYTHON_BIN" -m experiments.factorization.evaluate \
    --config configs/paper/evaluation.json \
    --run-dir "$FAILED_ATTEMPT/factorization" \
    --output-dir "$EVALUATION_DIR"
) >>"$LOG_ROOT/evaluation.log" 2>&1

"$PYTHON_BIN" "$WORKSPACE/scripts/hash_artifact_tree.py" \
  "$EVALUATION_DIR" \
  --output "$FAILED_ATTEMPT/evaluation.file-manifest.json"
echo "evaluation recovery completed: $ARM_ID at $(date -u +%FT%TZ)"

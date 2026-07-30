#!/usr/bin/env bash
set -uo pipefail

GPU_SELECTOR="${1:?usage: run_2607_25091_queue.sh GPU EXPECTED_GPU ARM_ID...}"
EXPECTED_GPU="${2:?pass an expected GPU-name substring}"
shift 2

if (( $# == 0 )); then
  echo "pass at least one arm ID" >&2
  exit 2
fi

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$WORKSPACE/scripts/run_guarded_2607_25091_arm.sh"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE/.venv-paper/bin/python}"
CONTINUE_ON_FAILURE="${CONTINUE_ON_FAILURE:-0}"

if [[ "$CONTINUE_ON_FAILURE" != "0" && "$CONTINUE_ON_FAILURE" != "1" ]]; then
  echo "CONTINUE_ON_FAILURE must be 0 or 1" >&2
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "paper environment not found or not executable: $PYTHON_BIN" >&2
  exit 2
fi

cd "$WORKSPACE"

declare -A seen=()
declare -a failures=()
completed=0
skipped=0

for arm_id in "$@"; do
  if [[ -n "${seen[$arm_id]:-}" ]]; then
    echo "duplicate arm in queue: $arm_id" >&2
    exit 2
  fi
  seen["$arm_id"]=1

  if ! arm_json="$("$PYTHON_BIN" -m reprolab.matrixctl show --arm "$arm_id")"
  then
    echo "invalid arm in queue: $arm_id" >&2
    exit 2
  fi
  status="$(jq -r '.status' <<<"$arm_json")"
  if [[ "$status" == "complete" ]]; then
    echo "QUEUE_SKIP arm=$arm_id reason=completed"
    ((skipped += 1))
    continue
  fi

  echo "QUEUE_START arm=$arm_id gpu=$GPU_SELECTOR"
  if "$RUNNER" "$arm_id" "$GPU_SELECTOR" "$EXPECTED_GPU"; then
    echo "QUEUE_COMPLETE arm=$arm_id"
    ((completed += 1))
    continue
  else
    exit_code=$?
  fi

  failures+=("$arm_id:$exit_code")
  echo "QUEUE_FAILED arm=$arm_id exit_code=$exit_code" >&2
  if [[ "$CONTINUE_ON_FAILURE" != "1" ]]; then
    echo "QUEUE_STOP completed=$completed skipped=$skipped failures=1" >&2
    exit "$exit_code"
  fi
done

echo "QUEUE_SUMMARY completed=$completed skipped=$skipped failures=${#failures[@]}"
if (( ${#failures[@]} > 0 )); then
  printf 'QUEUE_FAILURE %s\n' "${failures[@]}" >&2
  exit 1
fi

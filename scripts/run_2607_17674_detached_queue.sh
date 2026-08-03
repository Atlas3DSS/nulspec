#!/usr/bin/env bash
set -euo pipefail

GPU_UUID="${1:?usage: run_2607_17674_detached_queue.sh GPU_UUID EXPECTED_GPU ARTIFACT_ROOT ARM...}"
EXPECTED_GPU="${2:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${3:?pass an absolute artifact root}"
shift 3
if (( $# == 0 )); then
  echo "pass at least one registered arm" >&2
  exit 2
fi
ARMS=("$@")

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHER="$WORKSPACE/scripts/launch_detached_2607_17674_arm.sh"
VALIDATOR="$WORKSPACE/scripts/validate_2607_17674_attempt_artifacts.py"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE/research/replications/2607.17674/work/upstream/.venv/bin/python}"
POLL_SECONDS="${NULSPEC_QUEUE_POLL_SECONDS:-30}"
MAX_OPERATIONAL_RETRIES="${NULSPEC_MAX_OPERATIONAL_RETRIES:-1}"
MAX_GPU_TEMP_C="${NULSPEC_MAX_GPU_TEMP_C:-84}"
MIN_RUNTIME_AVAILABLE_GIB="${NULSPEC_MIN_RUNTIME_AVAILABLE_GIB:-6}"
PROTECTED_UNIT="${NULSPEC_PROTECTED_USER_UNIT:-palworld.service}"
QUEUE_ID="${NULSPEC_QUEUE_ID:-queue-$(date -u +%Y%m%dT%H%M%SZ)-$(git -C "$WORKSPACE" rev-parse --short=12 HEAD)}"
QUEUE_ROOT="$ARTIFACT_ROOT/queues/$QUEUE_ID"
JOURNAL="$QUEUE_ROOT/events.jsonl"

if [[ "$ARTIFACT_ROOT" != /* ]]; then
  echo "artifact root must be absolute" >&2
  exit 2
fi
if [[ ! "$GPU_UUID" =~ ^GPU-[0-9a-fA-F-]+$ ]]; then
  echo "GPU selector must be an exact UUID" >&2
  exit 2
fi
if [[ ! "$QUEUE_ID" =~ ^queue-[A-Za-z0-9_.-]+$ ]]; then
  echo "unsafe queue ID" >&2
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "paper environment not found: $PYTHON_BIN" >&2
  exit 2
fi
if (( POLL_SECONDS < 5 || MAX_OPERATIONAL_RETRIES < 0 )); then
  echo "invalid queue polling or retry policy" >&2
  exit 2
fi

mkdir -p "$QUEUE_ROOT"
exec 8>"${XDG_RUNTIME_DIR:-/tmp}/nulspec-260717674-queue.lock"
if ! flock -n 8; then
  echo "another 2607.17674 queue supervisor is active" >&2
  exit 2
fi

record() {
  local event="$1"
  shift
  jq -nc \
    --arg at_utc "$(date -u +%FT%TZ)" \
    --arg event "$event" \
    --arg detail "$*" \
    '{at_utc:$at_utc,event:$event,detail:$detail}' >> "$JOURNAL"
}

protected_restarts="$(systemctl --user show "$PROTECTED_UNIT" --property=NRestarts --value 2>/dev/null || true)"
if [[ -z "$protected_restarts" ]]; then
  record queue_blocked "protected unit unavailable: $PROTECTED_UNIT"
  exit 3
fi

active_unit=""
stop_experiment_first() {
  local reason="$1"
  record safety_stop "$reason unit=${active_unit:-none}"
  if [[ -n "$active_unit" ]] && systemctl --user is-active --quiet "$active_unit"; then
    systemctl --user stop "$active_unit" || true
  fi
  exit 75
}

check_host_safety() {
  local state restarts available_kib required_kib temp
  state="$(systemctl --user show "$PROTECTED_UNIT" --property=ActiveState --value 2>/dev/null || true)"
  restarts="$(systemctl --user show "$PROTECTED_UNIT" --property=NRestarts --value 2>/dev/null || true)"
  if [[ "$state" != "active" ]]; then
    stop_experiment_first "protected_unit_state=$state"
  fi
  if [[ "$restarts" != "$protected_restarts" ]]; then
    stop_experiment_first "protected_unit_restarts=$restarts baseline=$protected_restarts"
  fi
  available_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
  required_kib="$((MIN_RUNTIME_AVAILABLE_GIB * 1024 * 1024))"
  if [[ -z "$available_kib" || "$available_kib" -lt "$required_kib" ]]; then
    stop_experiment_first "available_memory_kib=${available_kib:-missing} minimum=$required_kib"
  fi
  temp="$(
    nvidia-smi --query-gpu=uuid,temperature.gpu --format=csv,noheader,nounits |
      awk -F', *' -v uuid="$GPU_UUID" '$1 == uuid {print $2; count++} END {if (count != 1) exit 1}'
  )" || stop_experiment_first "gpu_identity_missing=$GPU_UUID"
  if (( temp > MAX_GPU_TEMP_C )); then
    stop_experiment_first "gpu_temperature_c=$temp maximum=$MAX_GPU_TEMP_C"
  fi
}

launch_arm() {
  local arm="$1" stamp attempt_id unit_name
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  attempt_id="attempt-${stamp}-$(git -C "$WORKSPACE" rev-parse --short=12 HEAD)"
  unit_name="nulspec-260717674-$(printf '%s' "$arm" | sha256sum | cut -c1-12)-$stamp"
  check_host_safety
  record arm_launching "arm=$arm attempt=$attempt_id unit=$unit_name.service"
  ATTEMPT_ID="$attempt_id" \
  NULSPEC_ATTEMPT_STAMP="$stamp" \
  NULSPEC_UNIT_NAME="$unit_name" \
  "$LAUNCHER" "$arm" "$GPU_UUID" "$EXPECTED_GPU" "$ARTIFACT_ROOT" >/dev/null
  active_unit="$unit_name.service"
  CURRENT_ATTEMPT="$ARTIFACT_ROOT/runs/$arm/$attempt_id"
  record arm_started "arm=$arm attempt=$attempt_id unit=$active_unit"
}

wait_for_attempt() {
  local arm="$1" inactive_polls=0
  while true; do
    check_host_safety
    if [[ -f "$CURRENT_ATTEMPT/run.complete.json" ]]; then
      if "$PYTHON_BIN" "$VALIDATOR" \
        --attempt "$CURRENT_ATTEMPT" --arm-id "$arm" --require-terminal >/dev/null
      then
        record arm_validated "arm=$arm attempt=$(basename "$CURRENT_ATTEMPT")"
        active_unit=""
        return 0
      fi
      record false_completion "arm=$arm attempt=$(basename "$CURRENT_ATTEMPT")"
      active_unit=""
      return 70
    fi
    if [[ -f "$CURRENT_ATTEMPT/run.failed.json" ]]; then
      local code
      code="$(jq -r '.exit_code // 1' "$CURRENT_ATTEMPT/run.failed.json")"
      record arm_failed "arm=$arm attempt=$(basename "$CURRENT_ATTEMPT") exit_code=$code"
      active_unit=""
      case "$code" in
        70|129|141) return "$code" ;;
        *) return 1 ;;
      esac
    fi
    if systemctl --user is-active --quiet "$active_unit"; then
      inactive_polls=0
    else
      inactive_polls=$((inactive_polls + 1))
      if (( inactive_polls >= 6 )); then
        record missing_terminal "arm=$arm attempt=$(basename "$CURRENT_ATTEMPT") unit=$active_unit"
        active_unit=""
        return 70
      fi
    fi
    sleep "$POLL_SECONDS"
  done
}

record queue_started "arms=${ARMS[*]} gpu=$GPU_UUID protected_unit=$PROTECTED_UNIT protected_restarts=$protected_restarts"
for arm in "${ARMS[@]}"; do
  retries=0
  while true; do
    launch_arm "$arm"
    if wait_for_attempt "$arm"; then
      break
    else
      status=$?
    fi
    if (( status != 70 && status != 129 && status != 141 )); then
      record queue_failed "arm=$arm nonretryable_status=$status"
      exit "$status"
    fi
    if (( retries >= MAX_OPERATIONAL_RETRIES )); then
      record queue_failed "arm=$arm operational_retry_limit=$MAX_OPERATIONAL_RETRIES status=$status"
      exit "$status"
    fi
    retries=$((retries + 1))
    record arm_fresh_retry "arm=$arm retry=$retries previous_status=$status"
  done
done

jq -n \
  --arg completed_at_utc "$(date -u +%FT%TZ)" \
  --arg queue_id "$QUEUE_ID" \
  --argjson arms "$(printf '%s\n' "${ARMS[@]}" | jq -R . | jq -s .)" \
  '{schema_version:1,completed_at_utc:$completed_at_utc,queue_id:$queue_id,arms:$arms,valid:true}' \
  > "$QUEUE_ROOT/queue.complete.json"
record queue_completed "arms=${ARMS[*]}"

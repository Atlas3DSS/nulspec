#!/usr/bin/env bash
# Launch one extension seed at its completed base-seed boundary, then guard it.

set -euo pipefail

if (( $# != 4 )); then
    printf 'usage: %s SEED BASE_PID GPU_UUID CPU_SET\n' "$0" >&2
    exit 64
fi

SEED=$1
BASE_PID=$2
GPU_UUID=$3
CPU_SET=$4
: "${REPLICATION_BASE:?Set REPLICATION_BASE to the experiment root}"
: "${REPLICATION_PYTHON:?Set REPLICATION_PYTHON to the environment interpreter}"
BASE=${REPLICATION_BASE%/}
BASE_OUTPUT="$BASE/outputs/package-vs-intent/seed-$SEED"
EXTENSION_OUTPUT="$BASE/outputs/extensions/seed-$SEED"
MIN_AVAILABLE_KIB=8388608
MAX_TEMP_C=88
: "${PROTECTED_PROCESS_PATTERN:?Set PROTECTED_PROCESS_PATTERN for the shared service}"

if [[ ! "$SEED" =~ ^[1-4]$ ]] || [[ ! "$BASE_PID" =~ ^[0-9]+$ ]]; then
    printf 'invalid seed or PID\n' >&2
    exit 64
fi

log() {
    printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

base_pid_is_expected() {
    [[ -r "/proc/$BASE_PID/cmdline" ]] || return 1
    local command
    command=$(tr '\0' ' ' < "/proc/$BASE_PID/cmdline")
    [[ "$command" == *"$BASE/source/run_trial.py"* ]]
    [[ "$command" == *"--seed $SEED"* ]]
}

extension_pid_is_expected() {
    local pid=$1
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    local command
    command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
    [[ "$command" == *"$BASE/source/run_extensions.py"* ]]
    [[ "$command" == *"--seed $SEED"* ]]
}

safe_to_run() {
    pgrep -f -- "$PROTECTED_PROCESS_PATTERN" >/dev/null || return 1
    local available_kib temperature
    available_kib=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    (( available_kib >= MIN_AVAILABLE_KIB )) || return 1
    temperature=$(nvidia-smi --id="$GPU_UUID" --query-gpu=temperature.gpu \
        --format=csv,noheader,nounits)
    (( temperature < MAX_TEMP_C ))
}

if [[ -f "$EXTENSION_OUTPUT/complete.json" ]]; then
    log "extension seed $SEED already complete"
    exit 0
fi

if ! base_pid_is_expected; then
    if [[ -f "$BASE_OUTPUT/complete.json" ]]; then
        log "base seed $SEED already complete; proceeding to launch checks"
    else
        log "refusing to wait on unvalidated base PID $BASE_PID"
        exit 65
    fi
fi

while base_pid_is_expected; do
    sleep 5
done

if [[ ! -f "$BASE_OUTPUT/complete.json" ]]; then
    log "base seed $SEED stopped without complete.json; extension not launched"
    exit 66
fi
if ! safe_to_run; then
    log "launch guard failed for extension seed $SEED"
    exit 67
fi

mkdir -p "$EXTENSION_OUTPUT"
log "launching extension seed $SEED on $GPU_UUID CPUs $CPU_SET"
PYTHONPATH="$BASE/runtime:$BASE/source" CUDA_VISIBLE_DEVICES="$GPU_UUID" \
    taskset -c "$CPU_SET" nice -n 5 \
    "$REPLICATION_PYTHON" -u "$BASE/source/run_extensions.py" \
    --data-root "$BASE/source/cell_images" \
    --base-output-root "$BASE/outputs/package-vs-intent" \
    --output-root "$BASE/outputs/extensions" \
    --seed "$SEED" --progress \
    >"$EXTENSION_OUTPUT/run.log" 2>&1 &
extension_pid=$!
printf '%s\n' "$extension_pid" >"$EXTENSION_OUTPUT/run.pid"

stop_extension() {
    if extension_pid_is_expected "$extension_pid"; then
        log "stopping extension seed $SEED pid=$extension_pid"
        kill -INT "$extension_pid" 2>/dev/null || true
    fi
}
trap stop_extension INT TERM

while extension_pid_is_expected "$extension_pid"; do
    if ! safe_to_run; then
        log "runtime guard tripped for extension seed $SEED"
        stop_extension
        wait "$extension_pid" || true
        exit 68
    fi
    sleep 10
done

wait "$extension_pid"
if [[ ! -f "$EXTENSION_OUTPUT/complete.json" ]]; then
    log "extension seed $SEED exited without complete.json"
    exit 69
fi
log "extension seed $SEED complete"

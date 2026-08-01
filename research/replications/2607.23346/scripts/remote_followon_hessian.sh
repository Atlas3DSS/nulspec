#!/usr/bin/env bash
# Launch one Hessian diagnostic after its guarded extension wrapper completes.

set -euo pipefail

if (( $# != 4 )); then
    printf 'usage: %s SEED EXTENSION_WATCHER_PID GPU_UUID CPU_SET\n' "$0" >&2
    exit 64
fi

SEED=$1
EXTENSION_WATCHER_PID=$2
GPU_UUID=$3
CPU_SET=$4
: "${REPLICATION_BASE:?Set REPLICATION_BASE to the experiment root}"
: "${REPLICATION_PYTHON:?Set REPLICATION_PYTHON to the environment interpreter}"
BASE=${REPLICATION_BASE%/}
EXTENSION_OUTPUT="$BASE/outputs/extensions/seed-$SEED"
HESSIAN_OUTPUT="$BASE/outputs/hessian-extensions/seed-$SEED"
MIN_AVAILABLE_KIB=8388608
MAX_TEMP_C=88
: "${PROTECTED_PROCESS_PATTERN:?Set PROTECTED_PROCESS_PATTERN for the shared service}"

if [[ ! "$SEED" =~ ^[1-4]$ ]] || [[ ! "$EXTENSION_WATCHER_PID" =~ ^[0-9]+$ ]]; then
    printf 'invalid seed or PID\n' >&2
    exit 64
fi

log() {
    printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

extension_watcher_is_expected() {
    [[ -r "/proc/$EXTENSION_WATCHER_PID/cmdline" ]] || return 1
    local command
    command=$(tr '\0' ' ' < "/proc/$EXTENSION_WATCHER_PID/cmdline")
    [[ "$command" == *"$BASE/source/remote_followon_extension.sh"* ]]
    [[ "$command" == *" $SEED "* ]]
}

hessian_pid_is_expected() {
    local pid=$1
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    local command
    command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
    [[ "$command" == *"$BASE/source/run_hessian_extensions.py"* ]]
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

if [[ -f "$HESSIAN_OUTPUT/complete.json" ]]; then
    log "Hessian seed $SEED already complete"
    exit 0
fi

if ! extension_watcher_is_expected; then
    if [[ -f "$EXTENSION_OUTPUT/complete.json" ]]; then
        log "extension seed $SEED already complete; proceeding to launch checks"
    else
        log "refusing to wait on unvalidated extension watcher PID $EXTENSION_WATCHER_PID"
        exit 65
    fi
fi

while extension_watcher_is_expected; do
    sleep 5
done

if [[ ! -f "$EXTENSION_OUTPUT/complete.json" ]]; then
    log "extension seed $SEED stopped without complete.json; Hessian not launched"
    exit 66
fi
if ! safe_to_run; then
    log "launch guard failed for Hessian seed $SEED"
    exit 67
fi

mkdir -p "$HESSIAN_OUTPUT"
log "launching Hessian seed $SEED on $GPU_UUID CPUs $CPU_SET"
PYTHONPATH="$BASE/runtime:$BASE/source" CUDA_VISIBLE_DEVICES="$GPU_UUID" \
    taskset -c "$CPU_SET" nice -n 5 \
    "$REPLICATION_PYTHON" -u \
    "$BASE/source/run_hessian_extensions.py" \
    --base-output-root "$BASE/outputs/package-vs-intent" \
    --testset "$BASE/source/released/TESTSET.pth" \
    --output-root "$BASE/outputs/hessian-extensions" \
    --seed "$SEED" >"$HESSIAN_OUTPUT/run.log" 2>&1 &
hessian_pid=$!
printf '%s\n' "$hessian_pid" >"$HESSIAN_OUTPUT/run.pid"

stop_hessian() {
    if hessian_pid_is_expected "$hessian_pid"; then
        log "stopping Hessian seed $SEED pid=$hessian_pid"
        kill -INT "$hessian_pid" 2>/dev/null || true
    fi
}
trap stop_hessian INT TERM

while hessian_pid_is_expected "$hessian_pid"; do
    if ! safe_to_run; then
        log "runtime guard tripped for Hessian seed $SEED"
        stop_hessian
        wait "$hessian_pid" || true
        exit 68
    fi
    sleep 10
done

wait "$hessian_pid"
if [[ ! -f "$HESSIAN_OUTPUT/complete.json" ]]; then
    log "Hessian seed $SEED exited without complete.json"
    exit 69
fi
log "Hessian seed $SEED complete"

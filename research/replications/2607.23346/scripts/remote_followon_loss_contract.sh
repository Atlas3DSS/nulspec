#!/usr/bin/env bash
# Launch one post-hoc loss-contract seed after its Hessian wrapper completes.

set -euo pipefail

if (( $# != 4 )); then
    printf 'usage: %s SEED HESSIAN_WATCHER_PID GPU_UUID CPU_SET\n' "$0" >&2
    exit 64
fi

SEED=$1
HESSIAN_WATCHER_PID=$2
GPU_UUID=$3
CPU_SET=$4
: "${REPLICATION_BASE:?Set REPLICATION_BASE to the experiment root}"
: "${REPLICATION_PYTHON:?Set REPLICATION_PYTHON to the environment interpreter}"
BASE=${REPLICATION_BASE%/}
HESSIAN_OUTPUT="$BASE/outputs/hessian-extensions/seed-$SEED"
LOSS_OUTPUT="$BASE/outputs/loss-contract-extensions/seed-$SEED"
MIN_AVAILABLE_KIB=8388608
MAX_TEMP_C=88
: "${PROTECTED_PROCESS_PATTERN:?Set PROTECTED_PROCESS_PATTERN for the shared service}"

if [[ ! "$SEED" =~ ^[1-4]$ ]] || [[ ! "$HESSIAN_WATCHER_PID" =~ ^[0-9]+$ ]]; then
    printf 'invalid seed or PID\n' >&2
    exit 64
fi

log() {
    printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

hessian_watcher_is_expected() {
    [[ -r "/proc/$HESSIAN_WATCHER_PID/cmdline" ]] || return 1
    local command
    command=$(tr '\0' ' ' < "/proc/$HESSIAN_WATCHER_PID/cmdline")
    [[ "$command" == *"$BASE/source/remote_followon_hessian.sh"* ]]
    [[ "$command" == *" $SEED "* ]]
}

loss_pid_is_expected() {
    local pid=$1
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    local command
    command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
    [[ "$command" == *"$BASE/source/run_loss_contract_extension.py"* ]]
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

if [[ -f "$LOSS_OUTPUT/complete.json" ]]; then
    log "loss-contract seed $SEED already complete"
    exit 0
fi

if ! hessian_watcher_is_expected; then
    if [[ -f "$HESSIAN_OUTPUT/complete.json" ]]; then
        log "Hessian seed $SEED already complete; proceeding to launch checks"
    else
        log "refusing to wait on unvalidated Hessian watcher PID $HESSIAN_WATCHER_PID"
        exit 65
    fi
fi

while hessian_watcher_is_expected; do
    sleep 5
done

if [[ ! -f "$HESSIAN_OUTPUT/complete.json" ]]; then
    log "Hessian seed $SEED stopped without complete.json; diagnostic not launched"
    exit 66
fi
if ! safe_to_run; then
    log "launch guard failed for loss-contract seed $SEED"
    exit 67
fi

mkdir -p "$LOSS_OUTPUT"
log "launching loss-contract seed $SEED on $GPU_UUID CPUs $CPU_SET"
PYTHONPATH="$BASE/runtime:$BASE/source" CUDA_VISIBLE_DEVICES="$GPU_UUID" \
    taskset -c "$CPU_SET" nice -n 5 \
    "$REPLICATION_PYTHON" -u \
    "$BASE/source/run_loss_contract_extension.py" \
    --data-root "$BASE/source/cell_images" \
    --base-output-root "$BASE/outputs/package-vs-intent" \
    --output-root "$BASE/outputs/loss-contract-extensions" \
    --seed "$SEED" --progress >"$LOSS_OUTPUT/run.log" 2>&1 &
loss_pid=$!
printf '%s\n' "$loss_pid" >"$LOSS_OUTPUT/run.pid"

stop_loss() {
    if loss_pid_is_expected "$loss_pid"; then
        log "stopping loss-contract seed $SEED pid=$loss_pid"
        kill -INT "$loss_pid" 2>/dev/null || true
    fi
}
trap stop_loss INT TERM

while loss_pid_is_expected "$loss_pid"; do
    if ! safe_to_run; then
        log "runtime guard tripped for loss-contract seed $SEED"
        stop_loss
        wait "$loss_pid" || true
        exit 68
    fi
    sleep 10
done

wait "$loss_pid"
if [[ ! -f "$LOSS_OUTPUT/complete.json" ]]; then
    log "loss-contract seed $SEED exited without complete.json"
    exit 69
fi
log "loss-contract seed $SEED complete"

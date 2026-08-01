#!/usr/bin/env bash
# Fail-closed resource guard for NULSPEC trial processes on the shared dev box.
# It validates exact trial command lines before signaling and never signals the
# protected shared-service process.

set -euo pipefail

: "${REPLICATION_BASE:?Set REPLICATION_BASE to the experiment root}"
: "${PRIMARY_GPU_UUID:?Set PRIMARY_GPU_UUID for seeds 1 and 3}"
: "${SECONDARY_GPU_UUID:?Set SECONDARY_GPU_UUID for seeds 2 and 4}"
BASE=${REPLICATION_BASE%/}
OUTPUT_ROOT="$BASE/outputs/package-vs-intent"
MIN_AVAILABLE_KIB=8388608
MAX_TEMP_C=88
: "${PROTECTED_PROCESS_PATTERN:?Set PROTECTED_PROCESS_PATTERN for the shared service}"

log() {
    printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

validated_pid() {
    local seed=$1
    local pid_file="$OUTPUT_ROOT/seed-$seed/run.pid"
    [[ -f "$pid_file" ]] || return 1
    local pid command
    pid=$(<"$pid_file")
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
    [[ "$command" == *"$BASE/source/run_trial.py"* ]] || return 1
    [[ "$command" == *"--seed $seed"* ]] || return 1
    printf '%s\n' "$pid"
}

terminate_seed() {
    local seed=$1
    local reason=$2
    local pid
    if ! pid=$(validated_pid "$seed"); then
        return 0
    fi
    log "stopping seed $seed pid=$pid: $reason"
    kill -INT "$pid" 2>/dev/null || true
}

all_complete_or_stopped() {
    local seed
    for seed in 1 2 3 4; do
        if [[ -f "$OUTPUT_ROOT/seed-$seed/complete.json" ]]; then
            continue
        fi
        if validated_pid "$seed" >/dev/null; then
            return 1
        fi
    done
    return 0
}

log "guard started; floor=8GiB ceiling=88C"
while ! all_complete_or_stopped; do
    if ! pgrep -f -- "$PROTECTED_PROCESS_PATTERN" >/dev/null; then
        for seed in 1 2 3 4; do
            terminate_seed "$seed" "protected shared-service process absent"
        done
        log "guard tripped on protected-process absence"
        exit 86
    fi

    available_kib=$(grep MemAvailable /proc/meminfo | tr -s ' ' | cut -d' ' -f2)
    if (( available_kib < MIN_AVAILABLE_KIB )); then
        for seed in 1 2 3 4; do
            terminate_seed "$seed" "MemAvailable below 8GiB"
        done
        log "guard tripped on host memory"
        exit 87
    fi

    temp_primary=$(nvidia-smi --id="$PRIMARY_GPU_UUID" --query-gpu=temperature.gpu \
        --format=csv,noheader,nounits)
    temp_secondary=$(nvidia-smi --id="$SECONDARY_GPU_UUID" --query-gpu=temperature.gpu \
        --format=csv,noheader,nounits)
    if (( temp_primary >= MAX_TEMP_C )); then
        terminate_seed 1 "primary GPU reached ${temp_primary}C"
        terminate_seed 3 "primary GPU reached ${temp_primary}C"
        log "guard tripped on primary GPU temperature"
        exit 88
    fi
    if (( temp_secondary >= MAX_TEMP_C )); then
        terminate_seed 2 "secondary GPU reached ${temp_secondary}C"
        terminate_seed 4 "secondary GPU reached ${temp_secondary}C"
        log "guard tripped on secondary GPU temperature"
        exit 89
    fi
    sleep 10
done
log "guard complete; no active incomplete trial remains"

#!/usr/bin/env bash
# At a completed-stage boundary, restart one validated trial with more loaders.

set -euo pipefail

if [[ $# -ne 3 ]]; then
    printf 'usage: %s SEED GPU_UUID CPU_SET\n' "$0" >&2
    exit 64
fi

SEED=$1
GPU_UUID=$2
CPU_SET=$3
: "${REPLICATION_BASE:?Set REPLICATION_BASE to the experiment root}"
: "${REPLICATION_PYTHON:?Set REPLICATION_PYTHON to the environment interpreter}"
BASE=${REPLICATION_BASE%/}
SOURCE_ROOT="$BASE/source"
OUTPUT_ROOT="$BASE/outputs/package-vs-intent"
PYTHON=$REPLICATION_PYTHON
SEED_DIR="$OUTPUT_ROOT/seed-$SEED"
BOUNDARY="$SEED_DIR/stages/sprkd_upstream_direct_init.pth"
: "${PROTECTED_PROCESS_PATTERN:?Set PROTECTED_PROCESS_PATTERN for the shared service}"

log() {
    printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

validated_pid() {
    [[ -f "$SEED_DIR/run.pid" ]] || return 1
    local pid command
    pid=$(<"$SEED_DIR/run.pid")
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
    [[ "$command" == *"$SOURCE_ROOT/run_trial.py"* ]] || return 1
    [[ "$command" == *"--seed $SEED"* ]] || return 1
    [[ "$command" == *"--num-workers 2"* ]] || return 1
    printf '%s\n' "$pid"
}

log "waiting for seed $SEED exact-script stage boundary"
while [[ ! -f "$BOUNDARY" ]]; do
    if [[ -f "$SEED_DIR/complete.json" ]]; then
        log "seed $SEED completed before promotion"
        exit 0
    fi
    if ! validated_pid >/dev/null; then
        log "seed $SEED no longer has the validated two-worker process"
        exit 65
    fi
    sleep 5
done

pid=$(validated_pid)
log "boundary reached; interrupting validated seed $SEED pid=$pid"
kill -INT "$pid"
for _attempt in $(seq 1 30); do
    if ! kill -0 "$pid" 2>/dev/null; then
        break
    fi
    sleep 1
done
if kill -0 "$pid" 2>/dev/null; then
    log "seed $SEED did not stop within 30 seconds; refusing fallback signal"
    exit 66
fi

if ! pgrep -f -- "$PROTECTED_PROCESS_PATTERN" >/dev/null; then
    log "protected service absent; refusing relaunch"
    exit 67
fi
available_kib=$(grep MemAvailable /proc/meminfo | tr -s ' ' | cut -d' ' -f2)
temperature=$(nvidia-smi --id="$GPU_UUID" --query-gpu=temperature.gpu \
    --format=csv,noheader,nounits)
if (( available_kib < 12582912 || temperature >= 80 )); then
    log "relaunch gate failed: available_kib=$available_kib temperature=$temperature"
    exit 68
fi

nohup env \
    PYTHONPATH="$BASE/runtime:$SOURCE_ROOT" \
    CUDA_VISIBLE_DEVICES="$GPU_UUID" \
    taskset -c "$CPU_SET" nice -n 10 \
    "$PYTHON" -u "$SOURCE_ROOT/run_trial.py" \
    --data-root "$SOURCE_ROOT/cell_images" \
    --output-root "$OUTPUT_ROOT" \
    --seed "$SEED" \
    --epochs 500 \
    --teacher-epochs 2 \
    --n-teachers 3 \
    --batch-size 64 \
    --num-workers 6 \
    --progress \
    >>"$SEED_DIR/run.log" 2>&1 &
new_pid=$!
printf '%s\n' "$new_pid" >"$SEED_DIR/run.pid"
log "relaunched seed $SEED pid=$new_pid workers=6 cpu_set=$CPU_SET"

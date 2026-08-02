#!/usr/bin/env bash
set -euo pipefail

ARM_ID="${1:?usage: run_guarded_2607_17674_arm.sh ARM_ID GPU_UUID EXPECTED_GPU ARTIFACT_ROOT}"
GPU_UUID="${2:?pass an exact GPU UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${4:?pass an absolute artifact root}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$WORKSPACE/scripts/run_2607_17674_arm.sh"
MEMORY_HIGH="${NULSPEC_MEMORY_HIGH:-22G}"
MEMORY_MAX="${NULSPEC_MEMORY_MAX:-26G}"
MEMORY_SWAP_MAX="${NULSPEC_MEMORY_SWAP_MAX:-2G}"
CPU_QUOTA="${NULSPEC_CPU_QUOTA:-600%}"
MAX_START_TEMP_C="${NULSPEC_MAX_START_TEMP_C:-72}"

if [[ ! "$GPU_UUID" =~ ^GPU-[0-9a-fA-F-]+$ ]]; then
  echo "GPU selector must be an exact UUID" >&2
  exit 2
fi

gpu_row="$(
  nvidia-smi \
    --query-gpu=uuid,name,temperature.gpu \
    --format=csv,noheader,nounits |
    awk -F', *' -v uuid="$GPU_UUID" '$1 == uuid {print; count++} END {if (count != 1) exit 1}'
)" || {
  echo "exactly one matching GPU was not found" >&2
  exit 2
}
start_temp="$(awk -F', *' '{print $3}' <<<"$gpu_row")"
if (( start_temp > MAX_START_TEMP_C )); then
  echo "GPU start temperature ${start_temp}C exceeds ${MAX_START_TEMP_C}C" >&2
  exit 2
fi

exec systemd-run --user --scope \
  -p TasksMax=2048 \
  -p CPUWeight=20 \
  -p IOWeight=20 \
  -p MemoryHigh="$MEMORY_HIGH" \
  -p MemoryMax="$MEMORY_MAX" \
  -p MemorySwapMax="$MEMORY_SWAP_MAX" \
  -p CPUQuota="$CPU_QUOTA" \
  env NULSPEC_GUARDS_CONFIRMED=1 \
  nice -n 10 ionice -c 2 -n 7 \
  "$RUNNER" "$ARM_ID" "$GPU_UUID" "$EXPECTED_GPU" "$ARTIFACT_ROOT"

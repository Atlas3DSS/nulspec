#!/usr/bin/env bash
set -euo pipefail

ARM_ID="${1:?usage: run_guarded_2607_25091_arm.sh ARM_ID GPU EXPECTED_GPU}"
GPU_SELECTOR="${2:?pass a CUDA device index or UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$WORKSPACE/scripts/run_2607_25091_arm.sh"
HOST_PROFILE="${NULSPEC_HOST_PROFILE:-shared}"

common_properties=(
  -p TasksMax=2048
  -p CPUWeight=20
  -p IOWeight=20
)

if [[ "$HOST_PROFILE" == "shared" ]]; then
  exec systemd-run --user --scope \
    "${common_properties[@]}" \
    -p MemoryHigh=12G \
    -p MemoryMax=16G \
    -p MemorySwapMax=2G \
    -p CPUQuota=800% \
    env NULSPEC_HOST_PROFILE=shared NULSPEC_SHARED_GUARDS_CONFIRMED=1 \
    nice -n 10 ionice -c 2 -n 7 \
    "$RUNNER" "$ARM_ID" "$GPU_SELECTOR" "$EXPECTED_GPU"
fi

if [[ "$HOST_PROFILE" != "dedicated" ]]; then
  echo "NULSPEC_HOST_PROFILE must be 'shared' or 'dedicated'" >&2
  exit 2
fi

exec systemd-run --user --scope \
  "${common_properties[@]}" \
  -p MemoryHigh=32G \
  -p MemoryMax=48G \
  -p MemorySwapMax=4G \
  -p CPUQuota=1200% \
  env NULSPEC_HOST_PROFILE=dedicated \
  nice -n 10 ionice -c 2 -n 7 \
  "$RUNNER" "$ARM_ID" "$GPU_SELECTOR" "$EXPECTED_GPU"

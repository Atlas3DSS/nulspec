#!/usr/bin/env bash
set -euo pipefail

ARM_ID="${1:?usage: run_guarded_2607_17674_arm.sh ARM_ID GPU_UUID EXPECTED_GPU ARTIFACT_ROOT}"
GPU_UUID="${2:?pass an exact GPU UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${4:?pass an absolute artifact root}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# This compatibility entry point is intentionally detached. A remote SSH
# observer may disappear without owning or signalling the scientific process.
exec "$WORKSPACE/scripts/launch_detached_2607_17674_arm.sh" \
  "$ARM_ID" "$GPU_UUID" "$EXPECTED_GPU" "$ARTIFACT_ROOT"

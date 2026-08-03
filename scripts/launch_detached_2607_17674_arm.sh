#!/usr/bin/env bash
set -euo pipefail

ARM_ID="${1:?usage: launch_detached_2607_17674_arm.sh ARM_ID GPU_UUID EXPECTED_GPU ARTIFACT_ROOT}"
GPU_UUID="${2:?pass an exact GPU UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${4:?pass an absolute artifact root}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$WORKSPACE/scripts/run_2607_17674_arm.sh"
MEMORY_HIGH="${NULSPEC_MEMORY_HIGH:-8G}"
MEMORY_MAX="${NULSPEC_MEMORY_MAX:-12G}"
MEMORY_SWAP_MAX="${NULSPEC_MEMORY_SWAP_MAX:-2G}"
CPU_QUOTA="${NULSPEC_CPU_QUOTA:-600%}"
MAX_START_TEMP_C="${NULSPEC_MAX_START_TEMP_C:-72}"

if [[ ! "$GPU_UUID" =~ ^GPU-[0-9a-fA-F-]+$ ]]; then
  echo "GPU selector must be an exact UUID" >&2
  exit 2
fi
if [[ "$ARTIFACT_ROOT" != /* ]]; then
  echo "artifact root must be absolute" >&2
  exit 2
fi

gpu_row="$(
  nvidia-smi --query-gpu=uuid,name,temperature.gpu --format=csv,noheader,nounits |
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

stamp="${NULSPEC_ATTEMPT_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
git_short="$(git -C "$WORKSPACE" rev-parse --short=12 HEAD)"
attempt_id="${ATTEMPT_ID:-attempt-${stamp}-${git_short}}"
arm_hash="$(printf '%s' "$ARM_ID" | sha256sum | cut -c1-12)"
unit_name="${NULSPEC_UNIT_NAME:-nulspec-260717674-${arm_hash}-${stamp}}"
if [[ ! "$attempt_id" =~ ^attempt-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$ ]]; then
  echo "attempt ID is not immutable-attempt shaped: $attempt_id" >&2
  exit 2
fi
if [[ ! "$unit_name" =~ ^[A-Za-z0-9_.@-]+$ ]]; then
  echo "unsafe systemd unit name" >&2
  exit 2
fi
if systemctl --user is-active --quiet "$unit_name.service"; then
  echo "unit is already active: $unit_name.service" >&2
  exit 2
fi

systemd-run --user \
  --unit="$unit_name" \
  --collect \
  --service-type=exec \
  --property=TasksMax=2048 \
  --property=CPUWeight=20 \
  --property=IOWeight=20 \
  --property=MemoryHigh="$MEMORY_HIGH" \
  --property=MemoryMax="$MEMORY_MAX" \
  --property=MemorySwapMax="$MEMORY_SWAP_MAX" \
  --property=CPUQuota="$CPU_QUOTA" \
  --property=KillMode=control-group \
  --property=TimeoutStopSec=180 \
  --setenv=NULSPEC_GUARDS_CONFIRMED=1 \
  --setenv=ATTEMPT_ID="$attempt_id" \
  nice -n 10 ionice -c 2 -n 7 \
  "$RUNNER" "$ARM_ID" "$GPU_UUID" "$EXPECTED_GPU" "$ARTIFACT_ROOT"

launch_root="$ARTIFACT_ROOT/launches"
mkdir -p "$launch_root"
receipt="$launch_root/${attempt_id}.json"
if [[ -e "$receipt" ]]; then
  echo "refusing to overwrite launch receipt: $receipt" >&2
  exit 2
fi
jq -n \
  --arg schema_version "1" \
  --arg launched_at_utc "$(date -u +%FT%TZ)" \
  --arg arm_id "$ARM_ID" \
  --arg attempt_id "$attempt_id" \
  --arg unit "$unit_name.service" \
  --arg gpu_uuid "$GPU_UUID" \
  --arg git_head "$(git -C "$WORKSPACE" rev-parse HEAD)" \
  '{
    schema_version: ($schema_version | tonumber),
    launched_at_utc: $launched_at_utc,
    arm_id: $arm_id,
    attempt_id: $attempt_id,
    unit: $unit,
    gpu_uuid: $gpu_uuid,
    git_head: $git_head,
    detached_remote_service: true
  }' > "$receipt"
jq '.' "$receipt"

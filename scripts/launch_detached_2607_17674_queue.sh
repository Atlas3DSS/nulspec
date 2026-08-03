#!/usr/bin/env bash
set -euo pipefail

GPU_UUID="${1:?usage: launch_detached_2607_17674_queue.sh GPU_UUID EXPECTED_GPU ARTIFACT_ROOT ARM...}"
EXPECTED_GPU="${2:?pass an expected GPU-name substring}"
ARTIFACT_ROOT="${3:?pass an absolute artifact root}"
shift 3
if (( $# == 0 )); then
  echo "pass at least one registered arm" >&2
  exit 2
fi

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$WORKSPACE/scripts/run_2607_17674_detached_queue.sh"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
unit_name="${NULSPEC_QUEUE_UNIT_NAME:-nulspec-260717674-queue-$stamp}"

systemd-run --user \
  --unit="$unit_name" \
  --collect \
  --service-type=exec \
  --property=TasksMax=256 \
  --property=CPUWeight=10 \
  --property=IOWeight=10 \
  --property=MemoryMax=512M \
  --property=KillMode=control-group \
  --setenv=NULSPEC_QUEUE_ID="queue-${stamp}-$(git -C "$WORKSPACE" rev-parse --short=12 HEAD)" \
  nice -n 15 ionice -c 3 \
  "$RUNNER" "$GPU_UUID" "$EXPECTED_GPU" "$ARTIFACT_ROOT" "$@"

jq -n \
  --arg launched_at_utc "$(date -u +%FT%TZ)" \
  --arg unit "$unit_name.service" \
  --arg git_head "$(git -C "$WORKSPACE" rev-parse HEAD)" \
  --argjson arms "$(printf '%s\n' "$@" | jq -R . | jq -s .)" \
  '{schema_version:1,launched_at_utc:$launched_at_utc,unit:$unit,git_head:$git_head,arms:$arms,detached_remote_service:true}'

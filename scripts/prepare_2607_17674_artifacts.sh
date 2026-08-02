#!/usr/bin/env bash
set -euo pipefail

MODEL_KEY="${1:?usage: prepare_2607_17674_artifacts.sh MODEL_KEY ARTIFACT_ROOT}"
ARTIFACT_ROOT="${2:?pass an absolute artifact root}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${UPSTREAM:-$WORKSPACE/research/replications/2607.17674/work/upstream}"
PROTOCOL="$WORKSPACE/protocols/2607.17674/config.json"
PYTHON_BIN="$UPSTREAM/.venv/bin/python"

USER_ROOT="$(getent passwd "$(id -u)" | cut -d: -f6)"
if [[ -z "$USER_ROOT" || "$USER_ROOT" != /* ]]; then
  echo "could not resolve the current user's home directory" >&2
  exit 2
fi
if [[ "$ARTIFACT_ROOT" != /* ]]; then
  echo "artifact root must be an absolute path" >&2
  exit 2
fi
case "$ARTIFACT_ROOT" in
  /|/home|"$USER_ROOT"|"$WORKSPACE")
    echo "refusing broad artifact root: $ARTIFACT_ROOT" >&2
    exit 2
    ;;
esac
if [[ "$ARTIFACT_ROOT" == "$WORKSPACE"/* && "$ARTIFACT_ROOT" != "$WORKSPACE"/research/replications/2607.17674/* ]]; then
  echo "artifact root inside the repository must stay within the study workspace" >&2
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "frozen upstream environment is missing: $PYTHON_BIN" >&2
  exit 2
fi

"$PYTHON_BIN" "$WORKSPACE/scripts/validate_2607_17674_protocol.py" \
  --upstream "$UPSTREAM" >/dev/null

MODEL_ID="$(jq -er --arg key "$MODEL_KEY" '.models[$key].hf_id' "$PROTOCOL")"
MODEL_REVISION="$(jq -er --arg key "$MODEL_KEY" '.models[$key].revision' "$PROTOCOL")"
MODEL_ROOT="$ARTIFACT_ROOT/models/$MODEL_KEY/$MODEL_REVISION"
DATA_ROOT="$ARTIFACT_ROOT/data/paper"
PREP_ROOT="$ARTIFACT_ROOT/preparation"
PREP_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PREP_ATTEMPT="$PREP_ROOT/$PREP_STAMP-$MODEL_KEY"

if [[ -e "$PREP_ATTEMPT" ]]; then
  echo "refusing to overwrite preparation attempt: $PREP_ATTEMPT" >&2
  exit 2
fi
mkdir -p "$PREP_ATTEMPT"
exec > >(tee -a "$PREP_ATTEMPT/prepare.log") 2>&1

echo "preparation started: $(date -u +%FT%TZ)"
echo "model: $MODEL_ID at $MODEL_REVISION"

mkdir -p "$MODEL_ROOT"
hf download "$MODEL_ID" \
  --revision "$MODEL_REVISION" \
  --local-dir "$MODEL_ROOT"
"$PYTHON_BIN" "$WORKSPACE/scripts/hash_artifact_tree.py" \
  "$MODEL_ROOT" \
  --output "$PREP_ATTEMPT/model-manifest.json" \
  --exclude-prefix .cache

if [[ ! -f "$ARTIFACT_ROOT/data/benchmark.complete.json" ]]; then
  if [[ -e "$DATA_ROOT" ]]; then
    echo "benchmark data exists without a completion manifest; refusing overwrite" >&2
    exit 2
  fi
  mkdir -p "$ARTIFACT_ROOT/data"
  jq --arg data_dir "$DATA_ROOT" '.data_dir = $data_dir' \
    "$UPSTREAM/configs/paper/benchmark.json" \
    > "$PREP_ATTEMPT/benchmark.runtime.json"
  (
    cd "$UPSTREAM"
    CUDA_VISIBLE_DEVICES="" "$PYTHON_BIN" \
      -m experiments.benchmark.generate \
      "$PREP_ATTEMPT/benchmark.runtime.json"
  )
  "$PYTHON_BIN" "$WORKSPACE/scripts/hash_artifact_tree.py" \
    "$DATA_ROOT" \
    --output "$ARTIFACT_ROOT/data/benchmark.file-manifest.json"
  jq -n \
    --arg completed_at "$(date -u +%FT%TZ)" \
    --arg config_sha256 "$(sha256sum "$UPSTREAM/configs/paper/benchmark.json" | awk '{print $1}')" \
    --arg file_manifest_sha256 "$(sha256sum "$ARTIFACT_ROOT/data/benchmark.file-manifest.json" | awk '{print $1}')" \
    '{schema_version:1, completed_at:$completed_at, config_sha256:$config_sha256, file_manifest_sha256:$file_manifest_sha256}' \
    > "$ARTIFACT_ROOT/data/benchmark.complete.json"
else
  echo "reusing completed benchmark data"
fi

jq -n \
  --arg completed_at "$(date -u +%FT%TZ)" \
  --arg model "$MODEL_ID" \
  --arg revision "$MODEL_REVISION" \
  --arg manifest_sha256 "$(sha256sum "$PREP_ATTEMPT/model-manifest.json" | awk '{print $1}')" \
  '{schema_version:1, completed_at:$completed_at, model:$model, revision:$revision, manifest_sha256:$manifest_sha256}' \
  > "$PREP_ATTEMPT/complete.json"
echo "preparation completed: $(date -u +%FT%TZ)"

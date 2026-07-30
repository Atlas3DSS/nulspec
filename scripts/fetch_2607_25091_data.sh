#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY="mr3haque/SLM-RL-Agents-Data"
REVISION="2cee50d2989aadebfd5af529937c99f7d539287a"
TARGET="${DATA_ROOT:-$WORKSPACE/paper_repro/data_release}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v hf >/dev/null 2>&1; then
  echo "hf CLI is required" >&2
  exit 2
fi

download_dir="$(mktemp -d /tmp/2607.25091-data.XXXXXX)"
cleanup() {
  rm -rf -- "$download_dir"
}
trap cleanup EXIT

hf download "$REPOSITORY" \
  --repo-type dataset \
  --revision "$REVISION" \
  --include 'datasets/**' \
  --local-dir "$download_dir"

hf download "$REPOSITORY" \
  results/all_results.json \
  --repo-type dataset \
  --revision "$REVISION" \
  --local-dir "$download_dir"

mkdir -p "$TARGET"

while IFS= read -r -d '' source_path; do
  relative="${source_path#"$download_dir"/}"
  destination="$TARGET/$relative"
  if [[ -e "$destination" ]]; then
    source_hash="$(sha256sum "$source_path" | awk '{print $1}')"
    destination_hash="$(sha256sum "$destination" | awk '{print $1}')"
    if [[ "$source_hash" != "$destination_hash" ]]; then
      echo "refusing to overwrite mismatched file: $destination" >&2
      exit 2
    fi
    continue
  fi
  mkdir -p "$(dirname "$destination")"
  cp -- "$source_path" "$destination"
done < <(
  find "$download_dir/datasets" "$download_dir/results" \
    -type f -print0
)

PYTHONPATH="$WORKSPACE${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON_BIN" "$WORKSPACE/scripts/validate_protocol.py" \
    --data-root "$TARGET" \
    --skip-upstream

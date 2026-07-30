#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENVIRONMENT="${PAPER_ENV:-$WORKSPACE/.venv-paper}"
PYTHON="${PYTHON_310:-python3.10}"

if [[ -e "$ENVIRONMENT" ]]; then
  echo "refusing to overwrite existing environment: $ENVIRONMENT" >&2
  exit 2
fi
if [[ ! -d "$WORKSPACE/paper_repro/SLM-RL-Agents/.git" ]]; then
  echo "bootstrap the pinned upstream checkout first" >&2
  exit 2
fi

uv venv --python "$PYTHON" "$ENVIRONMENT"
uv pip install \
  --python "$ENVIRONMENT/bin/python" \
  --index-url https://download.pytorch.org/whl/cu121 \
  'torch==2.5.1'
uv pip install \
  --python "$ENVIRONMENT/bin/python" \
  --requirements "$WORKSPACE/environments/paper/requirements.lock.txt"
uv pip install \
  --python "$ENVIRONMENT/bin/python" \
  -e "$WORKSPACE/paper_repro/SLM-RL-Agents"

env -u PYTHONPATH "$ENVIRONMENT/bin/python" \
  "$WORKSPACE/scripts/check_paper_environment.py" \
  --upstream "$WORKSPACE/paper_repro/SLM-RL-Agents"

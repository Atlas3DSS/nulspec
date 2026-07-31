#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

cd "$ROOT"
arguments=(
  --judgments calibration=extension/artifacts/judgments/calibration.jsonl \
  --judgments exact-70m=extension/artifacts/judgments/exact-70m.jsonl \
  --judgments corrected-70m=extension/artifacts/judgments/corrected-70m.jsonl \
  --judgments exact-410m=extension/artifacts/judgments/exact-410m.jsonl \
  --judgments corrected-410m=extension/artifacts/judgments/corrected-410m.jsonl \
  --sample-size "${OUTER_TEACHER_SAMPLE_SIZE:-20}"
)
for optional_label in exact-160m corrected-160m; do
  judgment="extension/artifacts/judgments/$optional_label.jsonl"
  if [[ -f "$judgment" ]]; then
    arguments+=(--judgments "$optional_label=$judgment")
  fi
done

"$PYTHON" extension/outer_teacher.py "${arguments[@]}"

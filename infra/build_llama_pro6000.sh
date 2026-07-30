#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/dev_genius/engines/llama.cpp}"
CMAKE="${CMAKE:-$ROOT/.build-venv/bin/cmake}"
BUILD_DIR="${BUILD_DIR:-$ROOT/build-cuda-pro6000}"

cd "$ROOT"

"$CMAKE" -S . -B "$BUILD_DIR" \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=120-real

"$CMAKE" --build "$BUILD_DIR" \
  --config Release \
  --parallel "${BUILD_JOBS:-6}" \
  --target llama-server llama-bench

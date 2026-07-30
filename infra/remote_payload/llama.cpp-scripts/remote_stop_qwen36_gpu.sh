#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/dev_genius/engines/llama.cpp}"
GPU_NAME="${GPU_NAME:?Set GPU_NAME, for example 3090 or 4090}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
PID_FILE="$LOG_DIR/llama-server-${GPU_NAME}.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No pid file for ${GPU_NAME}: $PID_FILE"
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]]; then
  rm -f "$PID_FILE"
  echo "Removed empty pid file for ${GPU_NAME}"
  exit 0
fi

if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "${GPU_NAME} server was not running"
  exit 0
fi

echo "Stopping ${GPU_NAME} llama-server pid ${pid}"
kill "$pid"
for _ in {1..30}; do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "Stopped ${GPU_NAME}"
    exit 0
  fi
  sleep 0.5
done

echo "Process ${pid} did not stop cleanly; sending SIGKILL"
kill -9 "$pid" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Stopped ${GPU_NAME}"

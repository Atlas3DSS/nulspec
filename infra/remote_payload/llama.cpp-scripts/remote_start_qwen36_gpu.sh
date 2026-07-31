#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/dev_genius/engines/llama.cpp}"
SERVER_BIN="${SERVER_BIN:-$ROOT/build-cuda/bin/llama-server}"
MODEL="${MODEL:-$HOME/dev_genius/models/gguf/qwen36-heretic2/Qwen3.6-27B-Heretic2-Uncensored-Finetune-Thinking.Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH-$HOME/dev_genius/models/gguf/unsloth-qwen36/mmproj-F16.gguf}"

GPU_INDEX="${GPU_INDEX:-}"
GPU_UUID="${GPU_UUID:-}"
EXPECTED_GPU_NAME="${EXPECTED_GPU_NAME:-}"
GPU_NAME="${GPU_NAME:-gpu${GPU_INDEX:-unknown}}"
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
ALIAS="${ALIAS:-qwen3.6-27b-q4-${GPU_NAME}}"

CTX_SIZE="${CTX_SIZE:-50000}"
BATCH_SIZE="${BATCH_SIZE:-2048}"
UBATCH_SIZE="${UBATCH_SIZE:-512}"
PARALLEL="${PARALLEL:-1}"
CACHE_TYPE_K="${CACHE_TYPE_K:-f16}"
CACHE_TYPE_V="${CACHE_TYPE_V:-f16}"
FLASH_ATTN="${FLASH_ATTN:-on}"
NGL="${NGL:-999}"
LORA_PATH="${LORA_PATH:-}"
THREADS="${THREADS:-8}"
THREADS_BATCH="${THREADS_BATCH:-$THREADS}"
NICE_LEVEL="${NICE_LEVEL:-10}"
IONICE_LEVEL="${IONICE_LEVEL:-7}"
MIN_AVAILABLE_MEM_GIB="${MIN_AVAILABLE_MEM_GIB:-10}"
DRY_RUN="${DRY_RUN:-0}"

LOG_DIR="${LOG_DIR:-$ROOT/logs}"
mkdir -p "$LOG_DIR"

PID_FILE="$LOG_DIR/llama-server-${GPU_NAME}.pid"
STDOUT_LOG="$LOG_DIR/llama-server-${GPU_NAME}.out.log"
LLAMA_LOG="$LOG_DIR/llama-server-${GPU_NAME}.llama.log"

if [[ ! -x "$SERVER_BIN" ]]; then
  echo "llama-server binary not found or not executable: $SERVER_BIN" >&2
  exit 1
fi

if [[ ! -f "$MODEL" ]]; then
  echo "model not found: $MODEL" >&2
  exit 1
fi

if [[ -z "$GPU_UUID" && -z "$GPU_INDEX" ]]; then
  echo "Set GPU_UUID (preferred) or GPU_INDEX" >&2
  exit 1
fi

selected_index=""
selected_uuid=""
selected_name=""
while IFS=',' read -r candidate_index candidate_uuid candidate_name; do
  candidate_index="${candidate_index//[[:space:]]/}"
  candidate_uuid="${candidate_uuid//[[:space:]]/}"
  candidate_name="${candidate_name#"${candidate_name%%[![:space:]]*}"}"
  if [[ -n "$GPU_UUID" && "$candidate_uuid" == "$GPU_UUID" ]] ||
     [[ -z "$GPU_UUID" && "$candidate_index" == "$GPU_INDEX" ]]; then
    selected_index="$candidate_index"
    selected_uuid="$candidate_uuid"
    selected_name="$candidate_name"
    break
  fi
done < <(nvidia-smi --query-gpu=index,uuid,name --format=csv,noheader)

if [[ -z "$selected_uuid" ]]; then
  echo "Requested GPU not found: uuid=${GPU_UUID:-unset} index=${GPU_INDEX:-unset}" >&2
  exit 1
fi

if [[ -n "$EXPECTED_GPU_NAME" && "$selected_name" != *"$EXPECTED_GPU_NAME"* ]]; then
  echo "GPU identity check failed: expected '$EXPECTED_GPU_NAME', found '$selected_name'" >&2
  exit 1
fi

# UUID selection is stable even when CUDA and nvidia-smi enumerate mixed
# Blackwell/Ampere cards differently.
GPU_SELECTOR="$selected_uuid"
GPU_INDEX="$selected_index"

available_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
minimum_kib="$((MIN_AVAILABLE_MEM_GIB * 1024 * 1024))"
if (( available_kib < minimum_kib )); then
  echo "Refusing to start with less than ${MIN_AVAILABLE_MEM_GIB} GiB available RAM" >&2
  exit 1
fi

MMPROJ_ARGS=()
if [[ -n "$MMPROJ_PATH" ]]; then
  if [[ ! -f "$MMPROJ_PATH" ]]; then
    echo "mmproj not found: $MMPROJ_PATH" >&2
    exit 1
  fi
  MMPROJ_ARGS=(--mmproj "$MMPROJ_PATH")
fi

LORA_ARGS=()
if [[ -n "$LORA_PATH" ]]; then
  if [[ ! -f "$LORA_PATH" ]]; then
    echo "LoRA adapter not found: $LORA_PATH" >&2
    exit 1
  fi
  LORA_ARGS=(--lora "$LORA_PATH")
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Stopping existing ${GPU_NAME} llama-server pid ${old_pid}"
    kill "$old_pid"
    for _ in {1..30}; do
      if ! kill -0 "$old_pid" 2>/dev/null; then
        break
      fi
      sleep 0.5
    done
    if kill -0 "$old_pid" 2>/dev/null; then
      echo "Existing pid ${old_pid} did not stop cleanly; sending SIGKILL"
      kill -9 "$old_pid" 2>/dev/null || true
    fi
  fi
fi

echo "Starting ${ALIAS} on GPU ${GPU_INDEX}: ${selected_name} (${selected_uuid}) port ${PORT}"
echo "ctx=${CTX_SIZE} batch=${BATCH_SIZE} ubatch=${UBATCH_SIZE} threads=${THREADS}/${THREADS_BATCH} kv=${CACHE_TYPE_K}/${CACHE_TYPE_V} fa=${FLASH_ATTN} mmproj=${MMPROJ_PATH:-none} lora=${LORA_PATH:-none}"
echo "Host guardrails: nice=${NICE_LEVEL} ionice=best-effort/${IONICE_LEVEL} min_available_ram=${MIN_AVAILABLE_MEM_GIB}GiB"

if [[ "$DRY_RUN" == "1" ]]; then
  env CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES="$GPU_SELECTOR" "$SERVER_BIN" --version
  exit 0
fi

setsid nice -n "$NICE_LEVEL" ionice -c 2 -n "$IONICE_LEVEL" \
  env CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES="$GPU_SELECTOR" "$SERVER_BIN" \
  -m "$MODEL" \
  --alias "$ALIAS" \
  -ngl "$NGL" \
  -fa "$FLASH_ATTN" \
  -c "$CTX_SIZE" \
  -np "$PARALLEL" \
  -b "$BATCH_SIZE" \
  -ub "$UBATCH_SIZE" \
  -ctk "$CACHE_TYPE_K" \
  -ctv "$CACHE_TYPE_V" \
  --threads "$THREADS" \
  --threads-batch "$THREADS_BATCH" \
  "${MMPROJ_ARGS[@]}" \
  "${LORA_ARGS[@]}" \
  --metrics \
  --host "$HOST" \
  --port "$PORT" \
  --log-file "$LLAMA_LOG" \
  > "$STDOUT_LOG" 2>&1 &

pid="$!"
echo "$pid" > "$PID_FILE"

for _ in {1..120}; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "llama-server exited during startup. Last log lines:" >&2
    tail -n 80 "$STDOUT_LOG" >&2 || true
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "Healthy: http://127.0.0.1:${PORT}"
    echo "PID: ${pid}"
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for health on port ${PORT}. Last log lines:" >&2
tail -n 80 "$STDOUT_LOG" >&2 || true
exit 1

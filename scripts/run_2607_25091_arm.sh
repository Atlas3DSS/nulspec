#!/usr/bin/env bash
set -euo pipefail

ARM_ID="${1:?usage: run_2607_25091_arm.sh ARM_ID GPU_SELECTOR EXPECTED_GPU}"
GPU_SELECTOR="${2:?pass a CUDA device index or UUID}"
EXPECTED_GPU="${3:?pass an expected GPU-name substring}"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="$WORKSPACE/paper_repro/SLM-RL-Agents"
DATA_ROOT="${DATA_ROOT:-$WORKSPACE/paper_repro/data_release}"
RUNS_ROOT="${RUNS_ROOT:-$WORKSPACE/paper_repro/full_matrix_runs}"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE/.venv-paper/bin/python}"
PROTOCOL_VERSION="1.0.0"
MIN_AVAILABLE_GIB="${MIN_AVAILABLE_GIB:-8}"
COMPAT_ROOT="${COMPAT_ROOT:-}"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_SELECTOR"
export TOKENIZERS_PARALLELISM=false
export WANDB_MODE=disabled
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export PYTHONPATH="${COMPAT_ROOT:+$COMPAT_ROOT:}$WORKSPACE:$UPSTREAM${PYTHONPATH:+:$PYTHONPATH}"

cd "$WORKSPACE"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "paper environment not found or not executable: $PYTHON_BIN" >&2
  echo "run environments/paper/create.sh before compute" >&2
  exit 2
fi

if [[ ! -d .git ]]; then
  echo "top-level Git repository is required" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain=v1)" && "${ALLOW_DIRTY:-0}" != "1" ]]; then
  echo "working tree is dirty; commit protocol/code before compute" >&2
  git status --short >&2
  exit 2
fi

"$PYTHON_BIN" scripts/validate_protocol.py >/dev/null

if ! git -C "$UPSTREAM" apply --reverse --check \
  "$WORKSPACE/patches/2607.25091/reproduction.patch" >/dev/null 2>&1
then
  echo "upstream reproduction patch is not applied exactly" >&2
  exit 2
fi

arm_json="$(
  "$PYTHON_BIN" -m reprolab.matrixctl show --arm "$ARM_ID"
)"
TRACK="$(jq -r '.track' <<<"$arm_json")"
MODEL="$(jq -r '.model' <<<"$arm_json")"
DATASET="$(jq -r '.dataset' <<<"$arm_json")"
SEED_VALUE="$(jq -r '.seed' <<<"$arm_json")"
MODEL_NAME="$(jq -r '.model_config.hf_id' <<<"$arm_json")"
LORA_R="$(jq -r '.model_config.lora_rank' <<<"$arm_json")"
REWARD_DTYPE="$(jq -r '.track_config.reward_dtype' <<<"$arm_json")"

actual_gpu="$(
  "$PYTHON_BIN" -c \
    'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO CUDA")'
)"
if [[ "$actual_gpu" != *"$EXPECTED_GPU"* ]]; then
  echo "GPU identity check failed: expected '$EXPECTED_GPU', got '$actual_gpu'" >&2
  exit 2
fi

"$PYTHON_BIN" scripts/check_paper_environment.py \
  --upstream "$UPSTREAM"

available_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
required_kib="$((MIN_AVAILABLE_GIB * 1024 * 1024))"
if (( available_kib < required_kib )); then
  echo "available system RAM is below ${MIN_AVAILABLE_GIB} GiB" >&2
  exit 2
fi

if [[ "${NULSPEC_HOST_PROFILE:-shared}" == "shared" ]]; then
  if [[ "${NULSPEC_SHARED_GUARDS_CONFIRMED:-0}" != "1" ]]; then
    echo "shared-host runs must use run_guarded_2607_25091_arm.sh" >&2
    exit 2
  fi
  lock_root="${XDG_RUNTIME_DIR:-/tmp}"
  exec 9>"$lock_root/nulspec-experiment.lock"
  if ! flock -n 9; then
    echo "another shared-host experiment holds the concurrency lock" >&2
    exit 2
  fi
  other_experiment_count="$(
    {
      pgrep -af 'train_(sft|reward|ppo)\\.py|paired_eval\\.py' || true
    } | awk -v current_pid="$$" '$1 != current_pid {count++} END {print count + 0}'
  )"
  if (( other_experiment_count > 0 )); then
    echo "another shared-host experiment is active; refusing concurrent launch" >&2
    exit 2
  fi
fi

if [[ "${PREFLIGHT_ONLY:-0}" == "1" ]]; then
  jq -n \
    --arg arm_id "$ARM_ID" \
    --arg protocol "$PROTOCOL_VERSION" \
    --arg gpu "$actual_gpu" \
    --arg python "$PYTHON_BIN" \
    --argjson available_memory_kib "$available_kib" \
    '{
      status: "preflight-passed",
      arm_id: $arm_id,
      protocol_version: $protocol,
      gpu: $gpu,
      python: $python,
      available_memory_kib: $available_memory_kib,
      training_started: false
    }'
  exit 0
fi

git_short="$(git rev-parse --short=12 HEAD)"
attempt_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
ATTEMPT_ID="${ATTEMPT_ID:-attempt-${attempt_stamp}-${git_short}}"
RUN_ROOT="$RUNS_ROOT/$ARM_ID/$ATTEMPT_ID"
LOG_ROOT="$RUN_ROOT/logs"

if [[ -e "$RUN_ROOT" ]]; then
  echo "refusing to overwrite attempt: $RUN_ROOT" >&2
  exit 2
fi
mkdir -p "$LOG_ROOT"

invocation="$0 $ARM_ID $GPU_SELECTOR $EXPECTED_GPU"
"$PYTHON_BIN" scripts/capture_run_manifest.py \
  --output "$RUN_ROOT/run.start.json" \
  --arm-id "$ARM_ID" \
  --phase start \
  --protocol-version "$PROTOCOL_VERSION" \
  --invocation "$invocation"

finish_attempt() {
  exit_code=$?
  trap - EXIT
  if (( exit_code == 0 )); then
    terminal_manifest="$RUN_ROOT/run.complete.json"
  else
    terminal_manifest="$RUN_ROOT/run.failed.json"
  fi
  "$PYTHON_BIN" scripts/capture_run_manifest.py \
    --output "$terminal_manifest" \
    --arm-id "$ARM_ID" \
    --phase end \
    --protocol-version "$PROTOCOL_VERSION" \
    --invocation "$invocation" \
    --exit-code "$exit_code" || true
  exit "$exit_code"
}
trap finish_attempt EXIT

DATA="$DATA_ROOT/datasets/$DATASET"
for file in sft_train.json sft_eval.json preference_train.json preference_eval.json; do
  if [[ ! -f "$DATA/$file" ]]; then
    echo "missing released data: $DATA/$file" >&2
    exit 2
  fi
done

SFT_DIR="$RUN_ROOT/sft"
RM_DIR="$RUN_ROOT/reward_model"
PPO_DIR="$RUN_ROOT/ppo"

if [[ "$TRACK" == "M" ]]; then
  source_arm="R-${MODEL}-${DATASET}-s${SEED_VALUE}"
  source_sft=""
  while IFS= read -r candidate; do
    attempt_dir="$(dirname "$candidate")"
    if [[ -d "$attempt_dir/sft/final" ]]; then
      source_sft="$attempt_dir/sft/final"
    fi
  done < <(
    find "$RUNS_ROOT/$source_arm" -mindepth 2 -maxdepth 2 \
      -name run.complete.json -type f 2>/dev/null | sort
  )
  if [[ -z "$source_sft" ]]; then
    echo "Track M requires a completed Track R SFT arm: $source_arm" >&2
    exit 2
  fi
  SFT_FINAL="$source_sft"
else
  SFT_FINAL="$SFT_DIR/final"
  "$PYTHON_BIN" "$UPSTREAM/scripts/train_sft.py" \
    --model_name "$MODEL_NAME" \
    --dataset_path "$DATA/sft_train.json" \
    --eval_dataset_path "$DATA/sft_eval.json" \
    --output_dir "$SFT_DIR" \
    --num_epochs 5 \
    --batch_size 8 \
    --gradient_accumulation_steps 4 \
    --learning_rate 2e-5 \
    --warmup_ratio 0.06 \
    --max_seq_length 512 \
    --lora_r "$LORA_R" \
    --lora_alpha "$((LORA_R * 2))" \
    --neftune_noise_alpha 5.0 \
    --save_steps 500 \
    --logging_steps 50 \
    --report_to none \
    --seed "$SEED_VALUE" \
    2>&1 | tee "$LOG_ROOT/sft.log"
fi

reward_flags=()
ppo_flags=()
if [[ "$TRACK" == "M" ]]; then
  reward_flags+=(--merge_sft_before_reward)
  ppo_flags+=(--reward_dtype float32 --reset_optimizer_on_rollback)
fi

"$PYTHON_BIN" "$UPSTREAM/scripts/train_reward.py" \
  --base_model "$SFT_FINAL" \
  "${reward_flags[@]}" \
  --dataset_path "$DATA/preference_train.json" \
  --eval_dataset_path "$DATA/preference_eval.json" \
  --output_dir "$RM_DIR" \
  --num_epochs 2 \
  --batch_size 8 \
  --gradient_accumulation_steps 2 \
  --learning_rate 1e-5 \
  --warmup_ratio 0.1 \
  --max_seq_length 512 \
  --lora_r "$LORA_R" \
  --lora_alpha "$((LORA_R * 2))" \
  --save_steps 200 \
  --logging_steps 20 \
  --report_to none \
  --seed "$SEED_VALUE" \
  2>&1 | tee "$LOG_ROOT/reward.log"

"$PYTHON_BIN" "$UPSTREAM/scripts/train_ppo.py" \
  --policy_model "$SFT_FINAL" \
  --reward_model "$RM_DIR/final" \
  "${ppo_flags[@]}" \
  --dataset_path "$DATA/sft_train.json" \
  --output_dir "$PPO_DIR" \
  --num_steps 250 \
  --batch_size 32 \
  --mini_batch_size 4 \
  --num_ppo_epochs 2 \
  --learning_rate 5e-6 \
  --kl_penalty 0.2 \
  --target_kl 6.0 \
  --clip_range 0.2 \
  --gamma 1.0 \
  --gae_lambda 0.95 \
  --max_new_tokens 96 \
  --temperature 0.9 \
  --top_p 0.95 \
  --lora_r "$LORA_R" \
  --save_steps 1000 \
  --logging_steps 25 \
  --seed "$SEED_VALUE" \
  2>&1 | tee "$LOG_ROOT/ppo.log"

for stage in sft ppo; do
  if [[ "$stage" == "sft" ]]; then
    model_path="$SFT_FINAL"
  else
    model_path="$PPO_DIR/final"
  fi
  "$PYTHON_BIN" "$UPSTREAM/scripts/evaluate.py" \
    --model_path "$model_path" \
    --eval_dataset "$DATA/sft_eval.json" \
    --reward_model_path "$RM_DIR/final" \
    --output_dir "$RUN_ROOT/eval_$stage" \
    --max_samples 200 \
    --max_new_tokens 128 \
    --temperature 0.8 \
    --batch_size 16 \
    2>&1 | tee "$LOG_ROOT/eval_$stage.log"
done

paired_args=(
  --run-root "$RUN_ROOT"
  --sft-path "$SFT_FINAL"
  --ppo-path "$PPO_DIR/final"
  --reward-path "$RM_DIR/final"
  --reward-dtype "$REWARD_DTYPE"
  --eval-data "$DATA/sft_eval.json"
  --output "$RUN_ROOT/paired_eval.json"
  --batch-size 16
)
"$PYTHON_BIN" "$WORKSPACE/paper_repro/paired_eval.py" \
  "${paired_args[@]}" \
  2>&1 | tee "$LOG_ROOT/paired_eval.log"

echo "completed $ARM_ID at $RUN_ROOT"

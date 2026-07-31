#!/usr/bin/env bash
set -euo pipefail

MODEL_KEY="${1:?usage: run_corrected_reward_init.sh MODEL_KEY GPU_SELECTOR EXPECTED_GPU}"
GPU_SELECTOR="${2:?pass a CUDA device index or GPU UUID}"
EXPECTED_GPU="${3:?pass a substring of the expected GPU name}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="$ROOT/SLM-RL-Agents"
DATA="$ROOT/data_release/datasets/tinystories"
COMPAT="$ROOT/compat"
SEED="${SEED:-42}"
EXACT_OUTPUTS="${EXACT_OUTPUTS_ROOT:-$ROOT/outputs}"
CORRECTED_OUTPUTS="${CORRECTED_OUTPUTS_ROOT:-$ROOT/outputs_corrected}"
EXACT_ROOT="$EXACT_OUTPUTS/$MODEL_KEY/tinystories"
RUN_ROOT="$CORRECTED_OUTPUTS/$MODEL_KEY/tinystories"
LOGS="${CORRECTED_LOGS_ROOT:-$ROOT/logs_corrected}"
RM_DIR="$RUN_ROOT/reward_model"
PPO_DIR="$RUN_ROOT/ppo"
PYTHON_BIN="${PYTHON_BIN:-python3}"

case "$MODEL_KEY" in
  pythia-70m)
    LORA_R=8
    ;;
  pythia-160m)
    LORA_R=16
    ;;
  pythia-410m)
    LORA_R=32
    ;;
  *)
    echo "unsupported model key: $MODEL_KEY" >&2
    exit 2
    ;;
esac

mkdir -p "$LOGS" "$RUN_ROOT"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_SELECTOR"
export PYTHONPATH="$COMPAT:$UPSTREAM${PYTHONPATH:+:$PYTHONPATH}"
export TOKENIZERS_PARALLELISM=false
export WANDB_MODE=disabled
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

actual_gpu="$("$PYTHON_BIN" -c 'import torch; print(torch.cuda.get_device_name(0))')"
if [[ "$actual_gpu" != *"$EXPECTED_GPU"* ]]; then
  echo "GPU identity check failed: expected '$EXPECTED_GPU', got '$actual_gpu'" >&2
  exit 2
fi
if [[ ! -d "$EXACT_ROOT/sft/final" ]]; then
  echo "exact-run SFT checkpoint is missing: $EXACT_ROOT/sft/final" >&2
  exit 2
fi

echo "Corrected reward-init follow-up on $actual_gpu"
echo "model=$MODEL_KEY seed=$SEED changes=merge-SFT-before-reward,float32-PPO-reward,reset-optimizer-on-rollback"

if [[ ! -d "$RM_DIR/final" ]]; then
  "$PYTHON_BIN" "$UPSTREAM/scripts/train_reward.py" \
    --base_model "$EXACT_ROOT/sft/final" \
    --merge_sft_before_reward \
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
    --seed "$SEED" \
    2>&1 | tee "$LOGS/${MODEL_KEY}_tinystories_reward.log"
fi

if [[ ! -d "$PPO_DIR/final" ]]; then
  "$PYTHON_BIN" "$UPSTREAM/scripts/train_ppo.py" \
    --policy_model "$EXACT_ROOT/sft/final" \
    --reward_model "$RM_DIR/final" \
    --reward_dtype float32 \
    --reset_optimizer_on_rollback \
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
    --seed "$SEED" \
    2>&1 | tee "$LOGS/${MODEL_KEY}_tinystories_ppo.log"
fi

for stage in sft ppo; do
  if [[ "$stage" == "sft" ]]; then
    model_path="$EXACT_ROOT/sft/final"
  else
    model_path="$PPO_DIR/final"
  fi
  if [[ ! -f "$RUN_ROOT/eval_${stage}/evaluation_results.json" ]]; then
    "$PYTHON_BIN" "$UPSTREAM/scripts/evaluate.py" \
      --model_path "$model_path" \
      --eval_dataset "$DATA/sft_eval.json" \
      --reward_model_path "$RM_DIR/final" \
      --output_dir "$RUN_ROOT/eval_${stage}" \
      --max_samples 200 \
      --max_new_tokens 128 \
      --temperature 0.8 \
      --batch_size 16 \
      2>&1 | tee "$LOGS/${MODEL_KEY}_tinystories_eval_${stage}.log"
  fi
done

if [[ ! -f "$RUN_ROOT/paired_eval.json" ]]; then
  "$PYTHON_BIN" "$ROOT/paired_eval.py" \
    --run-root "$RUN_ROOT" \
    --sft-path "$EXACT_ROOT/sft/final" \
    --ppo-path "$PPO_DIR/final" \
    --reward-path "$RM_DIR/final" \
    --reward-dtype float32 \
    --eval-data "$DATA/sft_eval.json" \
    --output "$RUN_ROOT/paired_eval.json" \
    --batch-size 16 \
    2>&1 | tee "$LOGS/${MODEL_KEY}_tinystories_paired_eval.log"
fi

echo "DONE corrected $MODEL_KEY"

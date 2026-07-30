#!/usr/bin/env bash
set -euo pipefail

MODEL_KEY="${1:?usage: run_tinystories_repro.sh MODEL_KEY GPU_SELECTOR EXPECTED_GPU}"
GPU_SELECTOR="${2:?pass a CUDA device index or GPU UUID}"
EXPECTED_GPU="${3:?pass a substring of the expected GPU name}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="$ROOT/SLM-RL-Agents"
DATA="$ROOT/data_release/datasets/tinystories"
COMPAT="$ROOT/compat"
OUTPUTS="$ROOT/outputs"
LOGS="$ROOT/logs"
PYTHON_BIN="${PYTHON_BIN:-/home/orwel/dev_genius/venv/bin/python}"
SEED="${SEED:-42}"
OUTPUTS="${OUTPUTS_ROOT:-$OUTPUTS}"
LOGS="${LOGS_ROOT:-$LOGS}"

case "$MODEL_KEY" in
  pythia-70m)
    MODEL_NAME="EleutherAI/pythia-70m-deduped"
    LORA_R=8
    ;;
  pythia-160m)
    MODEL_NAME="EleutherAI/pythia-160m-deduped"
    LORA_R=16
    ;;
  pythia-410m)
    MODEL_NAME="EleutherAI/pythia-410m-deduped"
    LORA_R=32
    ;;
  *)
    echo "unsupported model key: $MODEL_KEY" >&2
    exit 2
    ;;
esac

RUN_ROOT="$OUTPUTS/$MODEL_KEY/tinystories"
SFT_DIR="$RUN_ROOT/sft"
RM_DIR="$RUN_ROOT/reward_model"
PPO_DIR="$RUN_ROOT/ppo"

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

if [[ ! -f "$DATA/sft_train.json" || ! -f "$DATA/preference_train.json" ]]; then
  echo "released TinyStories files are missing under $DATA" >&2
  exit 2
fi

echo "Reproducing arXiv:2607.25091 on $actual_gpu"
echo "model=$MODEL_KEY data=released-tinystories protocol=5ep-SFT/2ep-RM/250step-PPO seed=$SEED"

if [[ ! -d "$SFT_DIR/final" ]]; then
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
    --seed "$SEED" \
    2>&1 | tee "$LOGS/${MODEL_KEY}_tinystories_sft.log"
fi

if [[ ! -d "$RM_DIR/final" ]]; then
  "$PYTHON_BIN" "$UPSTREAM/scripts/train_reward.py" \
    --base_model "$SFT_DIR/final" \
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
    --policy_model "$SFT_DIR/final" \
    --reward_model "$RM_DIR/final" \
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
  eval_dir="$RUN_ROOT/eval_$stage"
  model_dir="$RUN_ROOT/$stage/final"
  if [[ ! -f "$eval_dir/evaluation_results.json" ]]; then
    "$PYTHON_BIN" "$UPSTREAM/scripts/evaluate.py" \
      --model_path "$model_dir" \
      --eval_dataset "$DATA/sft_eval.json" \
      --reward_model_path "$RM_DIR/final" \
      --output_dir "$eval_dir" \
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
    --eval-data "$DATA/sft_eval.json" \
    --output "$RUN_ROOT/paired_eval.json" \
    --batch-size 16 \
    2>&1 | tee "$LOGS/${MODEL_KEY}_tinystories_paired_eval.log"
fi

echo "DONE $MODEL_KEY"

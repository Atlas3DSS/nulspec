# Release patches required for reproduction

The upstream source is pinned at commit `64acb621037c711395f2d77516bee70d8a49b819`.

1. `scripts/train_sft.py` and `scripts/train_reward.py`: map
   `--report_to none` to `[]`, not `None`. In Transformers 4.45.2, `None`
   enables all installed integrations and caused the unattended run to stop for
   a Weights & Biases API key before the first optimization step.
2. `scripts/verify_results.py`: the upstream file places
   `from __future__ import annotations` after two module string literals, which
   is a syntax error under Python 3.12. The verifier is not used to generate our
   independent metrics; this defect is retained in the pinned source and noted
   in the report.
3. `scripts/train_ppo.py`: add line-buffered per-step telemetry because an
   existing Transformers logging handler suppresses the release script's
   `INFO` progress records. No training operation is changed.

An attempted reward-forward batching optimization was rejected after an
8-example audit found that GPT-NeoX bfloat16 reward logits changed by as much as
1.12 solely with batch shape. The final run retains the release's one-example
reward forwards, and `validate_reward_batching.py` plus its JSON output preserve
this negative engineering result.

No optimization logic or hyperparameters were changed.

## Paper-faithful follow-up (not part of the exact-code run)

Three opt-in flags implement operations described by the paper but absent from
the default release path:

- `train_reward.py --merge_sft_before_reward` merges the SFT adapter before
  attaching a fresh reward LoRA, preventing `default`-adapter overwrite.
- `train_ppo.py --reward_dtype float32` uses the precision specified for the
  reward model in the paper's PPO numerical-stability section. The unchanged
  default remains the release's bfloat16.
- `train_ppo.py --reset_optimizer_on_rollback` clears optimizer state after
  restoring weights, matching Algorithm 1's explicit "reset optimizer moments"
  step. The release default retains optimizer state.

`run_corrected_reward_init.sh` enables all three flags and stores all results
separately under `outputs_corrected/`.

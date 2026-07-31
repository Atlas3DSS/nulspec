# Reproduction protocol

## Target

- Paper: *Towards Robust Reinforcement Learning for Small-Scale Language
  Model Agents* (arXiv:2607.25091, submitted 2026-07-27)
- Upstream repository:
  <https://github.com/rezwanh001/SLM-RL-Agents>
- Pinned commit: `64acb621037c711395f2d77516bee70d8a49b819`
- Released dataset: `rezwanh001/SLM-RL-Agent-Research-Data`, TinyStories
  config, exact downloaded JSON files

The paper's capacity-headroom claim predicts a negative/near-zero result for
Pythia-70M on TinyStories (released SFT PPL 51.41, reward delta -0.0754) and a
positive result for Pythia-410M (PPL 6.50, delta +1.3549). These two endpoints
are the overnight test.

## Exact training protocol

Both runs use seed 42 and the release's stated protocol:

- SFT: 5 epochs, batch 8, accumulation 4, LR 2e-5, LoRA rank 8/32, NEFTune 5
- Reward model: 2 epochs, batch 8, accumulation 2, LR 1e-5, LoRA rank 8/32
- PPO: 250 steps, batch 32, minibatch 4, 2 epochs, LR 5e-6, initial KL 0.2,
  target KL 6.0, clip 0.2, gamma 1.0, lambda 0.95, 96 generated tokens
- Released evaluation: 200 examples, 128 sampled tokens, temperature 0.8
- Independent evaluation: the same 200 prompts, paired greedy 96-token
  continuations, paired t interval/test, 10,000-replicate paired bootstrap,
  empirical paired wins/sign test, and diversity

The paper and `run_ppo_only.sh` state 250 PPO steps. The repository's
`run_optimal.sh` still says 500. This run follows the paper.

## Hardware and isolation

- Pythia-70M: workstation RTX 4090, 24 GiB
- Pythia-410M: shared-host RTX PRO 6000 Blackwell Workstation Edition, 96 GiB
- Unrelated services: never signalled, stopped, reconfigured, or placed in an
  experimental cgroup
- Shared-host experiment: exact PRO 6000 UUID, 12 GiB memory high/16 GiB hard
  process limit, 800% CPU quota, nice 10, low-priority I/O
- Workstation experiment: 24 GiB memory high/32 GiB hard process limit, 1200%
  CPU quota, nice 10, low-priority I/O

## Release defects and audit decisions

See `RELEASE_PATCHES.md` for the two compatibility patches and the telemetry-only
PPO patch. No optimizer, training operation, dataset, model, seed, or
hyperparameter is changed.

An attempted bfloat16 reward batching optimization was rejected. On eight
released 410M examples, changing only the forward batch shape changed individual
reward logits by as much as 1.1172. The final PPO and paired evaluation therefore
retain one-example reward forwards. The audit outputs are in `artifacts/`.

A second implementation mismatch was found in the release reward trainer. It
loads the SFT adapter as `default`, then `RewardTrainer` calls
`get_peft_model(..., adapter_name="default")` again. With PEFT 0.18.1 this
reinitializes the adapter (`B` changes from nonzero to exactly zero), contrary to
the paper's "init from π_SFT backbone" description. The exact released-code run
is retained as the primary reproduction. A controlled follow-up in
`outputs_corrected/` corrects this operation by merging the SFT adapter into the
backbone before attaching the reward-model LoRA.

The paper also states that all PPO tensors, explicitly including the reward
model, use float32. The release PPO script instead hard-codes bfloat16 reward
inference. The paper-faithful follow-up uses float32 reward inference; the exact
released-code run retains bfloat16.

Finally, Algorithm 1 says a rollback resets optimizer moments. The release
restores trainable weights only, retaining potentially corrupted Adam state.
The paper-faithful follow-up clears optimizer state after each rollback. The
defined `StableLogitsProcessor` is also never passed to generation; this dead
code is documented but not enabled because it is not part of the paper's stated
three-layer mechanism.

The release evaluation has three interpretation caveats:

1. Its perplexity is measured on prompt plus reference text, with prompt tokens
   included in the loss. It is not generated-continuation perplexity.
2. Its reported analytic "win rate" uses marginal reward means/variances and a
   normal approximation, not empirical same-prompt wins.
3. Sampled generation is not seeded in `evaluate.py`, and the release does not
   preserve the complete per-example reward vectors needed to independently
   reconstruct its confidence intervals.

The independent paired evaluation addresses points 2 and 3 without replacing
the release-protocol metrics used for direct comparison.

## Run

```bash
# Workstation
systemd-run --user --scope \
  -p MemoryHigh=24G -p MemoryMax=32G -p CPUQuota=1200% \
  nice -n 10 ionice -c 2 -n 7 \
  bash paper_repro/run_tinystories_repro.sh pythia-70m 0 "RTX 4090"

# Shared lab host
systemd-run --user --scope \
  -p MemoryHigh=12G -p MemoryMax=16G -p CPUQuota=800% \
  nice -n 10 ionice -c 2 -n 7 \
  bash paper_repro/run_tinystories_repro.sh \
    pythia-410m GPU-d739b9c5-bfbb-e95a-bbf1-7122f38c2cf1 "RTX PRO 6000"
```

The runner is resumable by completed stage. After copying the remote 410M
output into the local `outputs/` tree:

```bash
python3 paper_repro/analyze_results.py
```

The controlled follow-up is also resumable:

```bash
bash paper_repro/run_corrected_reward_init.sh pythia-70m 0 "RTX 4090"
bash paper_repro/run_corrected_reward_init.sh \
  pythia-410m GPU-d739b9c5-bfbb-e95a-bbf1-7122f38c2cf1 "RTX PRO 6000"
```

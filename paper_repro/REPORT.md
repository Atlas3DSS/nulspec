# Overnight replication report

## Bottom line

This is a partial confirmation of the paper's capacity-headroom pattern and a
disconfirmation of its stronger release/reproducibility claims.

- The high-perplexity Pythia-70M arm showed no statistically detectable PPO
  gain, matching the paper's qualitative prediction.
- The exact release code did **not** converge stably for 70M: after 45 finite
  updates, an infinite importance ratio corrupted LoRA weights; five consecutive
  rollbacks re-corrupted and the run stopped after 50 attempted steps, not 250.
- The exact 410M release-style metric strongly reproduced the paper (+1.140
  reward here versus +1.355 published), but its seeded same-prompt estimate was
  inconclusive and slightly negative: -0.128 [-0.759, +0.480].
- The paper-faithful 410M control also produced no paired gain (-0.014
  [-0.503, +0.476], p=0.956), despite completing 250 updates cleanly apart
  from one isolated KL warning.
- The paper method and released implementation differ in several consequential
  places. A separate paper-faithful follow-up corrects those mismatches rather
  than silently folding them into the primary reproduction.

## Target and test

The target is [*Towards Robust Reinforcement Learning for Small-Scale Language
Model Agents*](https://arxiv.org/abs/2607.25091) (arXiv:2607.25091, submitted
2026-07-27). Its [released code and result
table](https://github.com/rezwanh001/SLM-RL-Agents) cover 15 model/corpus
configurations and argue that useful PPO gain requires both a fluent SFT prior
(PPL < 20) and a discriminative reward model.

The overnight test reruns the paper's two TinyStories endpoints using the exact
released data and stated 5-epoch SFT / 2-epoch reward / 250-step PPO protocol:

| Arm | Hardware | Paper SFT PPL | Paper Δreward | Prediction |
|---|---|---:|---:|---|
| Pythia-70M | workstation RTX 4090 | 51.41 | -0.075 | null/negative |
| Pythia-410M | dev-box RTX PRO 6000 | 6.50 | +1.355 | positive |

## Results

### Exact released-code rerun

| Model | Finite / attempted PPO updates | Release-style Δreward | Paired Δreward (95% bootstrap CI) | Empirical paired win rate |
|---|---:|---:|---:|---:|
| Pythia-70M | 45 / 50, rollback stop | +0.067 | +0.047 [-0.110, +0.208] | 50.5% |
| Pythia-410M | 250 / 250 | +1.140 | -0.128 [-0.759, +0.480] | 53.8% |

The 70M paired t-test gives p=0.562; the paired sign test gives p=0.912.
Distinct-1/2 are essentially unchanged. The release-style stochastic evaluation
changes sign relative to the paper (+0.067 here versus -0.075 in the table), but
both are small; the seeded paired interval rules out neither a modest negative
nor modest positive effect.

For 410M, the release-style stochastic evaluation agrees closely with the
published positive result. Its paired t-test instead gives p=0.683, and the
paired sign test gives p=0.321. The positive release-style result therefore
reproduces, but the stricter paired protocol does not establish that PPO
improves reward on the same held-out prompts.

### Paper-faithful follow-up

| Model | Finite / attempted PPO updates | Release-style Δreward | Paired Δreward (95% bootstrap CI) | Empirical paired win rate |
|---|---:|---:|---:|---:|
| Pythia-70M | 249 / 250, recovered rollback | +0.944 | -0.084 [-0.501, +0.334] | 46.2% |
| Pythia-410M | 250 / 250 | -0.546 | -0.014 [-0.503, +0.476] | 48.5% |

This follow-up changes only operations explicitly described in the paper but
missing from the release path:

1. Merge the SFT adapter before attaching the reward-model LoRA.
2. Use float32 reward inference during PPO.
3. Reset optimizer moments after a weight rollback.

The 70M follow-up demonstrates that the third change matters operationally. It
encountered one corruption at attempted update 192, reset optimizer state, and
continued to the end. However, this was not healthy optimization: 226/249
finite updates had negative KL and the trainer emitted 146 ratio-threshold
warnings. Its paired t-test remains null (p=0.691).

The 410M follow-up was far more numerically stable: 250/250 finite updates,
zero ratio warnings, one negative-KL warning, and no rollback. Nevertheless,
its paired t-test is null (p=0.956; sign-test p=0.724). Its stochastic
release-style score is negative while the exact-code run's is strongly
positive, further exposing how sensitive the released marginal evaluation is
to reward-model construction and sampled generations.

## Release audit

1. **Reward initialization is overwritten.** `train_reward.py` loads the SFT
   adapter as `default`, then `RewardTrainer` attaches a new `default` adapter.
   In PEFT 0.18.1 the SFT LoRA B norm changes from 0.02327 to exactly zero.
2. **PPO reward precision disagrees with the paper.** The paper says all PPO
   tensors—including the reward model—are float32; release code loads reward
   inference in bfloat16.
3. **Rollback is incomplete.** The paper algorithm says to reset optimizer
   moments; release code restores weights only. This was observed directly:
   after the first 70M corruption, all five retained-state retries corrupted.
4. **A claimed logits guard is dead code.** `StableLogitsProcessor` is defined
   and comments say it clamps rollouts, but it is never passed to generation.
5. **Perplexity is mislabeled.** The paper says generated-continuation PPL; the
   evaluator scores prompt plus held-out reference text, including prompt loss.
6. **"Win rate" is not paired.** The release reports a marginal normal
   approximation from two means/variances, not empirical wins on same-prompt
   pairs.
7. **Released evaluation is not fully reconstructable.** Sampling is unseeded,
   only 50/200 generations are saved, and full per-example reward vectors are
   absent.
8. **Mechanical release defects.** `--report_to none` turns on every installed
   integration rather than none; `verify_results.py` has an invalid
   `from __future__` placement; paper/README say 250 PPO steps while
   `run_optimal.sh` says 500.

## Numerical audit

An attempted reward-scoring speedup was rejected rather than allowed to alter
the experiment. On eight 410M examples, changing only bfloat16 forward batch
shape moved an individual reward by up to 1.1172. In float32 the worst change
was 0.000734. Final PPO and paired metrics therefore keep one-example reward
forwards.

## Interpretation of all 15 released rows

Every released Δreward > +0.2 occurs below PPL 20 (5/8 below versus 0/7 above;
exploratory one-sided Fisher exact p=0.0186). But PPL < 20 is not sufficient:
three of eight below-threshold rows fail to exceed +0.2, including
Pythia-410M/CNN (-0.259). The paper's additional "informative reward" condition
is therefore necessary to rescue the rule, but the release does not provide a
separate pre-PPO quantitative threshold for that condition.

## Reproducibility

- Exact source commit, hashes, package versions, and GPU identities:
  `MANIFEST.json`
- Complete protocol and commands: `PROTOCOL.md`
- Compatibility and opt-in method patches: `RELEASE_PATCHES.md`
- Raw checkpoints/evaluations: `outputs/` and `outputs_corrected/`
- Raw training logs: `logs/` and `logs_corrected/`
- Independent paired evaluator: `paired_eval.py`
- Machine-readable aggregate and plots: `artifacts/`

All training jobs used GPU identity checks plus CPU, process-memory, nice, and
I/O limits. The live Palworld server was never signalled or reconfigured.

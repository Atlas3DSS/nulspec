# Frozen reproduction protocol: arXiv:2607.25091

**Protocol version:** 1.0.0

**Status:** frozen for confirmatory compute

**Target:** *Towards Robust Reinforcement Learning for Small-Scale Language
Model Agents*

**Paper:** <https://arxiv.org/abs/2607.25091>

**Upstream code commit:** `64acb621037c711395f2d77516bee70d8a49b819`

**Released data repository:** `mr3haque/SLM-RL-Agents-Data`

**Released data commit:** `2cee50d2989aadebfd5af529937c99f7d539287a`

**Released model repository:** `mr3haque/SLM-RL-Agents`

**Released model commit:** `1c74b58663ae3a97117abe60661c72915a6150ed`

No confirmatory full-matrix run may begin until this protocol passes validation,
is committed, and is tagged `2607.25091-protocol-v1.0.0`.

## 1. Research objective

Determine whether the released artifacts and locally rerun experiments support
the paper's reported numerical results and its capacity-headroom conclusion
across all five models and all three corpora.

This objective has four ordered parts:

1. verify the released artifacts without retraining;
2. rerun the complete released-code recipe;
3. rerun the complete written-method recipe where it differs;
4. freeze those results before beginning extensions.

Failure to execute a run is reportable evidence. It is not silently replaced by
a repaired run.

## 2. Matrix

The matrix contains 15 configurations:

- Models: Pythia-70M, Pythia-160M, Pythia-410M, SmolLM2-135M, SmolLM2-360M.
- Corpora: TinyStories, CNN/DailyMail, Wikitext-103.
- Initial seed: 42.

Each configuration is executed under two separately reported tracks, yielding
30 initial arms. `matrix.csv` is the frozen arm registry.

## 3. Source hierarchy and conflicting recipes

The release does not define one internally consistent executable recipe.

| Source | PPO settings or behavior |
|---|---|
| Paper Section IV-C | 250 steps, minibatch 4, LR 5e-6, KL 0.2, target 6 |
| README main-results note | 250 steps and float32 throughout |
| `scripts/run_ppo_only.sh` | 250 steps, minibatch 4, LR 5e-6, KL 0.2 |
| `scripts/run_optimal.sh` | 500 steps with the otherwise final settings |
| `scripts/run_all_experiments.sh` | 500 steps, minibatch 8, LR 1e-5, KL 0.1 |
| `scripts/run_full_pipeline.sh` | 1,000 steps, minibatch 8, LR 1e-5, KL 0.1 |
| README usage examples | 3 SFT epochs, 1 reward epoch, 500 PPO steps, and argument names that do not match the released CLIs |

All listed files first appear in the repository's single public commit, so Git
history cannot identify a later authoritative launcher.

The primary released-code interpretation uses the paper, main-results note, and
purpose-built `run_ppo_only.sh` settings. The 500-step `run_optimal.sh` variant
is a preregistered sensitivity run for any headline or discrepant configuration,
not an undocumented replacement for the primary recipe.

## 4. Track R — released-code, 250-step recipe

This track uses the released training implementation with defaults unchanged,
apart from non-semantic compatibility and telemetry patches.

### SFT

- exact released split;
- 5 epochs;
- per-device batch 8, gradient accumulation 4;
- AdamW, peak LR 2e-5;
- 6% warmup and cosine decay;
- maximum sequence length 512;
- NEFTune alpha 5;
- LoRA rank 8/16/32 by model and alpha `2r`;
- bfloat16/4-bit behavior from the released script;
- seed 42.

### Reward model

- exact released preference split;
- 2 epochs;
- per-device batch 8, gradient accumulation 2;
- AdamW, LR 1e-5, warmup ratio 0.1;
- maximum sequence length 512;
- LoRA rank and alpha as above;
- released adapter-loading behavior;
- seed 42.

### PPO

- 250 attempted steps;
- rollout batch 32, minibatch 4, two PPO epochs;
- LR 5e-6;
- initial KL coefficient 0.2, target KL 6.0;
- PPO clip 0.2, gamma 1.0, GAE lambda 0.95;
- 96 generated tokens, temperature 0.9, top-p 0.95;
- released reward-inference dtype and rollback behavior;
- seed 42.

The only allowed patches in Track R are:

- map `--report_to none` to an empty integration list;
- add line-buffered progress telemetry;
- compatibility shims required to import the pinned dependency stack.

Any other patch creates a new track.

## 5. Track M — manuscript-method recipe

Track M uses the same data, seed, models, and hyperparameters as Track R, but
enables operations stated in the manuscript and absent or contradicted in the
released execution path:

1. initialize the reward-model transformer from the trained SFT distribution
   without overwriting the SFT adapter;
2. use float32 reward inference inside PPO;
3. clear optimizer moments after restoring a rollback snapshot.

Track M reuses the matching Track R SFT checkpoint. This isolates reward/PPO
implementation differences and avoids treating stochastic SFT variation as a
method correction.

Track M is not described as “the original code.” Track R is not described as
“the written method.”

## 6. Artifact verification

Before training:

- verify upstream Git commit and patch digest;
- verify all 12 released data files by SHA-256 and row count;
- verify the released results JSON against the paper table;
- inventory every released SFT and PPO checkpoint;
- inspect available `training_args.bin` metadata;
- record missing reward checkpoints and any metadata that prevents exact
  reconstruction;
- execute static CLI checks against every documented command.

The stale dataset namespace in the paper-era protocol
(`rezwanh001/SLM-RL-Agent-Research-Data`) resolves neither anonymously nor for
the configured Hub account. The public data were located under
`mr3haque/SLM-RL-Agents-Data`; its TinyStories files exactly match the four
previously downloaded files. This namespace change is provenance, not a data
substitution.

## 7. Evaluation

### 7.1 Release-protocol evaluation

For direct comparison with the published table:

- first 200 held-out examples;
- sampled generation, maximum 128 new tokens, temperature 0.8;
- released reward model and evaluator;
- preserve all 200 prompts, generations, and per-example scores;
- record the evaluator's unseeded sampling behavior.

This output is reported using the release's field names even where an audit
finds those names misleading.

### 7.2 Independent paired evaluation

Without replacing Section 7.1:

- the same 200 prompts for SFT and PPO;
- deterministic greedy 96-token continuations;
- one-example reward forwards unless a dtype/batch equivalence test passes;
- paired mean difference and 95% bootstrap interval;
- paired permutation or t test, sign test, and empirical paired win rate;
- Distinct-1/2 and exact response identity rate;
- Holm-adjusted p-values across the 15 configurations.

All exclusions are fixed before model identity is unblinded in aggregate
analysis. Ties remain ties.

### 7.3 Reproduction assessment

Every configuration receives separate judgments:

- **execution:** completed, failed, or completed with recovery;
- **numerical:** published point estimate inside/outside the rerun uncertainty
  interval and absolute discrepancy;
- **directional:** sign agrees, disagrees, or is practically indistinguishable
  from zero;
- **claim-level:** whether the complete matrix supports the stated
  capacity-headroom pattern.

No single arbitrary tolerance determines the overall conclusion.
`scripts/analyze_2607_25091_matrix.py` implements this frozen consolidation:
it uses prompt-aligned release-evaluator scores, a deterministic 10,000-sample
bootstrap, absolute discrepancy, interval inclusion, directional assessment,
and a 15-test Holm family within each track. Missing interim arms enter the
Holm family with p=1; claim-level interpretation remains locked until all 15
arms in that track complete.

## 8. Existing pilot evidence

Runs completed before this protocol are retained under `paper_repro/outputs*`
and `extension/matrix_runs`. They may validate the runner and estimate resource
requirements, but the full matrix registry begins pending. Pilot observations
must not alter Track R or Track M settings.

## 9. Extensions embargo

The following are extensions and cannot modify primary reproduction outcomes:

- Qwen-27B pairwise judging;
- Codex or Fable outer-teacher review;
- readiness gates and alternative reward diagnostics;
- additional seeds;
- alternative PPO budgets, objectives, models, or datasets;
- cross-hardware performance comparisons.

Extension protocols are written and versioned after the 30 primary arms are
frozen. Exploration may be implemented earlier, but it remains clearly labeled
and does not determine primary exclusions.

## 10. Hardware and workload safety

Available accelerators:

- workstation: RTX 4090 24 GB;
- shared lab host: RTX 3090 24 GB;
- shared lab host: RTX PRO 6000 Blackwell 96 GB.

The original paper used two RTX A6000 48 GB GPUs. Hardware differences are
reported per arm.

Until a new measured capacity audit supports a concurrency change:

- only one experimental GPU workload may run on a shared host at a time;
- unrelated services are never stopped, signalled, reconfigured, or included
  in an experimental cgroup;
- every job uses a fixed GPU UUID, `MemoryHigh`, `MemoryMax`, `CPUQuota`, nice,
  and I/O priority;
- the runner refuses to start below the recorded free-memory threshold;
- resource pressure terminates the experiment, not the host.

Current hardware and memory are recaptured before concurrency limits change.
Prospective hardware is never written into a completed run manifest.

## 11. Environment strategy

The paper README recommends Python 3.10, PyTorch 2.5.1+cu121, Transformers
4.45.2, TRL 0.9.6, and PEFT 0.18.1. Track R first attempts that environment on
the RTX 3090/4090, whose architectures are supported by that stack.

The Blackwell GPU requires a newer CUDA/PyTorch stack and is therefore a
declared compatibility environment, not a bit-identical software reproduction.
Environment construction failures are preserved and reported.

Each run captures:

- Git and upstream revisions plus dirty-state flags;
- command and protocol version;
- host, CPU, RAM, kernel, GPUs, driver, and CUDA;
- Python executable and complete package lock;
- data/model hashes;
- timestamps, exit status, warnings, and recovery events.

## 12. Amendments and stopping

This protocol is immutable after tagging. Necessary changes create an amendment
file and a new tag. An arm stops on:

- the released trainer's own terminal condition;
- non-finite weights that cannot be recovered under its track;
- resource-safety guard activation;
- operator interruption recorded in the run manifest.

Runs are not extended merely because their result is null or unfavorable.

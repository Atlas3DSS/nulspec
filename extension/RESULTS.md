# Three-gate extension: initial results

## Bottom line

The extension disconfirms the paper's proposed readiness rule at seed 42.
Perplexity below 20 and excellent held-out reward discrimination did not
identify a policy that improved under PPO. Pythia-160M crossed the claimed
perplexity boundary but both PPO variants were numerically invalid and
independently null. Pythia-410M passed the strict numerical gate; exact PPO was
independently null and the paper-faithful policy was preferred only 40.5% of
the time. The latter within-arm interval excludes chance, although its
unadjusted p-value does not survive a conservative six-arm Bonferroni
correction.

The mechanism is reward transfer failure. On corrected 410M pairs where Qwen
consistently preferred SFT, the training reward nevertheless preferred PPO
56.6% of the time; its median PPO-minus-SFT reward was +0.637. Static
chosen/rejected accuracy therefore does not establish that a reward model is
valid on policy-generated outputs.

## Independent Qwen-27B endpoint

Each of 200 response pairs per arm was judged in both A/B orders. Only pairs
whose two decisions mapped to the same outcome enter the effect estimate.
Qwen first passed a held-out control: 49/50 released chosen responses were
preferred, with 50/50 order-consistent pairs and exactly balanced raw A/B
choices.

| Arm | Consistent / total | PPO / SFT / tie | PPO preference (95% bootstrap CI) | Sign p |
|---|---:|---:|---:|---:|
| exact 70M | 181 / 200 | 4 / 2 / 175 | 0.506 [0.492, 0.519] | 0.6875 |
| corrected 70M | 181 / 200 | 7 / 4 / 170 | 0.508 [0.489, 0.528] | 0.5488 |
| exact 160M | 186 / 200 | 1 / 5 / 180 | 0.489 [0.476, 0.500] | 0.2188 |
| corrected 160M | 161 / 200 | 9 / 4 / 148 | 0.516 [0.494, 0.537] | 0.2668 |
| exact 410M | 148 / 200 | 61 / 60 / 27 | 0.503 [0.432, 0.578] | 1.0000 |
| corrected 410M | 147 / 200 | 55 / 83 / 9 | 0.405 [0.330, 0.483] | 0.0212 |

Eight reviewer records used a symmetric, recorded 256-character fallback
because mojibake continuations exceeded Qwen's per-slot context. All other
records used the full continuation.

## Readiness and numerical integrity

All six reward models separate the released held-out preferences well. That
metric is not predictive here.

| Arm | SFT PPL | Reward accuracy | Mean chosen margin | Max BF16 batch-shape error |
|---|---:|---:|---:|---:|
| exact 70M | 53.66 | 0.964 | 3.56 | 1.562 |
| corrected 70M | 53.66 | 0.900 | 7.95 | 3.375 |
| exact 160M | 12.94 | 0.964 | 5.28 | 0.875 |
| corrected 160M | 12.94 | 0.980 | 7.50 | 1.469 |
| exact 410M | 6.46 | 0.984 | 10.50 | 1.391 |
| corrected 410M | 6.46 | 0.988 | 11.15 | 1.170 |

FP32 batch-shape errors were at most 0.003 in every arm. BF16 errors reached
0.875–3.375, validating the decision to keep reward scoring single-example
FP32 in the corrected protocol.

| Arm | Healthy / attempted PPO updates | Rollbacks | Ratio warnings | Negative-KL warnings | Strict integrity |
|---|---:|---:|---:|---:|---:|
| exact 70M | 45 / 50 | 5 | 24 | 43 | fail |
| corrected 70M | 249 / 250 | 1 | 146 | 178 | fail |
| exact 160M | 4 / 9 | 5 | 8 | 1 | fail |
| corrected 160M | 80 / 85 | 5 | 80 | 57 | fail |
| exact 410M | 250 / 250 | 0 | 0 | 0 | pass |
| corrected 410M | 250 / 250 | 0 | 0 | 1 | pass |

Resetting optimizer moments was useful but insufficient: it extended 160M from
4 healthy updates to 80 before the fifth-corruption stop. The exact 160M run
still produced a positive internal paired reward delta (+0.353, p=0.009)
despite completing only four healthy updates; corrected 160M was null
(-0.211, p=0.215). Internal reward improvement is therefore not evidence of a
valid training trajectory.

## Outer-teacher audit

Codex was invoked once through the existing ChatGPT-authenticated CLI, with API
key variables removed, an empty working directory, ignored user/project
configuration, an ephemeral session, and a read-only sandbox. Its packet
contained only Qwen records and population counts—no prompts, small-model
outputs, checkpoints, rewards, or training state. Fable was not called.

The outer teacher rated Qwen's review process **fail**, reliability **0.32**.
Across non-calibration records Qwen chose raw A 514 times versus raw B 325,
and 14–53 of 200 pairs per arm were order-inconsistent. This validates the
two-order filter and means Qwen should not be treated as an oracle. The audit
cannot establish semantic correctness because the underlying candidates were
intentionally outside its boundary. Outer-teacher findings remain separate
from training and from the primary effect estimates.

## What the paper should test next

The useful extension is now three readiness gates—language headroom,
**on-policy reward transfer**, and numerical integrity—followed by independent
evaluation with a reviewer audit. Offline reward accuracy is only a calibration
check.
Before expensive PPO, the reward model should also agree with an independent
judge on SFT-generated and controlled-degradation pairs. After PPO, reward
direction should be checked against blinded same-prompt preferences.

The implemented 18-arm matrix adds seeds 123 and 777 for confirmatory
uncertainty estimates. Six seed-42 arms are complete; the remaining 12 are
defined and resumable but are not included in this initial result. Until those
replicates are run, the corrected-410M harm signal and all between-capacity
comparisons should be treated as strong exploratory evidence, not a final
population estimate.

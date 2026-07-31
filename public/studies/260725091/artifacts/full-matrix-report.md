# arXiv:2607.25091 matrix status

This file is generated from `full_matrix_analysis.json`. It reports the frozen release-style comparison, the independent paired endpoint, training integrity, and execution provenance without altering any run artifact.

The frozen scientific base protocol is v1.0.0. Completed execution manifest versions are `1.0.0`: 9, `1.6.0`: 6, `1.7.0`: 6, `1.8.0`: 3, `1.9.0`: 6. Version 1.9.0 incorporates the nine retained operational protocol amendments; the frozen model-by-corpus matrix and scientific settings are unchanged.

## Reporting clarification: uncertainty scope

The release's 95% interval over 200 held-out prompts is a useful measure of prompt-level uncertainty for the sampled outputs in that evaluation. Its label does not, however, make explicit that it is conditional on one training seed and one unseeded sampled continuation per model and prompt. It therefore should not be read as training-to-training or decoding-to-decoding replication uncertainty. We report this as a limitation of scope, not as an invalidation of the released calculation. Separately, the released analytic interval treats the two marginal score distributions as independent; our same-prompt analysis is reported alongside it rather than rewriting the published value.

Our update leaves the published value and release-style point estimate unchanged. For the rerun, we retain the 200 underlying generations and reward differences and label our prompt-bootstrap interval as conditional. We also report a seeded, deterministic same-prompt endpoint as a separate diagnostic. Neither endpoint substitutes for independent training and decoding reruns, which would be required to estimate full run-to-run variability.

## Variance budget

| Variance source | Status | Interpretation |
|---|---|---|
| Held-out prompt composition | Estimated conditionally | The 10,000-replicate paired bootstrap resamples the 200 retained prompt-level reward differences, conditional on fixed checkpoints and retained generations. |
| Training seed | Not estimated | Every configuration has one independent training seed (`42`) per track; training-to-training variance and seed-by-method interaction are unknown. |
| Sampled decoding | Not estimated | Release evaluation retains one unseeded draw per checkpoint and prompt. The deterministic paired endpoint removes decoding noise from that diagnostic but does not measure decoding variance. |
| SFT contribution to R versus M | Controlled, not estimated | Track M reuses Track R's SFT checkpoint, preventing fresh SFT variation from entering the track contrast; SFT seed variance remains unknown. |
| Reward-model and PPO training | Single realization | A track difference describes these frozen runs, not an expected effect over fresh reward/PPO trainings. |
| Hardware and software stack | Sensitivity only | Per-arm provenance and exact-stack reevaluation probe disclosed stack effects; they do not estimate a hardware population variance. |
| Model/corpus heterogeneity | Described, not sampled | The 15 arms are fixed conditions, not 15 independent replicates of one method effect. Their spread is not used as a standard error. |
| Failures and recoveries | Documented, not replicated | Recovery attempts share verified checkpoints with source attempts and are not counted as independent runs. |

Accordingly, Track R-versus-M differences will be described as **single-seed method contrasts**. We will not use words such as “generally,” “reliably,” or “always” unless supported by additional independent training seeds. Estimating full run-to-run variance requires both multi-seed retraining and repeated sampled decoding.

## Track R

- Claim-ready arms: 15/15
- Terminal executions: 10 completed and 5 completed with recovery
- Prescribed PPO target reached: 11/15
- Published delta inside rerun 95% interval: 12/15
- Claim status: `ready_for_interpretation`

### Arm-level effects

| Arm | Execution | Evaluation | Paper Δ | Release rerun Δ [conditional 95% prompt CI] | Match | Independent paired Δ [conditional 95% prompt CI] | Holm p | Direction |
|---|---|---|---:|---:|:---:|---:|---:|---|
| R-pythia-70m-tinystories-s42 | completed | native_attempt | -0.0754 | +0.0571 [-0.1872, +0.3045] | yes | -0.0129 [-0.1283, +0.0995] | 1 | inconclusive_interval_includes_zero |
| R-pythia-70m-cnn_dailymail-s42 | completed | native_attempt | -0.1874 | +0.0788 [-0.1511, +0.3116] | no | -0.0594 [-0.1970, +0.0837] | 1 | inconclusive_interval_includes_zero |
| R-pythia-70m-wikitext-s42 | completed | native_attempt | -0.0618 | -0.1026 [-0.3301, +0.1348] | yes | +0.0387 [-0.0902, +0.1740] | 1 | inconclusive_interval_includes_zero |
| R-pythia-160m-tinystories-s42 | completed | native_attempt | +0.2377 | -0.0477 [-0.6025, +0.4992] | yes | +0.1379 [-0.0207, +0.2992] | 1 | inconclusive_interval_includes_zero |
| R-pythia-160m-cnn_dailymail-s42 | completed | native_attempt | -0.1976 | -0.0822 [-0.2649, +0.0992] | yes | -0.0089 [-0.1234, +0.1059] | 1 | inconclusive_interval_includes_zero |
| R-pythia-160m-wikitext-s42 | completed | native_attempt | +0.0435 | -0.1920 [-0.6555, +0.2695] | yes | -0.1374 [-0.3689, +0.0872] | 1 | inconclusive_interval_includes_zero |
| R-pythia-410m-tinystories-s42 | completed | native_attempt | +1.3549 | +1.4715 [+0.7398, +2.2281] | yes | +0.7814 [+0.1246, +1.4271] | 0.2565 | agrees |
| R-pythia-410m-cnn_dailymail-s42 | completed | native_attempt | -0.2586 | -0.5445 [-0.8633, -0.2379] | yes | -0.2052 [-0.4924, +0.0884] | 1 | agrees |
| R-pythia-410m-wikitext-s42 | completed | native_attempt | -1.0429 | -0.9716 [-1.4751, -0.4611] | yes | -0.6229 [-1.1901, -0.0492] | 0.4076 | agrees |
| R-smollm2-135m-tinystories-s42 | completed_with_recovery | native_attempt | +0.2255 | +0.3138 [-0.1171, +0.7437] | yes | +0.1385 [-0.2061, +0.4889] | 1 | inconclusive_interval_includes_zero |
| R-smollm2-135m-cnn_dailymail-s42 | completed_with_recovery | native_attempt | -0.1937 | -0.0328 [-0.3554, +0.2823] | yes | +0.1027 [-0.1932, +0.4049] | 1 | inconclusive_interval_includes_zero |
| R-smollm2-135m-wikitext-s42 | completed | native_attempt | +0.0151 | -0.0423 [-0.2696, +0.1773] | yes | -0.1285 [-0.3198, +0.0627] | 1 | inconclusive_interval_includes_zero |
| R-smollm2-360m-tinystories-s42 | completed_with_recovery | exact_stack_reevaluation | +0.7236 | +0.2579 [-0.1099, +0.6378] | no | +0.3962 [+0.0817, +0.7083] | 0.1987 | inconclusive_interval_includes_zero |
| R-smollm2-360m-cnn_dailymail-s42 | completed_with_recovery | exact_stack_reevaluation | -0.0008 | +0.3203 [+0.1287, +0.5104] | no | +0.1448 [-0.0525, +0.3349] | 1 | disagrees |
| R-smollm2-360m-wikitext-s42 | completed_with_recovery | exact_stack_reevaluation | +0.2721 | +0.3979 [+0.1950, +0.6038] | yes | +0.6190 [+0.4359, +0.8054] | 0.00015 | agrees |

### PPO training integrity

| Arm | Recorded steps | Target reached | Corruptions | Ratio warnings | Negative-KL warnings | Negative-KL steps |
|---|---:|:---:|---:|---:|---:|---:|
| R-pythia-70m-tinystories-s42 | 35/250 | no | 5 | 20 | 34 | 33/35 (94.3%) |
| R-pythia-70m-cnn_dailymail-s42 | 250/250 | yes | 0 | 61 | 39 | 189/250 (75.6%) |
| R-pythia-70m-wikitext-s42 | 250/250 | yes | 0 | 55 | 60 | 163/250 (65.2%) |
| R-pythia-160m-tinystories-s42 | 6/250 | no | 5 | 11 | 6 | 4/6 (66.7%) |
| R-pythia-160m-cnn_dailymail-s42 | 19/250 | no | 5 | 13 | 10 | 10/19 (52.6%) |
| R-pythia-160m-wikitext-s42 | 6/250 | no | 5 | 16 | 8 | 4/6 (66.7%) |
| R-pythia-410m-tinystories-s42 | 250/250 | yes | 0 | 0 | 0 | 28/250 (11.2%) |
| R-pythia-410m-cnn_dailymail-s42 | 250/250 | yes | 0 | 1 | 38 | 249/250 (99.6%) |
| R-pythia-410m-wikitext-s42 | 250/250 | yes | 0 | 0 | 19 | 245/250 (98.0%) |
| R-smollm2-135m-tinystories-s42 | 250/250 | yes | 0 | 0 | 31 | 213/250 (85.2%) |
| R-smollm2-135m-cnn_dailymail-s42 | 250/250 | yes | 0 | 0 | 67 | 242/250 (96.8%) |
| R-smollm2-135m-wikitext-s42 | 250/250 | yes | 0 | 0 | 58 | 235/250 (94.0%) |
| R-smollm2-360m-tinystories-s42 | 250/250 | yes | 0 | 0 | 0 | 39/250 (15.6%) |
| R-smollm2-360m-cnn_dailymail-s42 | 250/250 | yes | 0 | 0 | 12 | 196/250 (78.4%) |
| R-smollm2-360m-wikitext-s42 | 250/250 | yes | 0 | 0 | 3 | 215/250 (86.0%) |

### Capacity-headroom necessary-condition check

The released paper defines a fluent prior as release-style SFT PPL < 20 and identifies reward deltas > +0.2 as the material positive-gain cases. This reproduces that stated necessary-condition check; it is not a new fitted threshold.

- Status: `complete` (15/15 arms).
- Release-protocol material-positive arms: `R-pythia-410m-tinystories-s42`, `R-smollm2-135m-tinystories-s42`, `R-smollm2-360m-tinystories-s42`, `R-smollm2-360m-cnn_dailymail-s42`, `R-smollm2-360m-wikitext-s42`.
- Release-protocol material-positive arms with SFT PPL ≥ 20: none.
- Independent paired material-positive arms with SFT PPL ≥ 20: none.
- Full joint hypothesis testable from the release: **no**. The release does not give a preregistered threshold or retained claim-level measurement for an 'informative' or 'discriminative' reward signal, so only the paper's stated fluency necessary condition can be checked directly.

## Track M

- Claim-ready arms: 15/15
- Terminal executions: 15 completed and 0 completed with recovery
- Prescribed PPO target reached: 12/15
- Published delta inside rerun 95% interval: 5/15
- Claim status: `ready_for_interpretation`

### Arm-level effects

| Arm | Execution | Evaluation | Paper Δ | Release rerun Δ [conditional 95% prompt CI] | Match | Independent paired Δ [conditional 95% prompt CI] | Holm p | Direction |
|---|---|---|---:|---:|:---:|---:|---:|---|
| M-pythia-70m-tinystories-s42 | completed | native_attempt | -0.0754 | +0.1968 [-0.4734, +0.8717] | yes | -0.0741 [-0.4240, +0.2634] | 1 | inconclusive_interval_includes_zero |
| M-pythia-70m-cnn_dailymail-s42 | completed | native_attempt | -0.1874 | +0.1405 [-0.1036, +0.3994] | no | +0.0486 [-0.1167, +0.2115] | 1 | inconclusive_interval_includes_zero |
| M-pythia-70m-wikitext-s42 | completed | native_attempt | -0.0618 | +0.2714 [-0.0259, +0.5656] | no | -0.0792 [-0.3036, +0.1301] | 1 | inconclusive_interval_includes_zero |
| M-pythia-160m-tinystories-s42 | completed | native_attempt | +0.2377 | -0.1149 [-0.6334, +0.4042] | yes | +0.1862 [-0.1845, +0.5445] | 1 | inconclusive_interval_includes_zero |
| M-pythia-160m-cnn_dailymail-s42 | completed | native_attempt | -0.1976 | +0.1572 [-0.0706, +0.3854] | no | +0.1645 [-0.0141, +0.3393] | 0.5528 | inconclusive_interval_includes_zero |
| M-pythia-160m-wikitext-s42 | completed | native_attempt | +0.0435 | +0.0032 [-0.2653, +0.2738] | yes | +0.0661 [-0.0965, +0.2230] | 1 | inconclusive_interval_includes_zero |
| M-pythia-410m-tinystories-s42 | completed | exact_stack_reevaluation | +1.3549 | -0.2119 [-0.8537, +0.4294] | no | +0.6340 [+0.0484, +1.2224] | 0.2826 | inconclusive_interval_includes_zero |
| M-pythia-410m-cnn_dailymail-s42 | completed | native_attempt | -0.2586 | +0.0538 [-0.4590, +0.5522] | yes | +1.3832 [+0.7382, +2.0224] | 0.0002 | inconclusive_interval_includes_zero |
| M-pythia-410m-wikitext-s42 | completed | exact_stack_reevaluation | -1.0429 | +1.6959 [+1.0325, +2.3337] | no | +1.7139 [+1.1029, +2.3391] | 0.00015 | disagrees |
| M-smollm2-135m-tinystories-s42 | completed | native_attempt | +0.2255 | +2.2563 [+1.9795, +2.5336] | no | +1.9947 [+1.6794, +2.3003] | 0.00015 | agrees |
| M-smollm2-135m-cnn_dailymail-s42 | completed | native_attempt | -0.1937 | +0.2020 [-0.0804, +0.4749] | no | +0.1171 [-0.1237, +0.3585] | 1 | inconclusive_interval_includes_zero |
| M-smollm2-135m-wikitext-s42 | completed | native_attempt | +0.0151 | +0.4184 [+0.2013, +0.6319] | no | +0.7661 [+0.5293, +1.0090] | 0.00015 | agrees |
| M-smollm2-360m-tinystories-s42 | completed | exact_stack_reevaluation | +0.7236 | +0.2992 [-0.0621, +0.6600] | no | +0.9358 [+0.5433, +1.3115] | 0.00015 | inconclusive_interval_includes_zero |
| M-smollm2-360m-cnn_dailymail-s42 | completed | exact_stack_reevaluation | -0.0008 | +0.1204 [-0.0074, +0.2521] | yes | +0.0907 [-0.0254, +0.2087] | 0.8975 | inconclusive_interval_includes_zero |
| M-smollm2-360m-wikitext-s42 | completed | exact_stack_reevaluation | +0.2721 | +0.5556 [+0.3170, +0.7953] | no | +1.2678 [+0.9956, +1.5328] | 0.00015 | agrees |

### PPO training integrity

| Arm | Recorded steps | Target reached | Corruptions | Ratio warnings | Negative-KL warnings | Negative-KL steps |
|---|---:|:---:|---:|---:|---:|---:|
| M-pythia-70m-tinystories-s42 | 250/250 | yes | 1 | 99 | 146 | 213/249 (85.5%) |
| M-pythia-70m-cnn_dailymail-s42 | 250/250 | yes | 0 | 45 | 33 | 181/250 (72.4%) |
| M-pythia-70m-wikitext-s42 | 250/250 | yes | 0 | 49 | 51 | 140/250 (56.0%) |
| M-pythia-160m-tinystories-s42 | 53/250 | no | 5 | 59 | 38 | 46/49 (93.9%) |
| M-pythia-160m-cnn_dailymail-s42 | 62/250 | no | 5 | 48 | 19 | 44/58 (75.9%) |
| M-pythia-160m-wikitext-s42 | 90/250 | no | 5 | 134 | 75 | 79/86 (91.9%) |
| M-pythia-410m-tinystories-s42 | 250/250 | yes | 0 | 19 | 2 | 48/250 (19.2%) |
| M-pythia-410m-cnn_dailymail-s42 | 250/250 | yes | 0 | 0 | 0 | 2/250 (0.8%) |
| M-pythia-410m-wikitext-s42 | 250/250 | yes | 0 | 0 | 0 | 0/250 (0.0%) |
| M-smollm2-135m-tinystories-s42 | 250/250 | yes | 0 | 0 | 0 | 18/250 (7.2%) |
| M-smollm2-135m-cnn_dailymail-s42 | 250/250 | yes | 0 | 0 | 10 | 174/250 (69.6%) |
| M-smollm2-135m-wikitext-s42 | 250/250 | yes | 0 | 0 | 3 | 192/250 (76.8%) |
| M-smollm2-360m-tinystories-s42 | 250/250 | yes | 0 | 0 | 34 | 228/250 (91.2%) |
| M-smollm2-360m-cnn_dailymail-s42 | 250/250 | yes | 0 | 0 | 0 | 145/250 (58.0%) |
| M-smollm2-360m-wikitext-s42 | 250/250 | yes | 0 | 0 | 22 | 248/250 (99.2%) |

### Capacity-headroom necessary-condition check

The released paper defines a fluent prior as release-style SFT PPL < 20 and identifies reward deltas > +0.2 as the material positive-gain cases. This reproduces that stated necessary-condition check; it is not a new fitted threshold.

- Status: `complete` (15/15 arms).
- Release-protocol material-positive arms: `M-pythia-70m-wikitext-s42`, `M-pythia-410m-wikitext-s42`, `M-smollm2-135m-tinystories-s42`, `M-smollm2-135m-cnn_dailymail-s42`, `M-smollm2-135m-wikitext-s42`, `M-smollm2-360m-tinystories-s42`, `M-smollm2-360m-wikitext-s42`.
- Release-protocol material-positive arms with SFT PPL ≥ 20: `M-pythia-70m-wikitext-s42`, `M-pythia-410m-wikitext-s42`, `M-smollm2-135m-wikitext-s42`.
- Independent paired material-positive arms with SFT PPL ≥ 20: `M-pythia-410m-wikitext-s42`, `M-smollm2-135m-wikitext-s42`.
- Full joint hypothesis testable from the release: **no**. The release does not give a preregistered threshold or retained claim-level measurement for an 'informative' or 'discriminative' reward signal, so only the paper's stated fluency necessary condition can be checked directly.

## Track M versus Track R: fixed-configuration contrasts

Each row is a fixed-configuration, single-seed Track M minus Track R description. The tracks train different reward models, so internal reward-delta shifts are calibration-confounded and are not common-scale output-quality effects. No pooled effect or across-configuration standard error is reported. Track M bundles SFT-initialized reward training, float32 PPO reward inference, and optimizer-state reset on rollback; this design tests the manuscript-method bundle and cannot attribute an observed change to one component without a separate ablation. Raw warning counts are retained per arm, while the contrast uses warnings per recorded PPO step and negative-KL step fractions so runs with different stopping times are not compared as though they had equal exposure.

Output-quality method claims require the separately retained blinded Qwen comparison and outer-teacher audit.

- Status: `complete` (15/15 claim-ready configuration pairs).

| Configuration | Internal sampled Δ shift M−R | Internal deterministic Δ shift M−R | PPO steps M−R | Corruptions M−R | Ratio warnings/record R→M | Negative-KL warnings/record R→M | Negative-KL step share R→M |
|---|---:|---:|---:|---:|---:|---:|---:|
| pythia-70m / tinystories / seed 42 | +0.1397 | -0.0612 | +215 | -4 | 0.571→0.398 | 0.971→0.586 | 0.943→0.855 |
| pythia-70m / cnn_dailymail / seed 42 | +0.0616 | +0.1079 | +0 | +0 | 0.244→0.180 | 0.156→0.132 | 0.756→0.724 |
| pythia-70m / wikitext / seed 42 | +0.3740 | -0.1179 | +0 | +0 | 0.220→0.196 | 0.240→0.204 | 0.652→0.560 |
| pythia-160m / tinystories / seed 42 | -0.0672 | +0.0483 | +47 | +0 | 1.833→1.204 | 1.000→0.776 | 0.667→0.939 |
| pythia-160m / cnn_dailymail / seed 42 | +0.2394 | +0.1734 | +43 | +0 | 0.684→0.828 | 0.526→0.328 | 0.526→0.759 |
| pythia-160m / wikitext / seed 42 | +0.1952 | +0.2035 | +84 | +0 | 2.667→1.558 | 1.333→0.872 | 0.667→0.919 |
| pythia-410m / tinystories / seed 42 | -1.6834 | -0.1474 | +0 | +0 | 0.000→0.076 | 0.000→0.008 | 0.112→0.192 |
| pythia-410m / cnn_dailymail / seed 42 | +0.5984 | +1.5885 | +0 | +0 | 0.004→0.000 | 0.152→0.000 | 0.996→0.008 |
| pythia-410m / wikitext / seed 42 | +2.6675 | +2.3368 | +0 | +0 | 0.000→0.000 | 0.076→0.000 | 0.980→0.000 |
| smollm2-135m / tinystories / seed 42 | +1.9425 | +1.8562 | +0 | +0 | 0.000→0.000 | 0.124→0.000 | 0.852→0.072 |
| smollm2-135m / cnn_dailymail / seed 42 | +0.2348 | +0.0144 | +0 | +0 | 0.000→0.000 | 0.268→0.040 | 0.968→0.696 |
| smollm2-135m / wikitext / seed 42 | +0.4607 | +0.8946 | +0 | +0 | 0.000→0.000 | 0.232→0.012 | 0.940→0.768 |
| smollm2-360m / tinystories / seed 42 | +0.0413 | +0.5396 | +0 | +0 | 0.000→0.000 | 0.000→0.136 | 0.156→0.912 |
| smollm2-360m / cnn_dailymail / seed 42 | -0.1999 | -0.0540 | +0 | +0 | 0.000→0.000 | 0.048→0.000 | 0.784→0.580 |
| smollm2-360m / wikitext / seed 42 | +0.1578 | +0.6488 | +0 | +0 | 0.000→0.000 | 0.012→0.088 | 0.860→0.992 |

## Blackwell exact-stack sensitivity

Blackwell-native evaluations are preserved descriptively. Claim-level values come from the exact paper stack on Ampere or Ada hardware. The sampled release shift is confounded by fresh unseeded generations; the deterministic paired shift is the cleaner stack-sensitivity diagnostic.

| Arm | Exact-stack status | Native→exact sampled release shift | Native→exact deterministic paired shift |
|---|---|---:|---:|
| R-smollm2-360m-tinystories-s42 | completed | +0.1275 | +0.0021 |
| R-smollm2-360m-cnn_dailymail-s42 | completed | +0.1992 | +0.0022 |
| R-smollm2-360m-wikitext-s42 | completed | -0.0534 | -0.0003 |
| M-pythia-410m-tinystories-s42 | completed | -0.6830 | +0.0000 |
| M-pythia-410m-wikitext-s42 | completed | +0.3240 | -0.0064 |
| M-smollm2-360m-tinystories-s42 | completed | +0.3398 | -0.0000 |
| M-smollm2-360m-cnn_dailymail-s42 | completed | +0.0665 | -0.0000 |
| M-smollm2-360m-wikitext-s42 | completed | +0.0110 | -0.0000 |

## Execution and artifact provenance limitations

- The immutable Track R set contains 46 run or exact-stack manifests whose package inventory is empty because our original capture helper assumed `pip` existed in the uv environment. Those manifests remain unchanged; exact dependency locks, environment probes, and artifact hashes provide the replacement evidence. Future manifests use the repaired capture helper.
- Base-model Hub commits were identified retrospectively from the sole cached snapshots on both hosts rather than captured at launch. The five audited revisions matched the canonical default-branch heads at audit time, but the timing limitation remains explicit.
- The final SmolLM2-135M TinyStories and Wikitext workstation arms overlapped on one RTX 4090 under the prospectively recorded D012 scheduling decision. Their immutable manifests identify the GPU and service units but omitted the promised explicit concurrency field; terminal log hashes preserve the overlap evidence.
- The first local artifact consolidation omitted three complete Pythia checkpoint trees that remained intact on the dev box. Before this freeze, missing files were restored without overwriting existing artifacts and whole-attempt tree hashes, file counts, and byte counts matched on both hosts.
- Five failed source attempts remain retained. Recovery attempts reuse only hash-verified terminal phase outputs; partial PPO state is never treated as resumable or as an independent replicate.

## Fixed analysis rules

- Release intervals use a deterministic 10,000-replicate prompt-paired bootstrap over the 200 retained reward differences. They are conditional on one retained stochastic generation per model and prompt and do not estimate training- or decoding-rerun variability.
- Independent inference uses deterministic same-prompt continuations and a 100,000-replicate sign-flip test.
- An interval that includes zero is labeled directionally inconclusive. It is not described as equivalence or evidence that the effect is practically zero.
- Sign-flip p-values are Holm-adjusted within each frozen 15-arm track; unavailable arms enter an interim family as `p = 1`.
- A terminal released trainer can still fail the prescribed 250-step budget; execution and training integrity are reported separately.
- Failed attempts, recovery lineage, sampled native Blackwell metrics, nulls, and numerical warnings remain in the record.

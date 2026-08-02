# SPRKD malaria replication — one-page result

**Paper:** Dewan, Yogeswaran, and Fedoruk (2026), [*SPRKD: Effective
Knowledge Distillation for Deep Neural Networks via Saddle Region
Approximation*](https://arxiv.org/abs/2607.23346v1).
**Target:** the fully tabulated malaria experiment at the paper-linked code
revision.
**Outcome:** **Not replicated** as a public five-seed final result; the
underlying method remains **inconclusive**, not disproved.

## The claim

The paper reports that a 6,430-parameter SPRKD student trained from weak
two-epoch teachers reaches 94.80% validation accuracy over five trials. That
reportedly matches a scratch student (94.47%) and a strong teacher (94.50%),
while exceeding response knowledge distillation (RKD, 70.10%) by 24.70 points.
The authors attribute the result to saddle-region information and report the
curvature ordering SPRKD < Control-S < RKD.

## What we did

We froze seeds 0–4 and reran all five 500-epoch malaria trials on the complete
27,558-image public dataset. We kept three evidence layers separate:

1. replay of the authors' released checkpoints, histories, and Hessian files;
2. the exact current public reproduction path at the paper's epoch/trial count;
3. a narrow paper-intent reconstruction that starts SPRKD randomly and keeps
   RKD's weak teacher unmodified, resolving two direct prose/code conflicts.

Every final value is sample-weighted over 6,890 validation images. We publish
all five seeds, sample SDs, descriptive 95% t intervals across independent
training runs, paired predictions, exact McNemar tables, code/input/output
hashes, and an origin-separated error ledger. Extensions and post-hoc
diagnostics are labeled and cannot change the frozen result.

## Result

| Model/path | Five-seed final mean | SD | Paper |
|---|---:|---:|---:|
| Exact public SPRKD | 85.74% | 20.01 | 94.80% |
| Paper-intent SPRKD | 67.98% | 24.63 | 94.80% |
| Scratch Control-S | 86.42% | 20.08 | 94.47% |
| Exact public RKD | 50.00% | 0.32 | 70.10% |
| Paper-intent RKD | 71.51% | 1.36 | 70.10% |
| Strong Control-T | 95.24% | 0.13 | 94.50% |

Paper-intent SPRKD finished near chance in three of five seeds and averaged
3.53 points *below* weak-teacher RKD, reversing the headline comparison. The
exact script finished near chance in one seed; its RKD baseline stayed at 50%
because that path distills from a teacher already overwritten by the ASR.
Control-S also collapsed in one seed, while the larger Control-T was stable.

The important distinction is between reproducing an executable artifact and
confirming the proposed mechanism. Every SPRKD seed reached at least 92.61% in
its retained batch-mean history, and the exact-path mean of the five best such
epochs was 94.83%—almost the paper's 94.80%. Several runs then fell by more than
40 points before epoch 500. Because the release does not say whether Table 1
used best checkpoints,
excluded failed finals, or came from materially different historical code, we
can reject reproduction of the public final-result recipe without claiming the
method itself cannot work.

## What matched—and what did not

- **Matched:** strong-teacher performance was stable; the unmodified weak
  teacher and paper-intent RKD remained near 70%; all five SPRKD runs were
  capable of reaching above 92% in their retained batch-mean histories.
- **Did not match:** stable final 94.80% SPRKD, the 24.70-point paper-intent
  advantage over RKD, parity/equivalence with controls, and the released
  Hessian numbers/order as a complete set.
- **Artifacts disagree internally:** supplied checkpoints score 84/80/74% on
  the common 100-image set; separate historical traces end at 94.54% SPRKD and
  95.40% Control-S; released Hessian traces are 54.96/35.48/209.47 rather than
  33.39/71.33/408.27.

## What we learned

The main result is checkpoint- and loss-contract-sensitive. Conventional-logit
RKD remained near 71.67%, so RKD's double-Softmax behavior does not explain the
headline gap. Selecting the lowest-recorded-loss saddle raised SPRKD's mean to
86.10% and rescued two seeds, but one of five still collapsed.

The strongest post-hoc diagnostic changed only the student's terminal
`Softmax` to `Identity`, giving `CrossEntropyLoss` the logits its API expects.
All five SPRKD runs then finished between 94.62% and 95.11%: mean 94.792%, SD
0.193, almost exactly the paper's 94.80%. The paired scratch control averaged
95.152%, however, and SPRKD trailed it by 0.360 points on average. No corrected
SPRKD run recorded a negative-Hessian eigenstep. This makes the loss mismatch a
plausible explanation for instability and a valuable author-intent lead, not
prospective confirmation of the proposed mechanism.

Finally, a fully specified common-probe Hessian check reproduced the complete
SPRKD < Control-S < RKD ordering in only 1/5 exact-path and 2/5 paper-intent
seeds. Together, the diagnostics explain how a stable result near 94.80% is
obtainable while leaving the method-specific causal claim unresolved.

## Limits and next move

This is a targeted replication of Experiment 1, not the paper's preliminary
MNIST, CIFAR-100, or TinyImageNet observations. The exact historical
environment, per-trial records, checkpoint-selection rule, and Table 1 model
states are not public. The released random image split is also not
patient-grouped, so neither the paper nor this replication establishes
held-out-patient clinical generalization.

Our largest process limitation is that the protocols were timestamped and
frozen before their runs but were not committed and pushed before compute
began. Execution configs and hashes bind what ran, and the decision rule never
changed, but Git history alone cannot prove preregistration timing. Future work
requires a public protocol commit first.

The highest-value next step is author-intent reconciliation: obtain the exact
historical revision, seeds, five per-trial records, loss inputs, ASR selection,
checkpoint rule, and curvature provenance, then freeze and rerun that
configuration. A separate clean-room container rerun and a prospectively
registered larger-seed stability study would follow. Null results remain useful;
the goal is a record another lab can reproduce, inspect, and improve.

# Frozen replication protocol

**Frozen before scratch training:** 2026-07-31 (America/Los_Angeles).
Released-artifact inspection and code auditing occurred first and are explicitly
not treated as scratch-run outcomes.

## Claim under test

The primary claim is the malaria result in Table 1: after 500 epochs, SPRKD
achieves 94.80% top-1 validation accuracy, Control-S 94.47%, and response KD
70.10%, averaged across five trials. Secondary checks are the weak-teacher
ceiling, Control-T performance, the SPRKD-minus-RKD gap, and paired McNemar
comparisons.

## Scope boundary

This is a targeted replication of Experiment 1, the paper's only fully
tabulated head-to-head experiment and the experiment the upstream README calls
its full reproduction. TinyImageNet, MNIST, and CIFAR-100 are described as
preliminary qualitative or single-checkpoint supplementary findings without a
dedicated results table; the release provides loaders and architectures but no
equivalent end-to-end reproduction script, five-run records, or complete
configuration provenance for those claims. They are therefore not silently
treated as replicated here. Reconstructing them would be a separately frozen
follow-up, preferably after author clarification.

## Design

- Dataset: the repository's NLM malaria `cell_images` tree, verified as 27,558
  images and loaded with `Resize((32, 32))` plus `ToTensor()` only.
- Split: 75/25, using the released package's deterministic split implementation.
- Trials: five complete training seeds, fixed in advance as 0, 1, 2, 3, 4.
- Batch size: 64; Adam learning rate: 0.001; no augmentation.
- Weak ensemble: three 25,546-parameter teachers, two epochs each, saddle check
  every step, top four eigenvalues, released package defaults otherwise.
- Students and strong control: 500 epochs each.
- Architectures: the released `MalariaTeacherCNN` (25,546 parameters) and
  `MalariaStudentCNN` (6,430 parameters), including their terminal Softmax.
- Compute: CUDA GPUs may differ by trial. GPU model is a recorded nuisance
  variable; no mixed precision, `torch.compile`, changed batch size, or other
  throughput alteration is allowed.
- Seeds initialize Python, NumPy, CPU Torch, and all CUDA generators using the
  upstream `set_seed`. The upstream code does not request deterministic
  algorithms, so exact bitwise repeatability across GPU architectures is not
  claimed.

## Tracks

### A — released artifacts

Replay the three released student checkpoints on the supplied 100-image tensor
set, on each checkpoint's serialized validation split, and inspect the complete
historical metric traces. This verifies artifacts, not independent training.

### B — exact public reproduction path

Mirror `scripts/reproduce_malaria.py`, overriding only the paper-disclosed epoch
count from the script's demo default of 10 to 500 and adding the missing five-
seed outer loop. In particular, this track retains the script's direct ASR
initialization and its use of teacher 0 after `inject_state_list` mutates that
teacher to the ensemble ASR.

### C — narrowly corrected paper-intent diagnostic

Use the same package calls and hyperparameters, but (1) extract the injected ASR
as a target and then instantiate a fresh random SPRKD student, matching the
paper's explicit statement that the student is not initialized at the ASR, and
(2) train response KD from the saved two-epoch weak teacher, matching Table 1.
No other optimizer equation or default is changed. This is a diagnostic track,
not a claim of fully reconstructing the unavailable original run environment.

Control-S and Control-T are shared between B and C because these two corrections
do not affect them.

## Outcomes and statistics

For every model and seed, retain:

- sample-weighted final validation accuracy and cross-entropy loss;
- the upstream history's final and best unweighted batch-mean accuracy;
- predictions, targets, and validation indices;
- stage wall time, GPU identity, package versions, parameter count, and config;
- weak-teacher and ASR-mutated-teacher performance;
- saddle counts and recorded losses.

The primary aggregate is the arithmetic mean and sample standard deviation of
the five final, sample-weighted accuracies. A 95% t interval over five training
seeds is reported descriptively. We also report all seeds rather than hiding
variance. Paired comparisons use within-seed accuracy differences. McNemar tests
are run only between predictions made on the same seed's exact validation set;
they are not pooled across incompatible splits without labeling the pooling.

## Decision language

- **Replicated:** the five-seed 95% interval contains the reported value and the
  qualitative ordering/gap is reproduced without an undisclosed correction.
- **Partially replicated:** a central qualitative claim holds, but a numerical
  target, baseline, or implementation layer does not.
- **Not replicated:** the preregistered run materially contradicts the headline
  ordering or target.
- **Inconclusive:** a specification conflict, runtime failure, or fewer than
  three complete seeds prevents a defensible comparison.

No result is excluded for being unfavorable. Failed stages and local mistakes
remain in the error ledger.

# Frozen post-replication extension protocol

**Frozen before inspecting any scratch-run result:** 2026-07-31
(America/Los_Angeles). Released checkpoints and source conflicts were already
known. These diagnostics run only after a seed's preregistered replication
trial has completed and use a separate output tree.

The extensions isolate two paper/code mismatches with one change each. They do
not enter the Track A/B/C replication verdict.

## E1 — conventional logit response KD

The paper describes standard logit matching. Released malaria models terminate
in Softmax, while `train_response_kd` applies `log_softmax`/`softmax` again. E1
replaces only the terminal Softmax modules with identity functions, exposing
the unchanged final linear-layer logits to the unchanged KD trainer.

- Teacher: the saved, unmutated two-epoch `weak_teacher_0` from the same seed.
- Student: fresh initialization under the same seed.
- Objective: released pure KL objective, temperature 1.0, with no added hard-
  label term.
- Epochs, split, batch size, optimizer, learning rate, and preprocessing:
  unchanged from the frozen replication.

This tests conventional pure logit matching, not every modern KD variant.

## E2 — lowest-loss ASR with fresh student initialization

The paper says to aggregate the lowest-loss saddle from each weak teacher, but
the public end-to-end path passes snapshot-only lists to `aggregate_asr`, which
selects the last snapshot. E2 uses each checkpoint's paired `saddle_losses` to
select its minimum finite recorded loss, aggregates those three snapshots, and
extracts the student-space TLI target. A newly seeded student then approaches
that target iteratively, as the paper describes.

Everything else—including the released saddle criterion, optimizer defaults,
TLI implementation, and terminal Softmax/CrossEntropy behavior—is unchanged.
Recorded saddle losses came from different training minibatches, so “lowest”
inherits that upstream limitation and is not a common-dataset loss comparison.

## Design and reporting

- Frozen seeds: 0–4, paired to the exact same validation splits and base weak-
  teacher checkpoints.
- Outcomes: final sample-weighted validation accuracy/cross-entropy, all seed
  values, mean, sample SD, 95% t interval, paired accuracy differences, and
  exact per-seed McNemar tests against the matching preregistered baselines.
- Integrity: an extension refuses to start unless the base seed has
  `complete.json`, the recreated split exactly matches its saved indices, and
  all required teacher snapshots/losses are present.
- Interpretation: improvements, regressions, and null results are retained.
  Neither extension is described as an exact author result.

## E3 — common-probe scratch-model Hessian trace

**Frozen after scratch jobs began but before any scratch outcome was inspected:**
2026-08-01 (America/Los_Angeles). Operational progress bars and stage times had
been observed; model metrics had not. E3 is explicitly exploratory and cannot
alter the Track A/B/C verdict.

The paper's numerical Hessian setup is not fully recoverable, and its released
trace artifacts differ from Table 1. E3 therefore tests only the qualitative
ordering on our independently trained students under a fully specified common
measurement:

- Data: all 100 images in the authors' released `TESTSET.pth`, verified by the
  frozen SHA-256 digest and used as one PyHessian batch.
- Loss: cross-entropy on each saved model's released terminal-Softmax output.
- Estimator: exactly 100 Hutchinson Rademacher probes (`maxIter=100`, effective
  early-stop tolerance `-1e300`), with the same probe stream reset before every
  same-shaped student in a seed. The negative tolerance avoids PyHessian's
  signed-denominator early-stop edge case.
- Models: exact-script SPRKD and RKD, paper-intent SPRKD and RKD, plus the
  shared Control-S; all are final epoch-500 stage checkpoints.
- Outcomes: raw probe values, per-model mean/sample SD, five-seed aggregate,
  paired trace differences, and the number of seeds satisfying SPRKD <
  Control-S < RKD (plus the weaker paper claim SPRKD < each baseline).

The fixed 100-image batch is small and may overlap the training corpus; it is a
curvature probe, not a generalization estimate. Common random probes improve
paired precision but do not resolve the missing original model/data/probe
provenance or make its values numerically comparable to Table 1.

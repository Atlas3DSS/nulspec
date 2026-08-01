# SPRKD replication (arXiv:2607.23346)

Independent replication of **SPRKD: Effective Knowledge Distillation for Deep
Neural Networks via Saddle Region Approximation** (Dewan, Yogeswaran, and
Fedoruk, 2026).

Start with the [one-page result](ONE_PAGE.md), then read the
[full report](REPORT.md). The machine-readable website projection is
`WEBSITE_HANDOFF.json`; [FRONTEND_HANDOFF.md](FRONTEND_HANDOFF.md) defines its
typed classification-accuracy presentation.

The primary target is the fully tabulated malaria experiment: a 6,430-parameter
student reportedly reaches 94.80% validation accuracy after 500 epochs, versus
94.47% for a scratch student and 70.10% for response KD. The paper says these
values are means over five trials.

**Result: not replicated as a public final-epoch result; underlying method
inconclusive.** Exact-public and narrow paper-intent SPRKD averaged 85.742% and
67.977%, respectively, with chance-level finals in one and three of five seeds.
The unmodified-weak-teacher RKD reconstruction averaged 71.507%. Every SPRKD
run nevertheless reached at least 92.61% before some collapsed, so missing
historical checkpoint-selection and failed-run handling prevent a claim that
the method itself is disproved. See [ONE_PAGE.md](ONE_PAGE.md) for the compact
interpretation and [REPORT.md](REPORT.md) for the complete evidence boundary.

An explicitly post-hoc one-change diagnostic supplied logits rather than
terminal-Softmax probabilities to supervised cross-entropy. It eliminated all
five collapses and produced 94.792% SPRKD accuracy (SD 0.193), almost exactly
the paper's 94.80%; its paired scratch control averaged 95.152%. This is a
useful author-intent lead, not a replacement for the frozen primary result.

This is a targeted primary-experiment replication, not a claim to have rerun
every supplementary figure. The paper labels its TinyImageNet/MNIST/CIFAR-100
results preliminary and does not provide the same tabulated five-run evidence
or an end-to-end release script for them; the exact boundary and rationale are
frozen in [PROTOCOL.md](PROTOCOL.md).

This directory keeps three evidentiary layers separate:

1. **Released-artifact replay** checks the authors' frozen checkpoints and
   historical metric traces without retraining.
2. **Exact released-script track** runs the public package's end-to-end path at
   the paper's 500 epochs and five deterministic seeds.
3. **Paper-intent diagnostic track** changes only two observable script-level
   conflicts with the prose: it begins the SPRKD student from a fresh random
   initialization rather than directly at the ASR, and it distills the RKD
   baseline from the saved weak teacher rather than the ASR-mutated teacher.

The third layer is not silently substituted for the official implementation.
All results identify their layer. See [PROTOCOL.md](PROTOCOL.md) for the frozen
decision rules and [UPSTREAM_AUDIT.md](UPSTREAM_AUDIT.md) for specification
conflicts found before scratch training. [OPERATIONS.md](OPERATIONS.md) records
the multi-GPU execution and resume event; [TESTS.md](TESTS.md) records the
verification suite. [CITATION_AUDIT.md](CITATION_AUDIT.md) documents the
separate source-use review and outer-teacher calibration; it does not enter the
replication verdict.

The final release candidate goes through the frozen
[one-shot Fable peer-review gate](FABLE_REVIEW_PROTOCOL.md). Fable receives one
committed evidence packet and returns `PASS`, `FAIL`, or `HARD_FAIL`. `PASS`
authorizes publication. A normal `FAIL` supplies exactly three corrections;
after all three are documented and validated, publication continues without
resubmission. `HARD_FAIL` alone stops publication for human review. Fable can
only make the author-email draft eligible for a separate final human approval;
it can never authorize or send the email.

Raw source, datasets, virtual environments, checkpoints, and run logs are
ignored. Small manifests, scripts, derived tables, and the final report are
tracked.

## Frozen inputs

- arXiv source/PDF downloaded 2026-07-31
- upstream repository:
  `thetechdude124/SADDLE-POINT-RECRUITMENT-FOR-KNOWLEDGE-DISTILLATION`
- upstream commit: `7f1655ff1295c9a6dcf8d24f6410a036cd7e3497`
- public NLM malaria image tree bundled at that commit: 27,558 images

## Run

Fetch and checksum the ignored public inputs, then create an environment from
`requirements-replication.txt`:

```bash
scripts/fetch_inputs.sh
python -m venv work/.venv
work/.venv/bin/pip install --require-hashes -r requirements-artifacts.lock
```

One frozen trial is:

```bash
PYTHONPATH=work/upstream work/.venv/bin/python scripts/run_trial.py \
  --data-root work/upstream/cell_images \
  --output-root outputs/package-vs-intent \
  --seed 0 \
  --epochs 500 \
  --teacher-epochs 2 \
  --num-workers 4 \
  --progress
```

Each seed has an isolated directory and stage checkpoints. Re-running the same
command skips completed stages and recomputes only missing work.

Replay the released checkpoints and metric traces without retraining:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONPATH=work/upstream \
  work/.venv/bin/python scripts/verify_released.py \
  --upstream-root work/upstream \
  --released-root work/upstream \
  --output results/released_artifact_verification.json
```

After a base seed completes, the preregistered one-change diagnostics in
[EXTENSION_PROTOCOL.md](EXTENSION_PROTOCOL.md) can be run separately:

```bash
PYTHONPATH=work/upstream:scripts work/.venv/bin/python \
  scripts/run_extensions.py \
  --data-root work/upstream/cell_images \
  --base-output-root outputs/package-vs-intent \
  --output-root outputs/extensions \
  --seed 0 \
  --progress
```

They test conventional pure logit KD and lowest-loss-saddle ASR selection. They
are extensions, not replacements for the released-code replication.

The separately frozen common-probe Hessian diagnostic can then measure the
five final student checkpoints from that seed:

```bash
PYTHONPATH=work/upstream:scripts work/.venv/bin/python \
  scripts/run_hessian_extensions.py \
  --base-output-root outputs/package-vs-intent \
  --testset work/released/TESTSET.pth \
  --output-root outputs/hessian-extensions \
  --seed 0
```

The outcome-motivated supervised-loss diagnostic is run in its own tree:

```bash
PYTHONPATH=work/upstream:scripts work/.venv/bin/python \
  scripts/run_loss_contract_extension.py \
  --data-root work/upstream/cell_images \
  --base-output-root outputs/package-vs-intent \
  --output-root outputs/loss-contract-extensions \
  --seed 0 --progress
```

It changes only terminal `Softmax` to `Identity` so supervised
`CrossEntropyLoss` receives logits. It was specified after three completed
seeds and is not part of the preregistered verdict.

After all five seeds finish, the fail-closed analyzers validate and aggregate
the base and extension outputs:

```bash
PYTHONPATH=work/upstream:scripts work/.venv/bin/python scripts/analyze_trials.py \
  --input-root outputs/package-vs-intent --output-dir results
PYTHONPATH=work/upstream:scripts work/.venv/bin/python scripts/analyze_extensions.py \
  --base-root outputs/package-vs-intent \
  --extension-root outputs/extensions --output-dir results
PYTHONPATH=work/upstream:scripts work/.venv/bin/python \
  scripts/analyze_hessian_extensions.py \
  --base-root outputs/package-vs-intent \
  --hessian-root outputs/hessian-extensions --output-dir results
PYTHONPATH=work/upstream:scripts work/.venv/bin/python \
  scripts/analyze_training_stability.py \
  --base-root outputs/package-vs-intent --output-dir results
PYTHONPATH=work/upstream:scripts work/.venv/bin/python \
  scripts/analyze_loss_contract_extensions.py \
  --base-root outputs/package-vs-intent \
  --extension-root outputs/loss-contract-extensions --output-dir results
work/.venv/bin/python scripts/plot_primary_accuracy.py \
  --input results/scratch_summary.json \
  --output results/PRIMARY_ACCURACY_BY_SEED.png
```

The stability summary is explicitly post-hoc and descriptive. It was added
after a completed seed exposed a sharp epoch-level accuracy drop and cannot
change the preregistered replication verdict. Its outcome-motivated scope is
registered in [POSTHOC_DIAGNOSTICS.md](POSTHOC_DIAGNOSTICS.md).

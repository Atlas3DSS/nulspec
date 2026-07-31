# SLM-RL-Agents reproduction and audit

Independent, reproduction-first study of
[*Towards Robust Reinforcement Learning for Small-Scale Language Model
Agents*](https://arxiv.org/abs/2607.25091).

The project first attempts to reconstruct the paper and released GitHub
artifacts exactly enough to test every reported configuration. Corrections,
stronger evaluations, and new hypotheses are kept in separately labeled
tracks. Null results, numerical failures, and irreducible ambiguities are
preserved as results.

## Current status

- A two-configuration pilot reproduced the released-code Pythia-410M
  TinyStories reward delta but not its gain under seeded same-prompt
  evaluation.
- The pilot exposed consequential differences between the manuscript and the
  released implementation.
- All three released corpus bundles have now been located at an immutable Hub
  revision and verified; the paper-era dataset namespace is stale.
- Protocol v1.0.0 is frozen at the
  `2607.25091-protocol-v1.0.0` Git tag.
- Execution of the complete 5-model × 3-corpus × 2-track registry is active.
- Full-matrix results remain provisional until every terminal state and
  exclusion is consolidated against the frozen registry.

Start with the
[frozen protocol](protocols/2607.25091/REPRODUCTION_PROTOCOL.md) and
[research charter](docs/RESEARCH_CHARTER.md).

## Study structure

| Phase | Purpose | May change the primary result? |
|---|---|---|
| Artifact verification | Check released source, data, checkpoints, metadata, and tables | No training |
| Track R | Reproduce the final 250-step released-code path | Primary |
| Track M | Reproduce operations stated in the manuscript but absent from Track R | Separately primary |
| Extensions | External judging, outer-teacher audit, readiness gates, new seeds/methods | No |

The distinction matters because the paper, README, and repository launchers
specify incompatible PPO budgets and settings. The protocol records those
conflicts instead of silently selecting favorable values.

## Recreate the inputs

```bash
bash scripts/bootstrap_2607_25091_upstream.sh
bash scripts/fetch_2607_25091_data.sh
python3 scripts/validate_protocol.py
```

The bootstrap script checks out upstream commit
`64acb621037c711395f2d77516bee70d8a49b819` and applies a reviewable patch.
The data script fetches commit
`2cee50d2989aadebfd5af529937c99f7d539287a` and refuses to overwrite a
mismatched local file.

## Recreate the paper-stated environment

```bash
bash environments/paper/create.sh
```

The authors did not publish a complete dependency lock. The reconstructed lock,
known limitation, import checks, and CUDA smoke test are documented in
[environments/paper](environments/paper/README.md).

## Inspect and launch the matrix

```bash
python3 -m reprolab.matrixctl validate
python3 -m reprolab.matrixctl list
python3 -m reprolab.matrixctl show \
  --arm R-pythia-70m-tinystories-s42

PYTHON_BIN="$PWD/.venv-paper/bin/python" \
  bash scripts/run_guarded_2607_25091_arm.sh \
  R-pythia-70m-tinystories-s42 0 "RTX 4090"
```

The runner:

- requires a clean top-level Git revision;
- validates source and data before compute;
- selects and verifies one physical GPU;
- creates a new immutable attempt directory;
- captures start/end software and hardware manifests;
- preserves full logs and all 200 evaluation generations;
- refuses unguarded execution on shared lab hosts.

Track M refuses to start until the matching Track R arm has completed.

Run an explicit sequence of arms on one GPU:

```bash
bash scripts/run_2607_25091_queue.sh 0 "RTX 4090" \
  R-pythia-70m-tinystories-s42 \
  R-pythia-70m-wikitext-s42
```

The queue validates every arm before launch, rejects duplicate IDs, skips
already completed arms, and calls the same guarded runner serially. It stops
on the first failed arm by default. Set `CONTINUE_ON_FAILURE=1` only for a
deliberate unattended sweep; failed attempts remain immutable either way.

Run the complete source/data/environment/GPU/resource preflight without
creating an attempt directory or starting training:

```bash
PREFLIGHT_ONLY=1 \
  bash scripts/run_guarded_2607_25091_arm.sh \
  R-pythia-70m-tinystories-s42 0 "RTX 4090"
```

Consolidate current terminal states and results without modifying an attempt:

```bash
python3 scripts/analyze_2607_25091_matrix.py
```

## Existing pilot evidence

The original overnight work remains available for audit:

- [pilot report](paper_repro/REPORT.md);
- [pilot protocol](paper_repro/PROTOCOL.md);
- [release patch audit](paper_repro/RELEASE_PATCHES.md);
- [machine-readable results](paper_repro/artifacts/results_summary.json);
- [extension explainer](extension/EXPLAINER.md);
- [external-judge results](extension/RESULTS.md).

These runs are not relabeled as preregistered full-matrix results.

## Compute and workload safety

The local pool currently includes an RTX 4090, RTX 3090, and RTX PRO 6000.
Current roles and memory limits are in [docs/HARDWARE.md](docs/HARDWARE.md).

Experiments on shared hosts use GPU UUID verification, a single-job concurrency
rule, cgroup memory/CPU limits, positive nice, and low I/O priority. Unrelated
services remain outside the experimental cgroup and are never stopped,
signalled, or reconfigured by experiment tooling.

## Repository and artifacts

GitHub stores protocols, source, patches, issues, manifests, small raw records,
analysis, and reports. Downloaded datasets and multi-gigabyte checkpoints do
not enter ordinary Git history; immutable locations and SHA-256 hashes bind
them to each Git release. See [artifact policy](docs/ARTIFACT_POLICY.md).
All paper repositories also follow the
[lab repository scope and hygiene policy](docs/REPOSITORY_SCOPE_POLICY.md).

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md).

## Attribution and license

The target paper, original code, released models, and released data belong to
their respective authors and retain their original licenses. This repository's
new code and documentation are MIT licensed. Dataset redistribution is avoided;
the released dataset declares Apache-2.0.

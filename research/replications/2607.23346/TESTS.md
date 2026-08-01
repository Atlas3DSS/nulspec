# Verification log

Commands below were run against upstream commit
`7f1655ff1295c9a6dcf8d24f6410a036cd7e3497` and the replication code in this
directory.

## Upstream test suite

```bash
CUDA_VISIBLE_DEVICES='' PYTHONPATH=. python -m pytest -q
```

Result: **175 passed, 2 failed, 9 skipped in 89.54 s**.

Both failures are in `tests/test_paper.py`:

- `test_released_hessian_trace_rkd_largest`
- `test_released_sprkd_student_high_accuracy_on_testset`

In the pointer-only Git checkout, these tests use file existence as their
artifact gate and pass Git-LFS pointer text to `torch.load`, which fails with
`_pickle.UnpicklingError: invalid load key, 'v'`. The neighboring checkpoint
tests explicitly detect the same pointer format and skip with instructions to
run `git lfs pull`. Seven skips are LFS-aware artifact skips; two additional
statistics tests skip because optional `statsmodels` is absent.

This does not turn failed artifact tests into passing tests. Separately
downloaded public LFS objects were verified against their pointer SHA-256 OIDs
and successfully loaded by `verify_released.py`; that independent artifact
replay is recorded in `results/released_artifact_verification.json`.

The same verifier reads the three Table 1 Hessian artifacts. It confirms the
repository test's limited assertion that RKD has the largest released trace,
but the released artifacts do not match the three reported trace values and
reverse the paper's SPRKD-versus-Control-S ordering. This mismatch is recorded
in `UPSTREAM_AUDIT.md`; no fresh Hessian estimate is inferred from it.

## Replication-code checks

The following pass with no findings:

```bash
python -m py_compile scripts/*.py
ruff check scripts
bash -n scripts/*.sh
git diff --check -- .gitignore research/replications/2607.23346 research/ERRORS.md
```

`verify_released.py` completes CPU-only and reproduces the authors' executed
100-image contingency table exactly. `analyze_trials.py` additionally validates
every completed seed's frozen config hash, full train/validation partition,
stage set, prediction hashes, target cardinality, binary label range, and
prediction-derived accuracy before calculating an aggregate.

The released exact-McNemar helper overflowed on a real full-validation
comparison. The analysis-only replacement uses `scipy.stats.binomtest` on the
same package-generated discordant counts. Before use, its two-sided p-values
matched the released implementation for all 2,601 `(b, c)` pairs with each
count from 0 through 50; the stable path then completed the previously
overflowing full-split comparisons. A synthetic 3,000-versus-zero discordance
case also verified the separately reported log10 tail (`-902.7889569963`) when
the ordinary binary64 p-value correctly underflows to zero.

The ancillary citation analyzer also passed Ruff, Python compilation, and a
full fail-closed regeneration. It validated the digests of all 38 Qwen batch
traces and all 38 matched outer-teacher traces, required primary coverage of all
47 references plus four frozen route duplicates, and emitted a 38-entry public
trace-hash inventory. The raw traces remain in the ignored lab archive because
they contain retrieved source passages; the derived JSON and immutable hashes
are published with this study.

The regenerated CUDA 12.8 lock, including the plotting dependency, also
resolved in a no-write installation plan with hash enforcement:

```bash
uv pip install --python work/.venv/bin/python --dry-run --require-hashes \
  --index-strategy unsafe-best-match -r requirements-replication.lock
```

Result: 41 packages resolved. The explicit index policy matches the lock
generation command and is needed only for uv's first-index safety default;
the Dockerfile installs the same hashes with pip.

The separate artifact-replay lock also resolved under hash enforcement:

```bash
uv pip install --python work/.venv/bin/python --dry-run --require-hashes \
  --index-strategy unsafe-best-match -r requirements-artifacts.lock
```

Result: 108 packages resolved. This larger closure includes fastai 2.8.8 only
because the released historical checkpoints pickle fastai `Learner` objects;
scratch training and the container do not require that optional stack.
The README's pip path also completed a `--dry-run --require-hashes` plan against
the same lock without a resolver or hash error.

The artifact lock was then installed into a new disposable Python 3.12 virtual
environment. A CPU-only `verify_released.py` replay using the hash-verified LFS
objects regenerated every field in
`results/released_artifact_verification.json`; a recursive numeric comparison
found zero differences at `rel_tol=1e-10, abs_tol=1e-10`. The disposable
environment was moved to the workstation trash after validation.

## Final aggregate and publication checks

All five final analyzers report `status: complete` with the ordered seed set
0–4. Primary, extension, Hessian, and loss-contract integrity maps contain five
`passed` records. The two paired extension analyzers now invoke the complete
primary seed validator before reading a base prediction; a seed-0 smoke replay
confirmed the added base-prediction digest, binary-label, and shape checks.

The Hessian aggregate was regenerated after the public-projection audit and
contains exactly 100 finite raw probe values for each of five models in each of
five seeds: 2,500 values total. Its stored means and sample SDs were recomputed
from those values by the fail-closed analyzer. Every result JSON and the
executed-code manifest also passes `python -m json.tool`.

All four generated CSV tables use an explicit LF line terminator. This keeps
their checked-out bytes identical to the files hashed by the website handoff
under the repository's `eol=lf` policy.

The repository hygiene checker and its regression test also pass. The checker
continues to reject real RFC1918 addresses while recognizing IP-shaped CUDA
package versions on pip-compile continuation lines as pinned dependencies.

The repository-wide Python suite completed with **46 passed and 1 failed**.
The unrelated failure is
`tests/test_protocol.py::test_released_statistics_are_exactly_reconstructable`:
this checkout does not contain the ignored prior-study file
`paper_repro/SLM-RL-Agents/results/all_results.json`. The focused hygiene
regression suite passes 2/2, and this SPRKD study does not read or modify that
missing prior-study artifact.

The typed website handoff is built only after every source aggregate and linked
artifact exists:

```bash
work/.venv/bin/python scripts/build_website_handoff.py \
  --study-root . --output WEBSITE_HANDOFF.json \
  --classification not_replicated \
  --underlying-claim-status inconclusive \
  --rationale "Neither released artifacts nor five-seed final outcomes reproduced the reported stable accuracy and ordering; best-epoch proximity and missing historical selection/provenance leave the underlying method unresolved."
```

The final validation checks the exact seven input schema versions, target arXiv
ID, five ordered run routes, complete run-level model/comparison projections,
typed accuracy—not reward—metric identifier, post-hoc boundary, 2,500 Hessian
probes, unique artifact paths, and the SHA-256/byte count of every allowlisted
artifact. The handoff deliberately reports the canonical site import as
blocked until the frontend accepts a typed classification-accuracy arm.

## Container status

The Dockerfile and shell/Python syntax are checked, but neither Docker nor
Podman is installed on the experiment workstation. An image build is therefore
not represented as tested. The dev-box environment already matches the
container's pinned Torch/CUDA/Python dependency set closely enough to execute
the same runner; a clean container build remains a release gate on a host with
NVIDIA Container Toolkit.

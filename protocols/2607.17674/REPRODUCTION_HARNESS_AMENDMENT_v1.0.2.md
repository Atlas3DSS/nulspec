# Primary-execution harness amendment v1.0.2

This prospective trace-only amendment is frozen while the first Track R and
Track M 0.5B arms are active and before either 1.5B arm starts. It does not
change the scientific protocol, matrix, data, model revisions, upstream code,
training or evaluation commands, precision, optimization, seeds, resource
guards, arm order, stopping rules, or interpretation.

The v1.0.0 and v1.0.1 run-manifest helper invoked `python -m pip freeze --all`.
The exact `uv`-managed paper environment intentionally has no `pip` module, so
both active start manifests retained Python identity but recorded an empty
package list and a nonzero capture status. Version 1.0.2 retains that failed
attempt in its original manifests and makes two prospective provenance changes:

1. Run-manifest capture falls back to `importlib.metadata` when `pip freeze`
   fails, while recording the failed pip status and stderr separately.
2. Every new arm receives an append-only `python-environment.json` containing
   Python executable identity, its binary hash, platform, the `uv.lock` hash,
   normalized package records, and a package-list hash before training starts.
   The terminal-status trap is installed before this new capture step so a
   provenance failure produces `run.failed.json` rather than an unterminated
   attempt.

After each active 0.5B arm reaches a terminal state, the same standalone helper
will add a clearly labeled post-run supplemental inventory. It cannot be
backfilled into or represented as part of the original start manifest. The
amended harness is frozen by tag `2607.17674-primary-harness-v1.0.2`.

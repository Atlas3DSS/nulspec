# Primary-execution harness amendment v1.0.1

This prospective trace-only amendment is frozen after the first Track R arm
started and before any Track M arm or 1.5B arm started. It does not change the
scientific protocol version (`1.0.0`), matrix, data, model revisions, upstream
code, training or evaluation commands, precision, optimization, seeds,
resource guards, arm order, stopping rules, or result interpretation.

The v1.0.0 runner logged the path of the trained Track R base model reused by a
Track M arm, but did not create a content manifest for that input tree. Harness
v1.0.1 writes an append-only SHA-256 manifest of every base-model input file
before factorization and records its source arm and attempt identifier. This
also permits byte-exact verification when a completed base stage is copied to
a second host. The added read-only hashing step cannot alter the model files.

The first already-running Track R 0.5B attempt remains an unmodified v1.0.0
attempt. Its base tree receives a separate post-run integrity audit; it is not
backfilled into the active attempt. All subsequent arms use the amended runner,
frozen by tag `2607.17674-primary-harness-v1.0.1`.

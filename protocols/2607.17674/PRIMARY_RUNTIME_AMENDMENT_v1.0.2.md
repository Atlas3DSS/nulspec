# Primary runtime amendment v1.0.2

## Scope

This amendment supersedes only the recovery-manifest layout in primary runtime
amendment v1.0.1. The v1.0.1 correction that writes primary runner output to a
regular file remains in force. No model, data, checkpoint, seed, optimization,
generation, evaluation, or comparison setting changes.

## Failed v1.0.1 recovery preflight

The first v1.0.1 recovery invocation reached source hashing and then stopped
before launching the upstream evaluator. The generic manifest helper accepts
only `start` and `end` as phase values; the recovery supplied
`evaluation_recovery_start` and `evaluation_recovery_end`, so both manifest
calls failed validation and the guarded command returned 2. The GPU remained
idle. The root-level `evaluation-recovery.source.json` and
`logs/evaluation-recovery-runner.log` are retained as zero-science operational
evidence and are not accepted by the matrix analyzer.

## Corrected recovery identity

Every new recovery invocation now receives a unique directory:

`evaluation-recovery-attempts/recovery-<UTC>-<git-commit>/`

That directory owns `source.json`, `recovery.start.json`, one terminal recovery
manifest, and its logs. The generic helper uses its supported `start` and `end`
phase values; the directory and source schema carry the recovery-specific
meaning. Failed recoveries are append-only and do not block a later fresh
recovery while the canonical evaluation directory remains empty. At most one
completed recovery is permitted.

The analyzer accepts a recovered scientific result only when the original
primary exit is 141, the recovery terminal manifest exits 0, the source hashes
match the original failure and factorization artifacts, and the evaluator
output hash matches its file manifest. It reports the result as
`completed_recovered_evaluation`, never as an uninterrupted completion. A clean
end-to-end `run.complete.json`, if later produced, still takes precedence.

The pinned upstream evaluator source SHA-256 is
`6a6d8326108f29f3e522258a731f8ebb343092a6b8a0019cf868a75b7b51b330`;
the already frozen `evaluation.json` SHA-256 is
`39731599084d4c678d52edad50b301fa11716b123ce7b1041dcc64eb4f00bb0a`.
Both values are checked by the analyzer rather than merely recorded.

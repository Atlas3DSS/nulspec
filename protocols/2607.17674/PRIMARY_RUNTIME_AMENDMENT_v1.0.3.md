# Primary runtime amendment v1.0.3

Two Track M attempts launched on 2026-08-03 were interrupted when their SSH
observer transports ended. The 0.5B attempt stopped after optimizer step 120 of
782, and the 1.5B attempt stopped after step 150. Neither wrote its final
factorization checkpoint, final metrics, or released evaluation. The runner's
EXIT-only trap inherited status zero from the last completed child command and
incorrectly named both terminal manifests `run.complete.json`. The frozen
matrix analyzer correctly treats both attempts as `invalid_complete` because
their required artifacts are absent. They remain immutable with zero numerical
result weight.

This is a NULSPEC orchestration and terminal-classification failure, not an
upstream-paper failure. The 1.5B launcher journal records an SSH broken pipe;
the 0.5B attempt ended with the same observer-session termination signature.
Neither event was caused by a GPU, memory, thermal, or protected-service guard.

Runtime v1.0.3 prospectively changes execution control only:

1. Long primary arms run as detached transient user services on the target
   host. The SSH caller returns after service creation and does not own the
   scientific process lifetime.
2. SIGHUP, SIGINT, and SIGTERM receive explicit nonzero exit classifications.
3. Exit status zero cannot create `run.complete.json` until a separate
   validator confirms the full epoch-0001 checkpoint, factorization config and
   final metrics at optimizer step 782, released evaluation metrics, and the
   evaluation file-manifest hash.
4. A zero-status process with incomplete artifacts is reclassified as local
   failure exit 70 and receives `run.failed.json` plus an immutable validation
   record.
5. Fresh Track M attempts start from scratch. No partial optimizer state or
   interim validation metric from either invalid attempt is reused.

Model, data, seed, response source, objective, precision, batch sizes,
optimizer, schedule, epoch count, evaluation, and stopping rules are unchanged.

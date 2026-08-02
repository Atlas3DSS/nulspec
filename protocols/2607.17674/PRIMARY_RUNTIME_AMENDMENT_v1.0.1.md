# Primary runtime amendment v1.0.1

## Scope

This amendment changes orchestration and evidence handling only. It does not
change a model, dataset, seed, optimizer, precision, batch size, checkpoint,
generation setting, evaluator, or comparison rule in protocol v1.0.0.

## Trigger

The registered Track R Qwen2.5-1.5B attempt completed all 782 factorization
batches and wrote its final checkpoint and factorization metrics. When the
runner launched the authors' separate evaluator, verbose progress output was
still being mirrored through the bounded SSH observer transport. That observer
pipe closed, the nested `tee` chain propagated SIGPIPE, and the runner preserved
exit code 141 in `run.failed.json`. There was no CUDA error, kernel OOM event,
thermal guard trip, model error, or primary-service restart.

The failed attempt remains failed and its original terminal manifest and
truncated evaluator log are never overwritten.

## Correction for future attempts

The authoritative runner stream is written directly to `runner.log`. Read-only
status probes may tail that file, but a probe or transport can no longer become
part of the scientific process's stdout chain.

## Narrow evaluation recovery

An evaluation recovery is eligible only when all of the following hold:

1. the source attempt has `run.failed.json`, no `run.complete.json`, and exit
   code 141;
2. factorization training completed and the final `last.pt` target, config, and
   metrics exist;
3. the first evaluation output directory is absent or empty;
4. source, checkpoint, evaluator, configuration, and failure hashes are bound
   before compute;
5. the unchanged upstream command is rerun with
   `experiments.factorization.evaluate`, `configs/paper/evaluation.json`, the
   original factorization directory, and the registered evaluation directory;
6. recovery start, completion, logs, outputs, and a file manifest are appended
   under explicit `evaluation-recovery.*` names.

This works because the released evaluator is already a standalone process. It
loads `factorization/checkpoints/last.pt` and does not consume training-process
memory or RNG state. The recovery therefore makes no scientific change, while
the analyzer and report retain the operational distinction as
`completed_recovered_evaluation`. A later clean end-to-end completion, if run,
takes precedence over a recovered attempt.

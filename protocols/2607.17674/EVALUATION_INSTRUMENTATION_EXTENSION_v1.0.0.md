# Evaluation instrumentation extension v1.0.0

## Status and purpose

This prospective extension was frozen while the first primary factorization
arm was still training and before any primary standalone evaluation existed.
It does not modify the pinned upstream tree, a primary checkpoint, or the two
released calculations. Its purpose is to retain every classification that the
released evaluator discards and to measure three preregistered sensitivities.

The executable is `scripts/evaluate_2607_17674_instrumented.py`.

## Two registered RNG modes

1. `released-reseed` exactly replays the released evaluator's seed policy:
   Distributional Fidelity restarts the base seed in every batch; Analogical
   Consistency uses `base_seed + batch_start + 1`.
2. `advancing` seeds once at the start of each metric and passes no per-call
   seed, allowing the Torch RNG stream to advance across batches.

The first mode is a trace-preserving reproduction check. Its two released
scalars must match the primary aggregate-only evaluator when checkpoint,
environment, batch size, and seed match. A mismatch is a harness failure and
must be resolved before interpretation. The second mode is a sensitivity, not
a replacement primary result.

## Preserved records and registered summaries

The extension writes one JSONL row for each of 10,000 fidelity generations and
one for each of 1,024 analogical pairs. Rows retain example identities, task
family, rendered generations, inferred compatible-strategy sets, and exact
classification decisions. They contain no credentials.

The following summaries are fixed before results:

- released Distributional Fidelity (`unique_strategy + ambiguous_strategy`);
- released Analogical Consistency (nonempty strategy-set overlap);
- nonempty exact strategy-set equality;
- unique-strategy-only equality;
- ambiguous-pair and undefined-strategy-pair prevalence;
- task-conditioned outcome counts, computed later from the preserved rows;
- prompt/pair bootstrap intervals conditional on one trained checkpoint and
  the observed decoding draws, reported only with that limitation.

No interval from this extension estimates fresh-training variability. The
released-reseed outcomes are batch-dependent by construction, so an
independent-example interval is not valid for that mode. Bootstrap uncertainty
is reserved for the advancing-stream sensitivity and will remain conditional
on one checkpoint and one decoding realization.

## Fail-closed artifact contract

The output directory must not already exist. `run.start.json` binds the primary
checkpoint SHA-256, factorization config SHA-256, workspace revision, upstream
revision, seed, batch size, pair count, device, and RNG mode. On success,
`run.complete.json` binds the SHA-256 of both JSONL traces and `metrics.json`.
Partial directories are retained as failed/interrupted evidence and are never
resumed or overwritten.

## Pre-result verification

Before freezing this extension, the `released-reseed` path was run on the
upstream eight-example CPU smoke checkpoint with two analogical pairs. Its
Distributional Fidelity and Analogical Consistency were both exactly equal to
the upstream standalone evaluator (`0.0` and `0.0`), and the trace contained
exactly eight fidelity rows and two pair rows. The ignored completion-manifest
SHA-256 is
`48d8517039475befca6be8fdc97cf1c705d5e64ac0e15c88a41291d45b7e8883`.

## Interpretation boundary

This instrumentation can reveal sensitivity to batchwise RNG restart and the
ambiguous-strategy convention. It cannot isolate the effect of the extra
supervised `</z>` boundary token, which requires new training, and it cannot
repair the response-source difference between Track R and Track M. Those are
separate paired extensions after primary completion.

# Evaluation instrumentation amendment v1.0.1

## Scope

This trace-only amendment was frozen while the first primary factorization arm
was still training and before any standalone primary metric existed. It does
not change either registered RNG mode, a generated token, a classification
rule, or a summary definition from v1.0.0.

## Added provenance guard

Version 1.0.1 refuses scientific execution unless both the NULSPEC workspace
and pinned upstream tree have no tracked changes. It records the exact Git
revisions, Python/platform identity, Torch/CUDA/cuDNN versions, resolved device,
GPU name, memory, and compute capability. The two RNG-mode traces must match on
all environment and input identities before comparison.

## Added fail-closed analyzer

The new executable
`scripts/analyze_2607_17674_instrumented_evaluation.py` rejects missing files,
changed hashes, nonconsecutive row indices, row-count disagreements,
metric/recomputation disagreements, internally inconsistent strategy-set
decisions, mismatched checkpoint/source/environment identities, prompt/pair
misalignment between modes, and any failure of exact
primary/released-reseed scalar parity.

Only advancing-stream rows receive conditional bootstrap intervals. The
released-reseed trace receives none because its generation draws are dependent
across batches. Every interval is explicitly limited to prompt/pair resampling
conditional on one checkpoint and one generation per prompt; it does not
estimate fresh-training or repeated-decoding variability.

## Version boundary

The v1.0.0 smoke trace remains valid evidence for the generation logic check,
but final sensitivity runs and their comparison must use instrumentation
version 1.0.1 and this amendment's analyzer.

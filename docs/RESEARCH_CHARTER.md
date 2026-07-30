# Research charter

## Purpose

This project independently checks recent computational research using locally
controlled hardware. Its first study targets arXiv:2607.25091. The longer-term
goal is a series of reproducible paper checks that are useful to authors,
practitioners, and other independent researchers.

## Order of operations

1. **Artifact verification:** establish exactly what the paper, repository,
   datasets, checkpoints, and result files contain.
2. **Reproduction:** execute the most faithful feasible version of the stated
   method. If sources conflict, preserve each authoritative interpretation
   separately.
3. **Diagnosis:** explain failures and deviations with evidence. Do not silently
   repair a primary reproduction.
4. **Extension:** only after the primary result is frozen, test corrections,
   alternative evaluations, or new hypotheses.

## Non-negotiable reporting rules

- Null, negative, unstable, and incomplete runs are results.
- No run is deleted because its outcome is inconvenient.
- Every reported number must trace to raw observations, code revision, data
  hashes, a run manifest, and an analysis command.
- Exploratory findings are labeled exploratory until tested on untouched runs.
- Post-hoc exclusions and protocol amendments are reported explicitly.
- Original authors receive accurate attribution and a fair description of
  release limitations.
- Claims are calibrated to the evidence. “Failed to reproduce” does not by
  itself establish that an original claim is false.

## Reproducibility standard

Another researcher should be able to:

1. clone one Git commit or release;
2. fetch every external input from an immutable revision and verify its hash;
3. reconstruct the environment;
4. launch one arm with a single documented command;
5. obtain a complete machine-readable run manifest;
6. regenerate tables and figures without model retraining; and
7. identify every known difference from the target work.

## Repository policy

GitHub is the source of truth for protocols, code, issues, decisions, small raw
records, and reports. Large datasets and checkpoints use an appropriate
artifact host and are referenced by immutable revision plus SHA-256. Protocol
releases are tagged before confirmatory compute begins.

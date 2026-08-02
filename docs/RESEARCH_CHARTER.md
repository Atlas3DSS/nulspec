# Research charter

## Purpose

This project independently checks recent computational research using locally
controlled hardware. Its first study targets arXiv:2607.25091. The longer-term
goal is a field-diverse series of reproducible paper checks that is useful to
authors, practitioners, and other independent researchers. AI and machine
learning are one research area in that portfolio, not its default boundary.

## Candidate-selection policy

- Candidate papers must have a public arXiv record. AI/ML candidates use a
  rolling 12-month window; non-AI/ML candidates use a rolling 36-month window,
  measured from the first public arXiv version when screening begins.
- A candidate must be computationally closed enough to test end to end using
  obtainable inputs. Pure wet-lab claims, unavailable instruments, proprietary
  datasets, irreproducible private APIs, and inaccessible human-subject data
  are out of scope unless the paper contains a separable open computational
  claim.
- Selection rounds cast across fields rather than treating available ML
  tooling as a reason to select ML papers. Suitable areas include
  computational chemistry, geospatial and remote-sensing analysis, statistics,
  economics and quantitative social science, bioinformatics, ecology and
  climate, network science, numerical methods, and other open-data
  computational work.
- When candidates are similarly feasible and interesting, prefer the field
  underrepresented in the published NULSPEC corpus. Candidate batches should
  visibly mix AI/ML and non-AI/ML work instead of presenting one undifferentiated
  popularity ranking.
- Rank candidates using public-interest value, clarity of the falsifiable
  claims, input availability, artifact quality, estimated compute and wall
  time, licensing, and the likelihood that an independent result would help
  the relevant community. A null result remains useful; expected agreement is
  never a selection criterion.
- Favor short, self-contained CPU or modest-GPU studies alongside long
  accelerator runs when resource isolation permits. This builds a broader
  corpus without allowing throughput pressure to weaken a faithful primary
  attempt.

Every accepted candidate is labeled before execution as one of two evidence
paths:

1. **Artifact reproduction:** rerun the authors' released code, data, and
   configuration as exactly as feasible.
2. **Independent methods reimplementation:** reconstruct the stated method
   against the same or an author-sanctioned open dataset when usable released
   artifacts do not exist.

The second path is not described as an exact code reproduction. Both paths
must bind immutable inputs, preregister deviations, preserve failures, and
make the resulting claim no stronger than the evidence permits.

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

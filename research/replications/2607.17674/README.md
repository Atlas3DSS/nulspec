# NULSPEC replication workspace: arXiv:2607.17674

This directory holds the append-only working record for the replication of
*Uncovering Latent Reasoning Strategies in Language Models*.

The frozen protocol and source manifest live in
`protocols/2607.17674/`. Large downloads, generated benchmark data, model
snapshots, checkpoints, and private machine manifests live beneath ignored
`work/`, `outputs/`, and `private/` directories.

Current state: primary execution is active. The first released-config arm began
from the frozen v1.0.0 protocol; its Qwen2.5-0.5B base-model stage completed all
100,000 training records and the unchanged released factorization stage is in
progress. These are execution milestones, not result claims. Terminal status,
metrics, and artifact hashes come only from the immutable run manifest and
post-run analyzer.

Source ordering is fixed: artifact verification, released-code reproduction,
manuscript-method reproduction, diagnosis, then extension.

Primary arms after the already-running first Track R attempt use trace-only
harness tag `2607.17674-primary-harness-v1.0.1`. It adds a byte-exact manifest
for each factorization stage's trained base-model input; the scientific
protocol, upstream commands, and analyzer remain version 1.0.0.
The reason and checksum verification for staging the completed 0.5B base stage
to the second host are recorded in `CROSS_HOST_STAGING.md`.

## Reproducible analysis helpers

The citation inventory is regenerated from the pinned arXiv source with:

```bash
python scripts/inventory_2607_17674_citations.py \
  --source-root research/replications/2607.17674/work/sources/arxiv-src \
  --output /path/to/new-citation-inventory.json
```

The script refuses to overwrite an existing inventory. The tracked
`protocols/2607.17674/citation_inventory.json` is the deterministic reference
output.

After one or more primary attempts reach a terminal state, consolidate them
without editing their artifacts:

```bash
python scripts/analyze_2607_17674_matrix.py \
  --runs-root research/replications/2607.17674/work/primary/runs \
  --output research/replications/2607.17674/work/matrix-analysis.json \
  --markdown research/replications/2607.17674/work/MATRIX_STATUS.md
```

The analyzer validates terminal manifests, factorization settings, metric
ranges, and the evaluation-manifest hash before comparing an arm with the
preregistered digitized reference. It reports aggregate-only uncertainty as
unavailable and never manufactures an interval from missing observations.

Operational mistakes and upstream limitations are kept in `ERROR_LOG.md` as
separate append-only sections. The executable-artifact check is summarized in
`SMOKE_TEST.md`; the complete citation-source acquisition and its four
immutable attempts are summarized in `CITATION_SOURCE_ACQUISITION.md`.
Citation-review packetization is recorded in
`CITATION_REVIEW_PACKETIZATION.md`. Its prospective v1.0.1 amendment was tagged
before any Qwen citation invocation and covers 41 sources, 74 occurrences, and
all 4,230,676 extracted-text bytes without retrieval shortcuts.
The Qwen execution harness has the additional trace-only tag
`2607.17674-citation-audit-harness-v1.0.2`, which adds the llama-server binary
hash without changing the v1.0.1 evidence or generation contract.

The separate reviewer-of-reviewers hierarchy is now frozen prospectively at
`2607.17674-citation-teachers-v1.0.2`. It preserves every Qwen record, runs GLM
and Kimi as independent teachers, and uses subscription-authenticated Codex for
outer adjudication. Exact prompts, schemas, provider routes, spend gates,
executables, and the terminal trace validator are hash-bound. No Qwen, external
teacher, or Codex citation decision existed when that tag was created.
The exact staged execution order and fail-closed boundaries are documented in
`CITATION_REVIEW_RUNBOOK.md`.
The six-source human calibration ranges were written blind to Qwen output and
are documented in `CITATION_CALIBRATION_EXPECTATIONS.md`.

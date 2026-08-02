# NULSPEC replication workspace: arXiv:2607.17674

This directory holds the append-only working record for the replication of
*Uncovering Latent Reasoning Strategies in Language Models*.

The frozen protocol and source manifest live in
`protocols/2607.17674/`. Large downloads, generated benchmark data, model
snapshots, checkpoints, and private machine manifests live beneath ignored
`work/`, `outputs/`, and `private/` directories.

Current state: artifact verification and protocol registration. No primary GPU
arm had begun when protocol v1.0.0 was written.

Source ordering is fixed: artifact verification, released-code reproduction,
manuscript-method reproduction, diagnosis, then extension.

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
`SMOKE_TEST.md`.

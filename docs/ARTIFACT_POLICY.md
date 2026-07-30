# Artifact and provenance policy

## Stored in Git

- protocols, configuration registries, and decision records;
- source patches and bootstrap scripts;
- environment and hardware manifests;
- run metadata, small logs, per-example scalar records, and analysis code;
- final machine-readable summaries, figures, and reports.

## Stored outside ordinary Git history

- downloaded source datasets;
- pretrained model caches;
- SFT, reward-model, PPO, optimizer, and scheduler checkpoints;
- other individual files too large for normal GitHub review.

External artifacts must have:

- an immutable repository revision or release identifier;
- a relative path and byte count;
- a SHA-256 digest;
- license and source attribution;
- a documented retrieval command.

Git LFS is not assumed to be archival storage. Public releases should use a
stable model/dataset host and, for paper-grade snapshots, an archival service
such as Zenodo. GitHub release notes should link the corresponding artifact
manifest.

## Raw-data immutability

Completed run directories are append-only. Analysis writes to a separate
derived directory. A rerun receives a new run identifier even when it uses the
same configuration. Failed runs retain their logs and terminal state.

## Sensitive information

Manifests whitelist environment fields rather than dumping the complete
environment. Tokens, API keys, SSH material, user prompts unrelated to the
study, and private service configuration must never enter artifacts.

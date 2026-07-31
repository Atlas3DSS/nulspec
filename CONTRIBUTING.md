# Contributing

This repository treats reproduction as an empirical record, not a contest to
obtain a preferred result.

## Required practice

1. Open an issue describing the proposed run, correction, or extension.
2. State whether it belongs to artifact verification, manuscript reproduction,
   released-code reproduction, or an extension.
3. Pin source, data, model, and environment revisions before the run.
4. Do not change a frozen protocol in place. Amend it in a new version and
   explain why.
5. Preserve failed and null runs. Never overwrite an existing run directory.
6. Report all attempted configurations, exclusions, retries, and stopping
   decisions.
7. Keep generated checkpoints and datasets outside ordinary Git history; record
   immutable locations, sizes, and SHA-256 hashes.
8. Submit analysis changes without editing raw observations.
9. Apply the
   [lab repository scope and hygiene policy](docs/REPOSITORY_SCOPE_POLICY.md)
   before publication.

## Pull requests

Every pull request should include:

- the issue or protocol section it implements;
- tests or validation appropriate to the change;
- any effect on comparability with earlier runs;
- generated files that changed and the command that regenerated them;
- an explicit statement when there is no effect on experimental semantics.

Results are welcome whether they confirm, fail to reproduce, contradict, or are
inconclusive.

# Citation-teacher amendment v1.0.3

This trace-only harness amendment is frozen before any citation teacher packet
is built with version 1.0.3 and before any GLM, Kimi, or Codex invocation under
that version. Versions 1.0.0 through 1.0.2 remain immutable.

The version 1.0.2 packet builder used JSON's lowercase `false` in one Python
provenance field. Reaching that statement would raise `NameError` before a
packet or reviewer request existed. Version 1.0.3 changes only that literal to
Python `False`, advances the versioned config and runner defaults, and rebinds
the affected harness files by SHA-256.

The Qwen evidence boundary, prompts, schemas, provider routes, model requests,
reasoning levels, timeouts, retry rules, spend limits, Codex subscription
boundary, and release controls are unchanged. The correction cannot alter a
Qwen record, scientific result, publication state, training signal, or email
authorization.

The amended settings are in `citation_teacher_config.v1.0.3.json` and are
frozen by tag `2607.17674-citation-teachers-v1.0.3`.

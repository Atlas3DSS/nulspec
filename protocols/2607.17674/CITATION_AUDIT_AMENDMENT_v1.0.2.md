# Citation-audit execution amendment v1.0.2

This prospective trace-only amendment is frozen before any Qwen citation
review. It does not change the v1.0.1 evidence packets, source ordering,
calibration set, prompts, schemas, reviewer model, generation settings, retry
budget, validation rules, or review-plan hashes.

The v1.0.1 runner recorded the llama.cpp version output and complete route
properties but did not hash the llama-server executable itself. Version 1.0.2
adds the executable basename, byte count, and SHA-256 to `run-input.json` while
retaining the existing version command output. This closes an implementation-
provenance gap without changing a model request or scientific decision.

The amended runner is frozen by tag
`2607.17674-citation-audit-harness-v1.0.2`. The parent evidence contract remains
`2607.17674-citation-audit-v1.0.1`.

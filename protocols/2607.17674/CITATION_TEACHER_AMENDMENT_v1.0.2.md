# Citation-teacher amendment v1.0.2

This prospective execution amendment is frozen before any Qwen, external
teacher, or Codex citation-review invocation. It retains the v1.0.0 evidence
boundary and hierarchy and the v1.0.1 prompts, schemas, provider routes, rate
cards, timeouts, retry policy, and spend limits without modification.

Version 1.0.2 adds the complete append-only execution harness and binds its
packet builder, output-contract validator, GLM/Kimi runner, Codex runner, and
terminal trace validator by SHA-256. Codex is pinned prospectively to
`gpt-5.6-sol` with high reasoning through subscription authentication. All API
key variables are removed from its environment, its tool features are disabled,
and its session is ephemeral and read-only. The trace records the CLI version
and actual execution events. Because the subscription does not expose a
defensible marginal per-run dollar amount, Codex cost is recorded as null with
that accounting limitation rather than as a fabricated zero.

The validators require one terminal valid substantive result per GLM, Kimi,
and Codex chain; invalid attempts retain zero scientific weight. Provider costs
must reconcile across attempts and the completion manifest. Obvious teacher
disagreement cannot be collapsed, and no generated output receives publication,
training, or email authority.

The amended settings are in `citation_teacher_config.v1.0.2.json` and are
frozen by tag `2607.17674-citation-teachers-v1.0.2`.

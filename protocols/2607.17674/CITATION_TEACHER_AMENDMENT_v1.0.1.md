# Citation-teacher amendment v1.0.1

This prospective amendment is frozen before any Qwen or external citation
review. It does not change the evidence boundary, models, hierarchy, rubric,
or retry policy in v1.0.0. It adds the exact teacher and Codex prompt files,
their hashes, output-schema hashes, the exact direct-provider implementation
hash, dated public rate-card locators, and an enforced provider-spend gate.

Before every GLM or Kimi attempt, the runner computes a conservative upper
cost from packet bytes, the route's full requested completion allowance, and
the recorded rate card. A fresh attempt is forbidden when that upper bound
would exceed either the logical-teacher or total provider budget remaining.
Completed usage and provider-reported or calculated cost remain in the trace.
The gate can therefore stop a repair chain before its nominal attempt limit;
it can never convert a missing teacher into a vote.

Provider pricing is mutable external state. The configuration records the
official pages observed on 2026-08-01 and freezes conservative per-route rates
in the bound provider implementation. A numeric provider-reported cost is the
accounting authority for a completed call; the frozen rate is the fallback and
the pre-attempt ceiling basis. Any later price change is recorded rather than
silently changing this tag.

The amended settings are in `citation_teacher_config.v1.0.1.json` and are
frozen by tag `2607.17674-citation-teachers-v1.0.1`.

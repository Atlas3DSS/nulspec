# Frozen citation-teacher protocol: arXiv:2607.17674

**Protocol version:** 1.0.0

**Protocol tag:** `2607.17674-citation-teachers-v1.0.0`

**Parent citation-audit protocol:** `2607.17674-citation-audit-v1.0.1`

This protocol is frozen before any Qwen citation-review invocation. It governs
only review of the primary Qwen reviewer; it cannot alter primary experimental
observations or silently rewrite a Qwen record.

## Evidence boundary

The immutable teacher packet contains all schema-valid Qwen evidence-chunk
records, all 41 Qwen source-level citation reviews, aggregate counts, bounded
evidence excerpts, and public source locators. It excludes source PDFs, full
extracted source text, Qwen prompts and reasoning, checkpoints, credentials,
private infrastructure identifiers, and unrelated run state.

This boundary lets teachers test internal consistency, excerpt-to-claim fit,
score calibration, occurrence coverage, and systemic patterns. It cannot prove
that Qwen found every relevant passage in the underlying source. Every teacher
and Codex score is therefore explicitly conditional on the supplied Qwen
packet and automated excerpt-grounding checks.

## Independent teachers

GLM and Kimi receive byte-identical packets independently and concurrently.
Neither sees the other's output. The fixed logical routes, high-reasoning
settings, timeouts, retry limits, and cost fields are in
`citation_teacher_config.v1.0.0.json`. Each returns
`citation_teacher_audit.schema.json` and assigns Qwen a reviewer-quality score
from 1 through 10 using the parent protocol's anchors.

Every invocation is streamed. Raw streams, normalized events, exact prompts,
credential-free request bodies, route/model identity, usage, cost, timing, and
all failures are retained in a unique ignored directory. Invalid transport or
schema attempts have zero scientific weight and may receive only a linked
fresh structural/transport repair within the fixed budget. A valid substantive
`pass`, `warn`, or `fail` is never retried.

## Codex adjudication

Codex begins only after both logical teacher chains terminate in valid audits.
It receives the Qwen packet and every credential-free GLM/Kimi attempt record,
assesses each teacher separately, preserves all scientific disagreements, and
returns `citation_codex_adjudication.schema.json`. Codex assigns the final
1--10 Qwen reviewer-quality score and adjudicates flagged citation records.

Codex uses subscription authentication with API-key variables removed, an
ephemeral read-only execution directory, no tools, and no session persistence.
Malformed Codex objects have zero decision weight and may receive only a
linked structural retry. A valid scientific decision is never retried.

## Release and Fable boundary

Fable is excluded from this recurring teacher loop. One separate final
pipeline critique may occur only after Qwen, both teachers, Codex, and the full
trace validator complete. It receives a sanitized packet, is single-shot, and
cannot authorize publication, training, or email. The separate final-release
gate and every author email still require their own human controls; email
dispatch always requires approval of the exact hashed draft.

The hierarchy fails closed on a missing or invalid teacher chain, packet
mutation, an unpreserved attempt, collapsed disagreement, score outside 1--10,
scope-boundary violation, incomplete trace/cost record, or any generated claim
of release authority.

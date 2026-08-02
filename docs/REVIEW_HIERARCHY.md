# Qwen teacher hierarchy and trace policy

## Purpose

NULSPEC uses a layered process when local Qwen is the primary reviewer. GLM
and Kimi independently audit Qwen's review records. Codex then adjudicates the
two teacher audits as the outer layer.

```text
local Qwen primary review
        |
        +---------------------+
        |                     |
        v                     v
independent GLM audit   independent Kimi audit
        |                     |
        +----------+----------+
                   v
         Codex outer adjudication
```

Fable is deliberately excluded from this recurring teacher loop because its
cost profile is inappropriate for repeated process audits. Its separate roles
are final-release review and one sampled advisory process critique per ten
completed, validated paper pipelines.

## Evidence boundary

The teacher layers receive only Qwen's structured reviewer records and
aggregate counts. The packet excludes underlying prompts, candidate outputs,
checkpoints, reward values, training state, credentials, host data, and private
infrastructure identifiers. This preserves the boundary used by the completed
historical direct-Codex audit.

GLM, Kimi, and Codex may assess:

- A/B-order and mapped-winner consistency;
- contradictions between a winner and its rationale;
- unsupported certainty or vacuous reasoning;
- malformed records; and
- aggregate position bias visible in the supplied records.

They cannot determine whether unseen candidate content was semantically
correct. Their findings cannot silently rewrite the primary result, become
training reward, or authorize publication.

## Models and harnesses

GLM and Kimi receive the same immutable Qwen packet independently and are
launched concurrently. Neither sees the other model's audit. Codex waits at a
join until both logical teacher chains are valid. GLM-5.2 currently uses
OpenRouter with latency-sorted endpoint selection and an explicit alternate
provider order for linked transport repairs. Kimi K3 uses Moonshot AI's
first-party API and does not pass through OpenRouter. Every attempt records the
requested logical model, provider model identifier, route configuration, and
model identifier returned in the stream. GLM uses high reasoning effort; Kimi
also uses high reasoning effort.

Where the catalog reports a completion maximum, the runner requests that
maximum. Where completion capacity is the remaining context window, the runner
calculates a conservative packet-safe allowance and records the formula. A
large allowance permits detailed reasoning; it does not require verbosity.

An invalid invocation is never accepted as a teacher audit. The runner
preserves the failed attempt, records its diagnosis and cost, and creates a new
linked attempt with the minimum required repair. Repairs include transport or
provider failures, billing failures, malformed responses, and schema failures.
A valid scientific PASS, WARN, or FAIL is not retried. Every
attempt is immutable, the repair budget is explicit, and exhausting it blocks
the run before Codex. Schema-valid audits with nonconforming evidence
references retain the exact response and an explicit contract warning; they
are not silently rewritten.

Every attempt is streamed. The runner allows 60 seconds for the first provider
event, 60 seconds between subsequent events, and four minutes total. A missed
deadline is an execution failure with zero teacher weight. A GLM repair changes
OpenRouter's provider-selection route; a Kimi repair changes to the separately
configured direct fallback when its key is available. The immutable packet,
schema, reasoning effort, and model-capacity record do not change. Three fully
timed-out attempts exhaust the chain and block Codex, limiting the worst-case
wait to twelve minutes. If the independent Kimi fallback key is unavailable,
the setup failure is retained and the chain blocks without rotating back to
Moonshot. Active streamed progress is preserved as raw evidence.

Codex receives the Qwen packet and every complete credential-free attempt
record in the two valid teacher chains. Each record includes the route,
response model, timing, usage, cost, and byte-count/SHA-256 bindings for its
request, headers, raw SSE, normalized events, assembled response, and parsed
audit. The large raw bodies remain in the ignored archive rather than being
duplicated into the adjudication prompt. Codex assesses each teacher
separately, preserves execution repairs and scientific disagreements, and
identifies trace or scope defects. It cannot relax a missing-evidence gate,
change training signals, authorize publication, or authorize external
messaging.

A malformed or contract-invalid Codex object is also never repaired in place.
The runner preserves it with zero decision weight and issues a linked fresh
Codex attempt with the failed structural gate named explicitly. A valid
substantive adjudication is never retried, and three invalid attempts block the
pipeline.

## Trace contract

Raw traces are retained under an ignored, unique run directory. The directory
contains:

- the exact Qwen packet and both JSON schemas;
- exact logical model and provider-route records and their hashes;
- system and user prompts;
- request bodies with no credentials;
- attempt-start, attempt-complete, repair-link, and teacher-chain records;
- raw provider SSE streams and normalized stream-event records;
- parsed teacher audits and contract warnings;
- usage, reported cost, provider route, elapsed time, and output limits;
- the exact Codex adjudication packet and prompt;
- Codex CLI version, JSONL event transcript, stderr, and final output;
- an append-only lifecycle event log; and
- a sanitized public summary with an aggregate trace hash.

The runner writes the completion record and final lifecycle event before
computing the aggregate. The public-summary copy is excluded from that index to
avoid a circular hash. `validate_review_hierarchy.py` then recomputes the index,
checks every bound trace file, validates fan-out/join ordering and release
controls, and emits a run-specific validation record.

Credentials are read only from ignored environment configuration and never
written to prompts, requests, command arguments, logs, or public output.
Provider request IDs, private paths, and internal host data stay out of the
public projection.

## Separate final-release review

The final release gate requests Fable, GLM, and Kimi independently on the full,
immutable publication packet. This is separate from the Qwen teacher loop.

- A Fable safeguard or technical non-response is logged with its tokens, cost,
  provider message, and hashes. Its decision weight is zero, and it is not a
  scientific `HARD_FAIL`.
- After that zero-weight non-response, valid GLM and Kimi `PASS` decisions
  authorize publication of the bound release.
- If Fable returns a substantive review, all three final reviewers must return
  `PASS`.
- Only a valid substantive Fable `fail` creates scientific `HARD_FAIL`.
- Malformed, missing, or disagreeing final reviews block for human adjudication.
- Email dispatch always requires separate human approval of the exact draft.

## Batched Fable pipeline critique

GLM and Kimi audit every eligible Qwen paper pipeline, and Codex adjudicates
every valid pair. Fable is not called for each paper. After ten distinct paper
pipelines pass their end-to-end trace checks, the batch runner sorts their
study IDs, records a fresh 256-bit random seed, and ranks each ID by SHA-256 of
the seed and ID to reproducibly sample three of the ten. One sanitized packet
contains the shared architecture and schema
sources plus the three sampled completed-run summaries, validation records,
recorded integration failures, and costs. The other seven study IDs remain in
the cadence record so no paper can be reused to assemble another batch.

The batch uses exactly one Fable invocation at maximum effort, with no tools or
session persistence. Its seed, selected IDs, prompt, wrapper, parsed response,
usage, exact model, cost, timing, stderr, and hashes are retained. The ignored,
append-only registry refuses a repeated batch ID or any paper used in an
earlier batch. All ten inputs must validate and the complete packet must remain
under the enforced byte ceiling before the registry claim or model call. A
refusal or malformed response is logged and not retried automatically. The
critique may produce follow-up work, but it has zero decision weight and cannot
alter Qwen judgments, teacher adjudication, a frozen scientific result,
publication authority, or email authority.

Use repository-relative paths in a manifest containing exactly ten unique
papers:

```json
{
  "schema_version": "nulspec-fable-pipeline-critique-batch-input-v1",
  "batch_id": "papers-001",
  "papers": [
    {
      "study_id": "arxiv-study-id",
      "pipeline_summary": "path/to/review-summary.json",
      "validation": "path/to/review-validation.json",
      "corrections": "path/to/architecture-corrections.json"
    }
  ]
}
```

The shown paper object is repeated for ten distinct study IDs. Run the batch
with unique trace and public-result paths:

```bash
python3 extension/fable_pipeline_critique.py \
  --batch-manifest .artifacts/fable-pipeline-critique/papers-001.json \
  --run-id fable-papers-001 \
  --trace-root .artifacts/fable-pipeline-critique/fable-papers-001 \
  --public-result extension/artifacts/fable_pipeline_critique_papers-001.json
```

`--historical-single-run` exists only to reproduce the explicitly authorized
2026-08-01 single-pipeline traces. It is not the prospective cadence.

## Running the teacher hierarchy

```bash
export OPENROUTER_API_KEY='set in ignored environment configuration'
export MOONSHOT_API_KEY='set in ignored environment configuration'

python3 extension/review_hierarchy.py \
  --run-id study-and-date \
  --packet extension/artifacts/outer_teacher_packet.json \
  --trace-root .artifacts/review-hierarchy/study-and-date \
  --public-summary extension/artifacts/review_hierarchy_study-and-date.json
```

The command succeeds when both concurrently launched teacher chains terminate
with valid audits and the Codex adjudication passes its structural and scope
gates. A scientifically critical audit can still be a successful execution. An
invalid attempt enters its logged repair chain; if that chain is exhausted, the
run remains retained and Codex is not invoked.

## Architecture correction on 2026-08-01

Two implementation probes mistakenly included Fable in the recurring teacher
loop. The first was rejected locally before model invocation. The second
reached Fable and cost $1.431673 before the architecture was corrected. Both
traces remain retained. Neither result is eligible for the teacher-loop record,
and the production runner no longer invokes Fable. A subsequent sequential
GLM/Kimi implementation trace was also marked ineligible after it accepted an
invalid Kimi invocation at the join. The production runner now uses concurrent
fan-out and immutable linked repairs.

On 2026-08-01, a parallel OpenRouter probe established both outbound TLS
connections but produced no application response body before it was manually
terminated after approximately 29 minutes. That trace is retained and is not
an eligible teacher run. The current runner sends Kimi directly to Moonshot and
uses streamed progress deadlines for both teachers, so the same blind wait
cannot recur.

The next four hybrid traces exposed configuration and trace-contract defects:
`v5` used maximum instead of high Kimi reasoning and encountered an unavailable
fallback; `v6` finalized its aggregate before its last event; `v7` omitted
required trace metadata from the Codex packet; and `v8` lacked a linked repair
for an invalid Codex object. All four runs and their known costs remain in the
architecture-corrections record and are ineligible as reference executions.

`qwen-teacher-hybrid-20260801-v9` is the first validated protocol-v2 reference
run. GLM-5.2 completed through OpenRouter in 24.716814 seconds for $0.01467896;
Kimi K3 completed through Moonshot in 127.611468 seconds for $0.06617460. Both
returned valid `fail` process audits. Codex's first object had a partial pair
identity and was preserved with zero decision weight; its linked second attempt
was valid and accepted the result as a bounded process audit. The final 45-file
evidence index has aggregate SHA-256
`7c3924a87b4ba6c9b431b26a042e964f930f27182676b3901608c9857d11cb91`
and passed all 11 trace checks. No publication, training, email, or external
message was authorized.

The subsequent one-shot Fable pipeline-critique command did not reach Fable.
Claude Code rejected NULSPEC's unsupported JSON Schema draft declaration
locally in 0.916916 seconds, returned no model output, and reported no charge.
The exact failure is retained as a NULSPEC harness error, not an Anthropic
refusal. The schema and preflight were corrected. After explicit user
authorization, a separate `v2` trace bound the failed record and stderr hashes
and reached Fable without rewriting or retrying `v1` automatically.

The authorized `fable-pipeline-critique-20260801-v2` call completed in
688.55158 seconds for $4.14006. Fable assessed the architecture as
`sound_with_changes` with confidence 0.72 and returned 12 advisory findings:
two medium, seven low, and three informational. The medium findings recommend
an enforced per-run USD ceiling and distinguish safeguard refusals from
technical non-responses in the separate final-release gate. Other findings
cover typed failure classification, provider and Codex identity provenance,
provider-wide sanitization, fault-injection coverage, and structured pair
references. The critique also identified that its frozen packet omitted the
transport and validator source modules; both are now included in future packet
construction. No third critique call was made. None of these findings changed
the frozen Qwen review, teacher audits, Codex adjudication, publication state,
training signals, or email authority.

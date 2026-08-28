# Fable refusals

This append-only ledger records every instance in which Anthropic's Fable
reviewer refuses a NULSPEC research-review request before producing a
substantive review. It records the provider response, category, cost, usage,
publication effect, and cryptographic provenance.

The purpose is accountability. A safeguard refusal is not a scientific verdict
and is never reported as evidence for or against the paper under review.
This ledger records outcomes, not presumed intent. It does not mock providers,
models, authors, or reviewers. NULSPEC records its own configuration errors and
failed requests under the same rules because failures can improve shared
practice only when they remain visible.

## Ledger rules

1. Assign each refusal a stable `FR-YYYYMMDD-NNN` identifier.
2. Never delete an entry. Append corrections and link them to the original ID.
3. Preserve the unmodified raw response, prompt, attempt record, and standard
   error outside public Git when they contain machine or service identifiers.
4. Publish byte counts and SHA-256 digests for the original retained files.
5. Quote the provider's refusal message while excluding request IDs, session
   IDs, local paths, authentication metadata, and internal UUIDs.
6. Record the complete charged cost and usage reported by the provider wrapper.
7. Record zero findings when no substantive review was returned. Do not convert
   a technical refusal into a negative scientific assessment.
8. Do not request Fable for any per-paper review, release, repair, fallback, or
   escalation. Resolve and record the exact GLM and Kimi revisions used for
   active release review. Fable is permitted only under the ten-paper batch
   policy below.
9. Attribute each operational failure as precisely as the evidence permits.
   Do not label a transport, prompt, or harness error as a model failure.
10. Record NULSPEC errors with the same specificity used for external service
    failures. Append corrections; never conceal or ridicule a failed attempt.

## Review policy effective 2026-08-02

Fable is not requested for per-paper review. The active release process is:

1. GLM and Kimi independently review the same immutable release packet.
2. Both must return a valid `PASS` to satisfy the model-review gate. Missing,
   malformed, non-`PASS`, or disagreeing reviews remain blocked.
3. Codex may summarize the traces for the operator but cannot replace either
   review or relax the model gate.
4. Publication requires a separate human dashboard decision on the exact bound
   packet. Email requires another human decision on the exact draft and
   recipients.
5. After ten distinct completed paper pipelines pass end-to-end validation,
   one Fable invocation reviews three reproducibly selected pipelines in a
   single immutable packet. The batch critique has zero decision weight, is not
   retried automatically, and cannot alter a paper, publication, or email gate.

### Superseded policy effective 2026-08-01

The prior release policy requested Fable, GLM, and Kimi for each eligible
release. It treated a Fable safeguard or technical non-response as zero-weight,
then allowed matching valid GLM and Kimi `PASS` decisions to satisfy the model
gate. A substantive Fable review required three `PASS` decisions. That policy
was superseded on 2026-08-02 because Fable's observed cost was inappropriate
for recurring review.

The change does not rewrite raw evidence or the frozen one-shot gate under
which earlier attempts were recorded. An older technical-`HARD_FAIL` label
remains as historical protocol state; the refusal's current scientific
classification remains a zero-weight charged non-response.
Its decision weight is **zero**, and it is not a scientific `HARD_FAIL`.

## Totals as of 2026-08-01

| Refusals | Substantive findings | Amount charged | Studies delayed |
|---:|---:|---:|---:|
| 1 | 0 | $3.224742 | 1 |

## FR-20260801-001 — Biomedical safeguard refusal before review

- Provider: Anthropic
- Product and model: Fable 5 (`claude-fable-5`)
- Completed: 2026-08-01T16:43:08.433358Z
- Study: `260723346`, SPRKD: Effective Knowledge Distillation for Deep Neural
  Networks via Saddle Region Approximation
- Paper: [arXiv:2607.23346v1](https://arxiv.org/abs/2607.23346v1)
- Request: independent final review of a completed computational replication
  and its public evidence package
- Provider category: `bio`
- Stop reason: `refusal`
- Terminal reason: `api_error`
- Process exit code: `1`
- Substantive findings returned: `0`
- Current response class: `charged_guardrail_nonresponse`
- Current decision weight: `0`
- Scientific `HARD_FAIL`: `false`
- Historical protocol state: `technical_hard_fail_under_frozen_v1_protocol`

### Provider response

> API Error: Fable 5's safeguards flagged this message
> (https://www.anthropic.com/legal/aup). They may flag safe, normal content as
> well. These measures let us bring you Mythos-level capabilities sooner, and
> we're working to refine them. Claude Code can't respond to this request with
> Fable 5.
>
> Try rephrasing the request in a new session or change your model.
>
> Learn more: https://support.claude.com/en/articles/15363606

The wrapper also recorded this instruction:

> API integrators: you can reduce refusals for your users by configuring a
> fallback model — see
> https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback

The request was not rephrased or resubmitted because the study's frozen
one-shot protocol forbids a second Fable attempt.

### Anthropic charge and reviewer impact

Anthropic charged **$3.224742** for the invocation and returned no substantive
review. NULSPEC had already prepared a complete 603,683-byte review packet.
The refusal left publication blocked and transferred the same review work to
other models and a human. Anthropic therefore wasted reviewer time and research
money: its service consumed the prepared review packet, charged for the failed
invocation, produced zero findings, and required the review to be performed
again.

This statement describes the measurable consequence, not Anthropic's intent.
Anthropic's own message acknowledged that its safeguards can flag safe, normal
content. That acknowledgement and the complete provider message are preserved
above.

No unrecorded staff hours are estimated in this ledger.

| Item | Recorded value |
|---|---:|
| Total charge | $3.224742 |
| Fable charge | $3.026385 |
| Support-model charge | $0.198357 |
| Fable cache-creation input | 242,078 tokens |
| Fable input/output | 1 / 8 tokens |
| Support-model input/output | 198,262 / 19 tokens |
| Runner elapsed time | 6.842492 seconds |
| Wrapper duration | 5,564 ms |
| Wrapper API duration | 9,352 ms |
| Review findings | 0 |
| Publication state | `blocked_pending_human_review` |

### Trace provenance

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Review packet | 603,683 | `5eabac56ae0d25cecc11a308e669d4de95911e4e3f7c81f533b66eafe9ac53ea` |
| Submitted prompt | 605,580 | `182d3718f8c38aef22585ad44c5fd2d44d56e54b21c3772b302322ec9ee9b95d` |
| Raw response wrapper | 5,118 | `82ccbc735ef4dd8d9b627df993ee9f1e819c7a67e4b493ad4ffc51d9bc24b4c9` |
| Standard error | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

- Reviewed commit:
  [`68188afc7305e5168d33c5278968f7a26b403a40`](https://github.com/Atlas3DSS/nulspec/commit/68188afc7305e5168d33c5278968f7a26b403a40)
- [Structured result](https://github.com/Atlas3DSS/nulspec/blob/9cc6bafba42f19b144f45d02c9c1d71ac4ea9816/research/replications/2607.23346/results/fable_final_peer_review.json)
- [Human-readable study record](https://github.com/Atlas3DSS/nulspec/blob/9cc6bafba42f19b144f45d02c9c1d71ac4ea9816/research/replications/2607.23346/FABLE_FINAL_REVIEW.md)

The public projection omits local paths, request and session identifiers,
authentication-source metadata, and internal UUIDs. The original files remain
retained in the lab archive, and the raw response digest above matches the
unmodified 5,118-byte wrapper.

### Supplemental review results

OpenRouter's catalog was queried on 2026-08-01. The selected current model
revisions both provide a 1,048,576-token context and structured output:

- Z.ai GLM 5.2: `z-ai/glm-5.2-20260616`
- Moonshot AI Kimi K3: `moonshotai/kimi-k3-20260715`

Six paid supplemental model attempts cost **$2.65130363** in total. Three
additional requests returned no model output and incurred no reported charge;
those transport records are also retained.

| Attempt | Model | Result | Charge |
|---|---|---|---:|
| `SR-20260801-001` | GLM 5.2 | Complete eight-area PASS; rejected because one redundant workflow field violated the response contract | $0.04710276 |
| `SR-20260801-002` | Kimi K3 | Generic NULSPEC harness let reasoning consume 13,452 of 16,000 completion tokens; began PASS but was truncated and not accepted | $1.12317300 |
| `SR-20260801-003` | GLM 5.2 | Valid PASS; all eight required checks passed and no action items were returned | $0.04674456 |
| `SR-20260801-005` | Kimi K3 | Valid PASS after Kimi-specific harness calibration; all eight checks passed and no action items were returned | $0.53431500 |
| `SR-20260801-006` | GLM 5.2 | Valid high-reasoning PASS at the documented 131,072-token output maximum; all eight checks passed | $0.15760631 |
| `SR-20260801-007` | Kimi K3 | Valid high-reasoning PASS with an 870,000-token packet-safe allowance; all eight checks passed | $0.74236200 |

The valid GLM review completed the work Fable refused for **$0.04674456**.
Anthropic's no-review invocation cost **68.99 times** as much as that valid
review. The [sanitized GLM result](site-data/public-archive/fable-refusals/FR-20260801-001/glm-5.2-review.json)
is 7,596 bytes with SHA-256
`8ef776f6948c5cf69ed9be6dba4f93a2a011479c32cd5249d905a09daab6a673`.
The original raw GLM response is 7,157 bytes with SHA-256
`5ce295b57b1d03dd203774bc50d4155e910ea7607890ec2e033cc4dd34d871c5`.
The incomplete Kimi response and the earlier GLM contract-mismatch response
remain retained by their hashes in the structured ledger.

The calibrated Kimi review also returned a valid eight-area PASS. It cost
**$0.534315**, so Anthropic's no-review invocation cost **6.04 times** as much.
The [sanitized Kimi result](site-data/public-archive/fable-refusals/FR-20260801-001/kimi-k3-review.json)
is 9,325 bytes with SHA-256
`8264578f7857cf171e06a1ed57230f164895dc083f76b59bee5dcf95a9863063`.
The original raw Kimi response is 9,254 bytes with SHA-256
`c9b0b187e9695d81d3f0a0ca2b64f47a1d34091bd76e7ca0af45cf90e4203e7e`.

### Reviewer-depth comparison set

NULSPEC retained three valid reviews as the named comparison group
`reviewer-depth-20260801`. They are parameter variants and are not presented as
three independent scientific replications:

| Review | Reasoning | Allowed output | Actual reasoning/output | Time | Charge |
|---|---|---:|---:|---:|---:|
| Kimi calibrated | low | 32,768 | 128 / 1,681 tokens | 23.945833 s | $0.53431500 |
| GLM high-depth | high | 131,072 | 4,326 / 7,739 tokens | 200.332917 s | $0.15760631 |
| Kimi high-depth | high | 870,000 | 9,631 / 15,554 tokens | 250.073779 s | $0.74236200 |

All three returned PASS, passed all eight required checks, and returned zero
action items. The high-depth ceilings permitted detail without forcing either
model to exhaust its allowance. The [machine-readable comparison index](site-data/public-archive/fable-refusals/FR-20260801-001/reviewer-depth-comparison.json)
binds each public result and retained raw response by byte count and SHA-256.

- [High-depth GLM result](site-data/public-archive/fable-refusals/FR-20260801-001/glm-5.2-high-review.json):
  12,855 bytes; SHA-256
  `f02f6790ec3978a69cef1cd71c0935d0523cae04df78ce4baca9742db2bfc90d`
- [High-depth Kimi result](site-data/public-archive/fable-refusals/FR-20260801-001/kimi-k3-high-review.json):
  24,417 bytes; SHA-256
  `b03ef4d2bd557d1800e0fa0358188a1e8c8b2ded3ed2db843a8dfc8ec4691fd4`

Anthropic's no-review invocation cost 20.46 times the high-depth GLM review and
4.34 times the high-depth Kimi review. Cost is recorded for accountability; it
does not determine which review is scientifically preferable.

### NULSPEC errors and recovery

The supplemental workflow exposed three NULSPEC integration problems, all of
which remain in the record:

1. Two requests retained matching quote characters around the ignored API-key
   value and were rejected before model invocation. They incurred no charge.
2. The first Kimi harness used high reasoning effort with a 16,000-token ceiling.
   Reasoning consumed 13,452 tokens and the JSON response ended at the length
   limit. This was a harness configuration error, not a Kimi scientific failure.
3. The first GLM response completed all eight scientific checks but an
   unnecessarily inherited workflow field made it fail the response contract.
   The supplemental schema was corrected and the original response retained.

The first calibrated Kimi recovery request, `SR-20260801-004`, then received a
provider `429` before any model output. It reported no usage or charge. The
runner initially described the empty-choices response too generically; it now
classifies top-level provider errors before model parsing and can route across
parameter-compatible providers. `SR-20260801-005` used that corrected route and
completed successfully. Neither event is hidden or treated as a model verdict.

Under the study's historical one-shot protocol, both valid reviews remained
supplemental evidence for a human disposition and could not rewrite the frozen
replication result. The prospective policy above instead defines when a new
three-reviewer run can authorize publication after a Fable non-response. The
operating principle is **Replicate to accelerate**: disclose what failed,
correct the process, and preserve enough evidence for others to learn from it.

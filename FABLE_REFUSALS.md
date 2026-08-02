# Fable refusal ledger

This append-only ledger records technical or safeguard refusals before a
substantive NULSPEC peer review. Refusals are process evidence, not scientific
evidence about a paper or replication. Exact provider traces remain in the
private lab archive; this public record removes request/session identifiers and
machine-local context.

## FABLE-REFUSAL-20260801-001

- Study: `260723346` / arXiv `2607.23346v1`
- Attempt: 2026-08-01T16:43:01.590076Z to 2026-08-01T16:43:08.433358Z
- Provider/model: Anthropic / `claude-fable-5`
- Category: `bio`
- Provider state: `refusal` / `api_error`
- Findings returned: **0**
- Charged cost: **$3.224742**
- Packet: `5eabac56ae0d25cecc11a308e669d4de95911e4e3f7c81f533b66eafe9ac53ea` (603,683 bytes)
- Prompt: `182d3718f8c38aef22585ad44c5fd2d44d56e54b21c3772b302322ec9ee9b95d` (605,580 bytes)
- Raw response: `82ccbc735ef4dd8d9b627df993ee9f1e819c7a67e4b493ad4ffc51d9bc24b4c9` (5,118 bytes)
- Publication consequence: Fable HARD_FAIL; no resubmission; invoke the one-pair GLM/Kimi supplemental disposition and otherwise fail closed for human review.

Sanitized provider message:

> API Error: Fable 5's safeguards flagged this message (https://www.anthropic.com/legal/aup). They may flag safe, normal content as well. These measures let us bring you Mythos-level capabilities sooner, and we're working to refine them. Claude Code can't respond to this request with Fable 5.
>
> Try rephrasing the request in a new session or change your model.
>
> Learn more: https://support.claude.com/en/articles/15363606

### Cost components

| Served model | Input | Cache creation | Output | Cost (USD) |
|---|---:|---:|---:|---:|
| `claude-fable-5` | 1 | 242,078 | 8 | $3.026385 |
| `claude-haiku-4-5-20251001` | 198,262 | 0 | 19 | $0.198357 |

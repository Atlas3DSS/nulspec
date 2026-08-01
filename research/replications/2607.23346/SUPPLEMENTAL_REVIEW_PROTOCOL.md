# Supplemental reviewer disposition protocol

Status: retrospective implementation record for the human-issued fallback
rule. This document was written after the provider attempts and must not be
described as a preregistration.

## Trigger and immutable input

Fable's one permitted review ended in a biomedical safeguard refusal before
any substantive finding. Fable is not resubmitted. The human disposition was
to submit the same frozen packet independently to the strongest current GLM and
Kimi models available through OpenRouter. Both requests bind:

- reviewed commit `68188afc7305e5168d33c5278968f7a26b403a40`;
- packet SHA-256
  `5eabac56ae0d25cecc11a308e669d4de95911e4e3f7c81f533b66eafe9ac53ea`;
  and
- prompt SHA-256
  `182d3718f8c38aef22585ad44c5fd2d44d56e54b21c3772b302322ec9ee9b95d`.

The exact dated models were `z-ai/glm-5.2-20260616` and
`moonshotai/kimi-k3-20260715`. Their catalog entries and the queried catalog
snapshot are hash-bound in
`results/supplemental_review_model_manifest.json`.

## Fail-closed rule

Only two independently schema-valid `PASS` decisions from the primary GLM/Kimi
pair can substitute for Fable's technical `HARD_FAIL`. Any `FAIL`,
`HARD_FAIL`, refusal, malformed response, or truncated response leaves the
release at `HARD_FAIL`. There is no retry or tiebreaker. An accidental later
call is preserved and charged but cannot enter the decision.

Supplemental review is release-process evidence. It cannot change a frozen
number, experimental interpretation, or scientific classification. Even a
two-PASS consensus would only make the exact author-email draft eligible for a
separate final human decision; it could never authorize or dispatch email.

## Trace and cost policy

Every request event is append-only, including authentication failures and
ineligible calls. Exact request/response traces remain in the ignored immutable
lab archive for future review-model training. The public export contains
sanitized response content, human labels, usage, costs, hashes, and byte counts
without credentials, request/session identifiers, UUIDs, or private paths.

The machine ledger is `results/external_review_ledger.json`; its training-ready
projection is `results/external_review_training_traces.jsonl`. The Fable refusal
also appears in the repository-root append-only `FABLE_REFUSALS.md` and
`FABLE_REFUSALS.json` ledgers.

## Observed result

The primary GLM content declared `PASS` but supplied the `FAIL`-only next-step
value, so deterministic validation rejected it. Kimi's content also began with
`PASS`, but the response hit its output limit and ended before its JSON object
closed. Neither is a valid structured decision. A later GLM contract-recovery
call returned a valid `PASS`; it is ineligible because it followed the primary
pair. The resulting supplemental disposition is `HARD_FAIL`, with publication
and author-email eligibility blocked pending human review.

import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const ledgerPath = resolve(root, "site-data", "fable-refusals.json");
const markdownPath = resolve(root, "FABLE_REFUSALS.md");
const ledger = JSON.parse(await readFile(ledgerPath, "utf8"));
const markdown = await readFile(markdownPath, "utf8");
const fableRunner = await readFile(
  resolve(root, "extension", "fable_pipeline_critique.py"),
  "utf8",
);
const reviewBackend = await readFile(
  resolve(root, "infra", "multibot", "nulspec_review.py"),
  "utf8",
);
const hierarchyDocs = await readFile(
  resolve(root, "docs", "REVIEW_HIERARCHY.md"),
  "utf8",
);
const errors = [];
const hex64 = /^[0-9a-f]{64}$/;
const fullCommit = /^[0-9a-f]{40}$/;
const refusalId = /^FR-[0-9]{8}-[0-9]{3}$/;
const supplementalId = /^SR-[0-9]{8}-[0-9]{3}$/;
const transportId = /^TR-[0-9]{8}-[0-9]{3}$/;
const privateText =
  /(?:\/home\/|[A-Za-z]:\\|req_[A-Za-z0-9]+|session_id|apiKeySource|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;

function check(condition, message) {
  if (!condition) errors.push(message);
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

check(
  ledger.schema_version === "nulspec-fable-refusal-ledger-v3",
  "unexpected Fable refusal ledger schema",
);
check(Array.isArray(ledger.refusals), "refusals must be an array");
check(ledger.refusals.length > 0, "refusal ledger must not be empty");
check(
  !fableRunner.includes("--historical-single-run") &&
    !fableRunner.includes("--explicit-reissue-of") &&
    !fableRunner.includes("historical_one_time_advisory_pipeline_critique"),
  "Fable runner retains a prohibited single-pipeline invocation path",
);
check(
  fableRunner.includes('required=True,\n        help="required manifest containing exactly ten') &&
    fableRunner.includes("if not 0 < args.max_budget_usd <= 5") &&
    fableRunner.includes('role = "batched_advisory_pipeline_critique"'),
  "Fable runner does not enforce its ten-paper batch and $5 budget boundary",
);
check(
  reviewBackend.includes('RELEASE_REVIEW_SCHEMA = "nulspec-glm-kimi-release-review-v1"') &&
    reviewBackend.includes('raise ReviewPacketError("per-paper release review must not invoke Fable")'),
  "review dashboard does not enforce the GLM/Kimi-only per-paper release boundary",
);
check(
  hierarchyDocs.includes("The historical single-pipeline runner and its reissue flags have been removed.") &&
    !hierarchyDocs.includes("`--historical-single-run` exists"),
  "review hierarchy documentation still exposes a single-pipeline Fable path",
);

const fallbackIds = new Set(
  (ledger.fallback_policy?.models ?? []).map((model) => model.model_id),
);
const fallbackCanonical = new Map(
  (ledger.fallback_policy?.models ?? []).map((model) => [
    model.model_id,
    model.canonical_slug,
  ]),
);
const ids = new Set();
let totalCost = 0;
let totalFindings = 0;
let studiesDelayed = 0;
let fallbackAttemptCount = 0;
let fallbackCost = 0;
let fallbackTransportEventCount = 0;
let validFallbackCount = 0;
const publicReviewText = [];
for (const [index, entry] of (ledger.refusals ?? []).entries()) {
  const label = `refusals[${index}]`;
  check(refusalId.test(entry.id), `${label} has an invalid stable ID`);
  check(!ids.has(entry.id), `${label} duplicates ${entry.id}`);
  ids.add(entry.id);
  check(entry.provider === "Anthropic", `${label} must identify the provider`);
  check(entry.product === "Fable 5", `${label} must identify the product`);
  check(
    entry.refusal?.stop_reason === "refusal" &&
      entry.refusal?.terminal_reason === "api_error",
    `${label} does not preserve the refusal terminal state`,
  );
  check(
    entry.refusal?.response_class === "charged_guardrail_nonresponse" &&
      entry.refusal?.decision_weight === 0 &&
      entry.refusal?.scientific_hard_fail === false &&
      entry.refusal?.historical_gate_classification ===
        "technical_hard_fail_under_frozen_v1_protocol",
    `${label} does not distinguish the non-response from a scientific HARD_FAIL`,
  );
  check(
    Number.isInteger(entry.refusal?.substantive_findings_returned) &&
      entry.refusal.substantive_findings_returned >= 0,
    `${label} has an invalid finding count`,
  );
  check(
    typeof entry.refusal?.provider_message === "string" &&
      entry.refusal.provider_message.includes("They may flag safe, normal content as well"),
    `${label} does not preserve the provider acknowledgement`,
  );
  check(
    entry.impact?.review_work_duplicated === true &&
      entry.impact?.publication_gate === "blocked_pending_human_review",
    `${label} does not record the review and publication consequence`,
  );
  check(
    Number.isFinite(entry.usage?.total_charged_usd) &&
      entry.usage.total_charged_usd > 0,
    `${label} has no positive provider charge`,
  );
  check(
    Math.abs(
      entry.usage.total_charged_usd -
        entry.usage.fable_charged_usd -
        entry.usage.support_model_charged_usd,
    ) < 1e-9,
    `${label} charge components do not equal the total`,
  );
  check(
    fullCommit.test(entry.request?.reviewed_commit ?? ""),
    `${label} reviewed commit is invalid`,
  );
  for (const [name, value] of Object.entries({
    packet: entry.request?.packet_sha256,
    prompt: entry.request?.prompt_sha256,
    raw_response: entry.evidence?.raw_response_sha256,
    stderr: entry.evidence?.stderr_sha256,
  })) {
    check(hex64.test(value ?? ""), `${label} has an invalid ${name} SHA-256`);
  }
  check(
    entry.evidence?.raw_response_byte_count > 0 &&
      entry.evidence?.stderr_byte_count === 0,
    `${label} has invalid retained-trace byte counts`,
  );
  check(
    entry.evidence?.raw_trace_public === false,
    `${label} must not claim that the unredacted trace is public`,
  );
  check(
    entry.evidence?.structured_result_url?.startsWith(
      "https://github.com/Atlas3DSS/nulspec/blob/",
    ) &&
      entry.evidence?.human_record_url?.startsWith(
        "https://github.com/Atlas3DSS/nulspec/blob/",
      ),
    `${label} evidence links are not immutable repository links`,
  );

  const supplemental = entry.supplemental_reviews;
  check(
    supplemental?.status === "four_valid_reviews_two_models" &&
      Array.isArray(supplemental?.attempts),
    `${label} has no supplemental-review record`,
  );
  check(
    Array.isArray(supplemental?.transport_records) &&
      supplemental.transport_records.length > 0,
    `${label} does not preserve no-cost transport events`,
  );
  const transportIds = new Set();
  for (const [recordIndex, record] of (
    supplemental?.transport_records ?? []
  ).entries()) {
    const recordLabel = `${label}.supplemental_reviews.transport_records[${recordIndex}]`;
    check(transportId.test(record.event_id), `${recordLabel} has an invalid ID`);
    check(!transportIds.has(record.event_id), `${recordLabel} duplicates its ID`);
    transportIds.add(record.event_id);
    check(
      Number.isInteger(record.count) && record.count > 0 && record.charged_usd === 0,
      `${recordLabel} has an invalid request count or charge`,
    );
    check(
      typeof record.responsibility === "string" &&
        typeof record.resolution === "string" &&
        record.responsibility.length > 20 &&
        record.resolution.length > 20,
      `${recordLabel} does not attribute and resolve the event`,
    );
    if ("raw_response_sha256" in record) {
      check(
        hex64.test(record.raw_response_sha256) &&
          Number.isInteger(record.raw_response_byte_count) &&
          record.raw_response_byte_count > 0,
        `${recordLabel} has invalid raw-response provenance`,
      );
    }
    fallbackTransportEventCount += record.count;
  }
  const attemptIds = new Set();
  let entryFallbackCost = 0;
  let entryValidCount = 0;
  for (const [attemptIndex, attempt] of (supplemental?.attempts ?? []).entries()) {
    const attemptLabel = `${label}.supplemental_reviews.attempts[${attemptIndex}]`;
    check(
      supplementalId.test(attempt.attempt_id),
      `${attemptLabel} has an invalid stable ID`,
    );
    check(
      !attemptIds.has(attempt.attempt_id),
      `${attemptLabel} duplicates ${attempt.attempt_id}`,
    );
    attemptIds.add(attempt.attempt_id);
    check(
      fallbackIds.has(attempt.model_id),
      `${attemptLabel} does not use a pinned fallback model`,
    );
    check(
      fallbackCanonical.get(attempt.model_id) === attempt.canonical_slug,
      `${attemptLabel} does not preserve the pinned canonical model revision`,
    );
    check(
      Number.isFinite(attempt.charged_usd) && attempt.charged_usd > 0,
      `${attemptLabel} has no positive recorded charge`,
    );
    check(
      Number.isInteger(attempt.prompt_tokens) && attempt.prompt_tokens > 0 &&
        Number.isInteger(attempt.completion_tokens) && attempt.completion_tokens > 0,
      `${attemptLabel} has invalid token usage`,
    );
    check(
      Number.isInteger(attempt.raw_response_byte_count) &&
        attempt.raw_response_byte_count > 0 &&
        hex64.test(attempt.raw_response_sha256 ?? ""),
      `${attemptLabel} has invalid raw-response provenance`,
    );
    check(
      typeof attempt.finding === "string" && attempt.finding.length > 40,
      `${attemptLabel} does not explain its disposition`,
    );
    entryFallbackCost += attempt.charged_usd;
    fallbackAttemptCount += 1;

    if (attempt.status === "completed_valid") {
      entryValidCount += 1;
      validFallbackCount += 1;
      check(
        attempt.indicated_verdict === "PASS" &&
          attempt.passed_check_count === 8 &&
          attempt.total_check_count === 8,
        `${attemptLabel} is not a complete eight-check PASS`,
      );
      check(
        typeof attempt.public_result_url === "string" &&
          attempt.public_result_url.startsWith(`/fable-refusals/${entry.id}/`),
        `${attemptLabel} has an invalid public result URL`,
      );
      const resultPath = resolve(root, "public", attempt.public_result_url.slice(1));
      const resultBytes = await readFile(resultPath);
      const resultText = resultBytes.toString("utf8");
      const result = JSON.parse(resultText);
      publicReviewText.push(resultText);
      check(
        resultBytes.byteLength === attempt.public_result_byte_count,
        `${attemptLabel} public result byte count does not match`,
      );
      check(
        sha256(resultBytes) === attempt.public_result_sha256,
        `${attemptLabel} public result SHA-256 does not match`,
      );
      check(
        [
          "nulspec-openrouter-supplemental-review-v2",
          "nulspec-openrouter-supplemental-review-v3",
          "nulspec-openrouter-supplemental-review-v4",
        ].includes(result.schema_version) &&
          result.decision?.verdict === "PASS" &&
          Array.isArray(result.decision?.checks) &&
          result.decision.checks.length === 8 &&
          result.decision.checks.every((row) => row.status === "PASS") &&
          Array.isArray(result.decision?.action_items) &&
          result.decision.action_items.length === 0,
        `${attemptLabel} public result is not the validated PASS decision`,
      );
      check(
        result.release_control?.publication_authorized === false &&
          result.release_control?.author_email_dispatch_authorized === false &&
          result.release_control?.human_disposition_required === true,
        `${attemptLabel} public result bypasses human release control`,
      );
    } else {
      check(
        !attempt.public_result_url,
        `${attemptLabel} exposes a rejected or incomplete result as validated`,
      );
    }
  }
  check(
    Math.abs(supplemental?.total_charged_usd - entryFallbackCost) < 1e-9,
    `${label} supplemental charge does not equal its attempt charges`,
  );
  check(entryValidCount === 4, `${label} must identify four valid review outputs`);
  const validGlmAttempt = supplemental?.attempts?.find(
    (attempt) =>
      attempt.status === "completed_valid" && attempt.model_id === "z-ai/glm-5.2",
  );
  const validKimiAttempt = supplemental?.attempts?.find(
    (attempt) =>
      attempt.status === "completed_valid" &&
      attempt.model_id === "moonshotai/kimi-k3",
  );
  check(
    Math.abs(
      supplemental?.anthropic_to_valid_glm_cost_ratio -
        Math.round(
          (entry.usage.total_charged_usd / validGlmAttempt?.charged_usd) * 100,
        ) /
          100,
    ) < 1e-9,
    `${label} Anthropic-to-valid-GLM cost ratio is incorrect`,
  );
  check(
    Math.abs(
      supplemental?.anthropic_to_valid_kimi_cost_ratio -
        Math.round(
          (entry.usage.total_charged_usd / validKimiAttempt?.charged_usd) * 100,
        ) /
          100,
    ) < 1e-9,
    `${label} Anthropic-to-valid-Kimi cost ratio is incorrect`,
  );
  const highDepthGlm = supplemental?.attempts?.find(
    (attempt) => attempt.comparison_label === "glm-high-max-output",
  );
  const highDepthKimi = supplemental?.attempts?.find(
    (attempt) => attempt.comparison_label === "kimi-high-max-output",
  );
  check(
    highDepthGlm?.reasoning_effort === "high" &&
      highDepthGlm.max_tokens === 131072 &&
      supplemental?.anthropic_to_high_depth_glm_cost_ratio ===
        Math.round((entry.usage.total_charged_usd / highDepthGlm.charged_usd) * 100) /
          100,
    `${label} high-depth GLM comparison is incomplete`,
  );
  check(
    highDepthKimi?.reasoning_effort === "high" &&
      highDepthKimi.max_tokens === 870000 &&
      supplemental?.anthropic_to_high_depth_kimi_cost_ratio ===
        Math.round((entry.usage.total_charged_usd / highDepthKimi.charged_usd) * 100) /
          100,
    `${label} high-depth Kimi comparison is incomplete`,
  );

  check(
    Array.isArray(supplemental?.comparison_sets) &&
      supplemental.comparison_sets.length === 1,
    `${label} does not retain the reviewer-depth comparison set`,
  );
  for (const comparison of supplemental?.comparison_sets ?? []) {
    check(
      comparison.comparison_group === "reviewer-depth-20260801" &&
        comparison.attempt_ids?.length === 3,
      `${label} comparison group is incomplete`,
    );
    const comparisonPath = resolve(
      root,
      "public",
      comparison.public_index_url.slice(1),
    );
    const comparisonBytes = await readFile(comparisonPath);
    const comparisonText = comparisonBytes.toString("utf8");
    const comparisonIndex = JSON.parse(comparisonText);
    publicReviewText.push(comparisonText);
    check(
      comparisonBytes.byteLength === comparison.public_index_byte_count &&
        sha256(comparisonBytes) === comparison.public_index_sha256,
      `${label} comparison index provenance does not match`,
    );
    check(
      comparisonIndex.schema_version === "nulspec-reviewer-depth-comparison-v1" &&
        comparisonIndex.comparison_group === comparison.comparison_group &&
        Array.isArray(comparisonIndex.reviews) &&
        comparisonIndex.reviews.length === 3 &&
        comparisonIndex.reviews.every(
          (review) =>
            review.verdict === "PASS" &&
            review.passed_check_count === 8 &&
            review.action_item_count === 0,
        ),
      `${label} comparison index is invalid`,
    );
  }
  fallbackCost += entryFallbackCost;
  check(markdown.includes(entry.id), `${label} is absent from FABLE_REFUSALS.md`);
  check(
    markdown.includes(entry.evidence.raw_response_sha256),
    `${label} raw-response digest is absent from FABLE_REFUSALS.md`,
  );
  totalCost += entry.usage.total_charged_usd;
  totalFindings += entry.refusal.substantive_findings_returned;
  studiesDelayed += entry.impact.publication_gate === "blocked_pending_human_review" ? 1 : 0;
}

check(
  ledger.summary?.refusal_count === ledger.refusals.length,
  "summary refusal count does not match the ledger",
);
check(
  ledger.summary?.substantive_review_count === totalFindings,
  "summary finding count does not match the ledger",
);
check(
  Math.abs(ledger.summary?.total_charged_usd - totalCost) < 1e-9,
  "summary charge does not match the ledger",
);
check(
  ledger.summary?.studies_delayed === studiesDelayed,
  "summary delayed-study count does not match the ledger",
);
check(
  ledger.summary?.fallback_attempt_count === fallbackAttemptCount,
  "summary fallback-attempt count does not match the ledger",
);
check(
  ledger.summary?.fallback_transport_event_count === fallbackTransportEventCount,
  "summary fallback-transport count does not match the ledger",
);
check(
  Math.abs(ledger.summary?.fallback_total_charged_usd - fallbackCost) < 1e-9,
  "summary fallback charge does not match the ledger",
);
check(
  ledger.summary?.fallback_valid_review_count === validFallbackCount,
  "summary valid fallback-review count does not match the ledger",
);
check(
  ledger.summary?.fallback_distinct_valid_model_count === 2,
  "summary distinct valid-model count is incorrect",
);
check(
  ledger.summary?.reviewer_depth_comparison_count === 3,
  "summary reviewer-depth comparison count is incorrect",
);
check(
  ledger.summary?.zero_weight_fable_nonresponse_count === 1,
  "summary zero-weight Fable non-response count is incorrect",
);

const reviewPolicy = ledger.review_policy;
check(
  reviewPolicy?.policy_version === "nulspec-glm-kimi-human-release-gate-v2" &&
    reviewPolicy?.active_reviewers_only === true &&
    Array.isArray(reviewPolicy?.reviewers) &&
    reviewPolicy.reviewers.map((row) => row.reviewer_family).join(",") ===
      "GLM,Kimi",
  "active two-reviewer policy is incomplete or reordered",
);
check(
  reviewPolicy?.decision_rule?.glm_kimi_unanimous_pass_satisfies_model_gate ===
      true &&
    reviewPolicy?.decision_rule
      ?.malformed_missing_nonpass_or_disagreeing_reviews_block === true &&
    reviewPolicy?.decision_rule?.codex_may_relax_failed_model_gate === false &&
    reviewPolicy?.decision_rule?.human_publication_approval_required === true &&
    reviewPolicy?.decision_rule?.author_email_human_approval_required === true,
  "active two-reviewer decision rule is incomplete",
);
check(
  reviewPolicy?.decision_rule?.fable_active_decision_weight === 0 &&
    reviewPolicy?.fable_batch_policy?.active_per_paper_invocation_allowed ===
      false &&
    reviewPolicy?.fable_batch_policy?.eligible_completed_papers === 10 &&
    reviewPolicy?.fable_batch_policy?.random_sample_size === 3 &&
    reviewPolicy?.fable_batch_policy?.invocations_per_batch === 1 &&
    reviewPolicy?.fable_batch_policy?.automatic_retry_allowed === false &&
    reviewPolicy?.fable_batch_policy?.decision_weight === 0 &&
    reviewPolicy?.fable_batch_policy?.publication_authority === false &&
    reviewPolicy?.fable_batch_policy?.email_authority === false,
  "batch-only Fable policy is incomplete",
);
check(
  reviewPolicy?.trace_policy?.raw_attempts_retained === true &&
    reviewPolicy?.trace_policy?.failed_attempts_retained === true &&
    reviewPolicy?.trace_policy?.silent_retry_allowed === false &&
    reviewPolicy?.trace_policy?.public_projection_excludes_private_identifiers ===
      true,
  "active review trace policy is incomplete",
);

const historicalPolicy = ledger.historical_review_policy;
check(
  historicalPolicy?.policy_version === "nulspec-three-reviewer-release-gate-v1" &&
    historicalPolicy?.superseded_by === reviewPolicy?.policy_version &&
    historicalPolicy?.reviewers?.map((row) => row.reviewer_family).join(",") ===
      "Fable,GLM,Kimi",
  "historical three-reviewer policy was not preserved",
);

check(
  ledger.fallback_policy?.human_disposition_required === true &&
    ledger.fallback_policy?.historical_only === true &&
    ledger.fallback_policy?.preferred_review_count === 2 &&
    ledger.fallback_policy?.minimum_successful_reviews === 1,
  "fallback review policy is incomplete",
);
check(
  Array.isArray(ledger.fallback_policy?.models) &&
    ledger.fallback_policy.models.length === 2,
  "fallback policy must pin GLM and Kimi",
);
check(fallbackIds.has("z-ai/glm-5.2"), "GLM fallback model is not pinned");
check(fallbackIds.has("moonshotai/kimi-k3"), "Kimi fallback model is not pinned");
for (const model of ledger.fallback_policy?.models ?? []) {
  check(
    typeof model.canonical_slug === "string" &&
      model.canonical_slug !== model.model_id &&
      model.context_length >= 1_000_000,
    `fallback model is not pinned to a dated large-context revision: ${model.model_id}`,
  );
}

const publicText = `${JSON.stringify(ledger)}\n${markdown}\n${publicReviewText.join("\n")}`;
check(!privateText.test(publicText), "public refusal ledger contains a private identifier");
check(
  markdown.includes("Anthropic charged **$3.224742**") &&
    markdown.includes("wasted reviewer time and research") &&
    markdown.includes("68.99 times") &&
    markdown.includes("6.04 times") &&
    markdown.includes("20.46 times") &&
    markdown.includes("4.34 times") &&
    markdown.includes("8ef776f6948c5cf69ed9be6dba4f93a2a011479c32cd5249d905a09daab6a673") &&
    markdown.includes("8264578f7857cf171e06a1ed57230f164895dc083f76b59bee5dcf95a9863063") &&
    markdown.includes("f02f6790ec3978a69cef1cd71c0935d0523cae04df78ce4baca9742db2bfc90d") &&
    markdown.includes("b03ef4d2bd557d1800e0fa0358188a1e8c8b2ded3ed2db843a8dfc8ec4691fd4") &&
    markdown.includes("This was a harness configuration error, not a Kimi scientific failure") &&
    markdown.includes("decision weight is **zero**") &&
    markdown.includes("scientific `HARD_FAIL`") &&
    markdown.includes("Fable is not requested for per-paper review") &&
    markdown.includes("one Fable invocation reviews three reproducibly selected") &&
    markdown.includes("Replicate to accelerate"),
  "Markdown ledger does not state the recorded financial and reviewer impact",
);

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(
    `validated ${ledger.refusals.length} Fable refusal(s): ` +
      `${totalFindings} findings, $${totalCost.toFixed(6)} charged`,
  );
}

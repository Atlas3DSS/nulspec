import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const ledgerPath = resolve(
  process.cwd(),
  "site-data/public-archive/data/selection-ledger.json",
);
const ledgerText = await readFile(ledgerPath, "utf8");
const ledger = JSON.parse(ledgerText);
const decisions = new Set(["completed", "selected", "deferred", "rejected"]);
const feasibilityClasses = new Set(["exact", "compatible", "infeasible"]);
const costStates = new Set(["not_started", "in_progress", "audit_pending", "final"]);
const privateText = new RegExp(
  String.raw`(?:/` +
    String.raw`home/|/Users/|[A-Za-z]:\\Users\\|BEGIN [A-Z ]*PRIVATE KEY|` +
    String.raw`(?:api|access|auth)[_-]?token\s*[=:]|GPU-[0-9a-f-]{36}|` +
    String.raw`[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|palworld|MonkeyPC|wtatum84)`,
  "i",
);

const fail = (message) => {
  throw new Error(`selection ledger validation failed: ${message}`);
};
const isObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const finiteNonNegative = (value) =>
  typeof value === "number" && Number.isFinite(value) && value >= 0;
const nonEmptyString = (value, maximumLength = 2_000) =>
  typeof value === "string" &&
  value.trim().length > 0 &&
  value.length <= maximumLength;
const stringList = (value, maximumItems = 20) =>
  Array.isArray(value) &&
  value.length <= maximumItems &&
  value.every((item) => nonEmptyString(item));

if (privateText.test(ledgerText)) fail("public snapshot contains private infrastructure text");
if (!isObject(ledger) || ledger.schema_version !== "nulspec-selection-ledger-v1") {
  fail("schema_version must be nulspec-selection-ledger-v1");
}
if (ledger.methodology_version !== "1.0.0") fail("unexpected methodology version");
for (const [key, value] of Object.entries({
  as_of_utc: ledger.as_of_utc,
  policy_effective_at_utc: ledger.policy_effective_at_utc,
})) {
  if (!nonEmptyString(value, 40) || Number.isNaN(Date.parse(value))) {
    fail(`${key} must be a valid timestamp`);
  }
}
if (
  !isObject(ledger.scope) ||
  ledger.scope.active_domain !== "Computational machine learning" ||
  !nonEmptyString(ledger.scope.expansion_policy)
) {
  fail("active program scope is missing or malformed");
}
if (
  !isObject(ledger.randomized_selection) ||
  ledger.randomized_selection.starts_per_block !== 3 ||
  ledger.randomized_selection.random_starts_per_block !== 1 ||
  !nonEmptyString(ledger.randomized_selection.pool_rule) ||
  !nonEmptyString(ledger.randomized_selection.draw_rule) ||
  !nonEmptyString(ledger.randomized_selection.replacement_rule)
) {
  fail("prospective randomized-selection contract is missing or malformed");
}
if (!Array.isArray(ledger.eligibility_rules) || ledger.eligibility_rules.length < 5) {
  fail("at least five eligibility rules are required");
}
const eligibilityIds = new Set();
for (const [index, rule] of ledger.eligibility_rules.entries()) {
  if (
    !isObject(rule) ||
    !/^EL-[0-9]{2}$/.test(rule.id ?? "") ||
    eligibilityIds.has(rule.id) ||
    !nonEmptyString(rule.label, 120) ||
    !nonEmptyString(rule.rule)
  ) {
    fail(`eligibility_rules[${index}] is invalid`);
  }
  eligibilityIds.add(rule.id);
}
if (!Array.isArray(ledger.candidates) || ledger.candidates.length === 0) {
  fail("candidate list must not be empty");
}

const ids = new Set();
const counts = { completed: 0, selected: 0, deferred: 0, rejected: 0 };
let quotaCounted = 0;
for (const [index, candidate] of ledger.candidates.entries()) {
  const label = `candidates[${index}]`;
  if (!isObject(candidate)) fail(`${label} must be an object`);
  if (!/^arxiv:[0-9]{4}\.[0-9]{5}$/.test(candidate.paper_id ?? "")) {
    fail(`${label}.paper_id is invalid`);
  }
  if (ids.has(candidate.paper_id)) fail(`${label}.paper_id is duplicated`);
  ids.add(candidate.paper_id);
  if (!nonEmptyString(candidate.title, 500)) fail(`${label}.title is invalid`);
  if (candidate.url !== `https://arxiv.org/abs/${candidate.paper_id.slice(6)}`) {
    fail(`${label}.url is not the canonical arXiv URL`);
  }
  if (Number.isNaN(Date.parse(candidate.received_at_utc))) {
    fail(`${label}.received_at_utc is invalid`);
  }
  if (!stringList(candidate.claim_scope) || candidate.claim_scope.length === 0) {
    fail(`${label}.claim_scope is invalid`);
  }
  if (!decisions.has(candidate.decision)) fail(`${label}.decision is invalid`);
  counts[candidate.decision] += 1;
  if (
    candidate.intake_cohort !== "pre-policy-convenience-v1" ||
    candidate.selection_method !== "priority_pre_policy"
  ) {
    fail(`${label} must preserve its pre-policy selection provenance`);
  }
  if (!stringList(candidate.why_selected) || candidate.why_selected.length === 0) {
    fail(`${label}.why_selected is invalid`);
  }
  if (!stringList(candidate.why_not_started_or_rejected)) {
    fail(`${label}.why_not_started_or_rejected is invalid`);
  }
  if (
    ["deferred", "rejected"].includes(candidate.decision) &&
    candidate.why_not_started_or_rejected.length === 0
  ) {
    fail(`${label} lacks its deferral or rejection reason`);
  }

  const gpu = candidate.estimate?.gpu_hours;
  if (
    !isObject(candidate.estimate) ||
    !isObject(gpu) ||
    !finiteNonNegative(gpu.min) ||
    !finiteNonNegative(gpu.likely) ||
    !finiteNonNegative(gpu.max) ||
    gpu.min > gpu.likely ||
    gpu.likely > gpu.max ||
    !finiteNonNegative(candidate.estimate.human_hours) ||
    !feasibilityClasses.has(candidate.estimate.feasibility?.class) ||
    !nonEmptyString(candidate.estimate.feasibility?.explanation)
  ) {
    fail(`${label}.estimate is invalid`);
  }

  const process = candidate.process;
  const processKeys = [
    "protocol_frozen",
    "terminal_artifact_valid",
    "automated_consistency_audit_complete",
    "human_publication_approved",
    "published",
    "quota_counted",
  ];
  if (
    !isObject(process) ||
    processKeys.some((key) => typeof process[key] !== "boolean")
  ) {
    fail(`${label}.process is invalid`);
  }
  if (
    process.quota_counted &&
    (!process.protocol_frozen ||
      !process.terminal_artifact_valid ||
      !process.human_publication_approved ||
      !process.published)
  ) {
    fail(`${label} counts toward quota without a finished publication contract`);
  }
  if (process.quota_counted) quotaCounted += 1;

  const cost = candidate.actual_cost;
  if (
    !isObject(cost) ||
    !costStates.has(cost.status) ||
    !nonEmptyString(cost.note) ||
    !["gpu_hours", "human_hours", "direct_cost_usd"].every(
      (key) => cost[key] === null || finiteNonNegative(cost[key]),
    )
  ) {
    fail(`${label}.actual_cost is invalid`);
  }
  if (
    cost.status === "final" &&
    [cost.gpu_hours, cost.human_hours, cost.direct_cost_usd].some(
      (value) => !finiteNonNegative(value),
    )
  ) {
    fail(`${label} has a final cost state with incomplete values`);
  }
  if (
    cost.status === "not_started" &&
    [cost.gpu_hours, cost.human_hours, cost.direct_cost_usd].some(
      (value) => value !== 0,
    )
  ) {
    fail(`${label} has nonzero cost while marked not started`);
  }
}

const expectedSummary = {
  considered: ledger.candidates.length,
  ...counts,
  quota_counted: quotaCounted,
};
for (const [key, value] of Object.entries(expectedSummary)) {
  if (ledger.summary?.[key] !== value) fail(`summary.${key} does not match candidates`);
}
if (!Number.isInteger(ledger.summary?.quota_target) || ledger.summary.quota_target < 1) {
  fail("summary.quota_target is invalid");
}

console.log(
  `Validated selection ledger: ${ledger.candidates.length} considered, ` +
    `${quotaCounted}/${ledger.summary.quota_target} quota-counted.`,
);

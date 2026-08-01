import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { basename, resolve, sep } from "node:path";

const root = process.cwd();
const publicationsDirectory = resolve(root, "site-data/publications");
const publicDirectory = resolve(root, "public");
const terminalExecutions = new Set([
  "completed",
  "completed_with_recovery",
  "failed",
  "aborted",
  "inconclusive_terminal",
]);
const verdicts = new Set(["MATCH", "DIVERGES", "INCONCLUSIVE"]);
const classifications = new Set([
  "REPRODUCED",
  "PARTIALLY_REPRODUCED",
  "NOT_REPRODUCED",
  "INCONCLUSIVE",
]);
const provenance = new Set(["EXACT", "COMPAT"]);
const requiredArtifactRoles = new Set([
  "result_summary",
  "full_report",
  "machine_analysis",
  "extension_roadmap",
  "website_handoff",
  "frontend_handoff",
]);
const accuracySchema = "nulspec-classification-accuracy-site-v1";
const accuracyHandoffSchema =
  "nulspec-classification-accuracy-study-handoff-v1";
const requiredAccuracyArtifactRoles = new Set([
  "result_summary",
  "full_report",
  "machine_analysis",
  "primary_figure",
  "frozen_primary_protocol",
  "extension_roadmap",
  "frontend_handoff",
  "upstream_audit",
  "posthoc_register",
  "posthoc_loss_contract",
  "executed_code_manifest",
]);
const armRouteComponent = /^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$/;
const privateText = new RegExp(
  String.raw`(?:/` +
    String.raw`home/|/Users/|[A-Za-z]:\\Users\\|BEGIN [A-Z ]*PRIVATE KEY|` +
    String.raw`(?:api|access|auth)[_-]?token\s*[=:]|GPU-[0-9a-f-]{36}|` +
    String.raw`[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|palworld|MonkeyPC|wtatum84)`,
  "i",
);

const digest = (value) => createHash("sha256").update(value).digest("hex");
const fail = (studyId, message) => {
  throw new Error(`study-${studyId} validation failed: ${message}`);
};
const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const safeRelative = (value) =>
  typeof value === "string" &&
  value.length > 0 &&
  !value.startsWith(".") &&
  !value.startsWith("/") &&
  !value.split("/").includes("..");
const finiteNumber = (value) => typeof value === "number" && Number.isFinite(value);
const validInterval = (value) =>
  Array.isArray(value) &&
  value.length === 2 &&
  finiteNumber(value[0]) &&
  finiteNumber(value[1]) &&
  value[0] <= value[1];
const detailRoutes = new Set();

async function validateAccuracyBundle(bundle, bundleBytes, file, studyId) {
  if (bundle.publication_status !== "ready") fail(studyId, "bundle is not ready");
  if (!/^[0-9]{3,}$/.test(studyId)) fail(studyId, "invalid study id");
  if (file !== `study-${studyId}.json`) fail(studyId, "filename does not match study id");
  if (bundle.study?.arxiv_url !== `https://arxiv.org/abs/${bundle.study?.arxiv_id}`) {
    fail(studyId, "paper URL is not canonical arXiv");
  }
  if (!/^[0-9a-f]{40}$/.test(bundle.source?.evidence_revision ?? "")) {
    fail(studyId, "evidence revision is not a full Git SHA");
  }
  if (
    bundle.source?.handoff_schema_version !== accuracyHandoffSchema ||
    bundle.source?.source_publication_status !==
      "blocked_pending_typed_accuracy_frontend" ||
    !/^[0-9a-f]{64}$/.test(bundle.source?.handoff_sha256 ?? "") ||
    !safeRelative(bundle.source?.handoff_path) ||
    !Number.isInteger(bundle.source?.declared_artifact_count) ||
    bundle.source.declared_artifact_count < requiredAccuracyArtifactRoles.size
  ) {
    fail(studyId, "source handoff provenance is missing or malformed");
  }
  const handoffPath = resolve(root, bundle.source.handoff_path);
  if (!handoffPath.startsWith(`${root}${sep}`)) {
    fail(studyId, "source handoff path escaped repository root");
  }
  const handoffBytes = await readFile(handoffPath);
  if (digest(handoffBytes) !== bundle.source.handoff_sha256) {
    fail(studyId, "source handoff digest mismatch");
  }

  if (
    bundle.classification?.replication_outcome !== "not_replicated" ||
    bundle.classification?.underlying_method_claim !== "inconclusive" ||
    typeof bundle.classification?.rationale !== "string" ||
    bundle.classification.rationale.trim().length === 0
  ) {
    fail(studyId, "frozen study classifications are missing or malformed");
  }
  if (
    bundle.metrics_schema?.id !== "sprkd_trial_accuracy_v1" ||
    bundle.metrics_schema?.primary_unit !== "percent_accuracy" ||
    bundle.metrics_schema?.primary_estimator !==
      "final_sample_weighted_full_validation_accuracy" ||
    bundle.metrics_schema?.not_prompt_bootstrap !== true ||
    bundle.metrics_schema?.not_equivalence_test !== true ||
    typeof bundle.metrics_schema?.uncertainty !== "string" ||
    !bundle.metrics_schema.uncertainty.includes("five independent training seeds")
  ) {
    fail(studyId, "typed classification-accuracy contract is malformed");
  }

  const runs = bundle.primary?.runs;
  const metrics = bundle.primary?.metrics;
  const comparisons = bundle.primary?.comparisons;
  if (!Array.isArray(runs) || runs.length !== 5) {
    fail(studyId, "publication must contain five frozen runs");
  }
  if (!isObject(metrics) || !isObject(comparisons)) {
    fail(studyId, "primary metrics or comparisons are missing");
  }
  const requiredMetrics = [
    "control_student",
    "control_teacher",
    "exact_public_response_kd",
    "exact_public_sprkd",
    "paper_intent_response_kd",
    "paper_intent_sprkd",
    "weak_teacher",
  ];
  for (const key of requiredMetrics) {
    const metric = metrics[key];
    const observed = metric?.observed;
    if (
      !isObject(metric) ||
      !isObject(observed) ||
      observed.unit !== "percent_accuracy" ||
      observed.estimator !== "final_sample_weighted_full_validation_accuracy" ||
      observed.n_training_seeds !== 5 ||
      !finiteNumber(observed.mean) ||
      !finiteNumber(observed.sample_sd) ||
      !validInterval(observed.descriptive_t95_interval) ||
      !Array.isArray(observed.per_seed) ||
      observed.per_seed.length !== 5 ||
      !observed.per_seed.every(finiteNumber)
    ) {
      fail(studyId, `invalid accuracy metric ${key}`);
    }
  }

  const completion = bundle.completion;
  if (
    completion?.registered_runs !== runs.length ||
    completion?.terminal_runs !== runs.length ||
    completion?.claim_ready_runs !== runs.length ||
    !isObject(completion?.gates) ||
    !Object.values(completion.gates).every((value) => value === true) ||
    completion.gates.typed_accuracy_frontend_complete !== true
  ) {
    fail(studyId, "ready-state run counts or gates are not closed");
  }
  if (
    bundle.frozen_primary_result?.registered_runs !== runs.length ||
    bundle.frozen_primary_result?.claim_ready_runs !== runs.length ||
    bundle.frozen_primary_result?.may_be_rewritten_by_extension !== false
  ) {
    fail(studyId, "frozen primary result does not match completed runs");
  }
  if (
    bundle.routes?.study !== `/studies/${studyId}` ||
    !Array.isArray(bundle.routes?.arms) ||
    bundle.routes.arms.length !== runs.length
  ) {
    fail(studyId, "canonical route contract is malformed");
  }

  const runIds = new Set();
  const seeds = new Set();
  for (const run of runs) {
    const detailRoute = `/studies/${studyId}/arms/${run?.run_id}`;
    if (
      !isObject(run) ||
      !armRouteComponent.test(run.run_id ?? "") ||
      runIds.has(run.run_id) ||
      !Number.isInteger(run.seed) ||
      seeds.has(run.seed) ||
      run.run_id !== `seed-${run.seed}` ||
      run.route !== detailRoute ||
      !bundle.routes.arms.includes(detailRoute) ||
      detailRoutes.has(detailRoute)
    ) {
      fail(studyId, `invalid or duplicate frozen run ${run?.run_id ?? "unknown"}`);
    }
    runIds.add(run.run_id);
    seeds.add(run.seed);
    detailRoutes.add(detailRoute);
    if (
      run.integrity?.status !== "passed" ||
      !Number.isInteger(run.integrity?.n_validation_targets) ||
      run.integrity.n_validation_targets < 1 ||
      !isObject(run.models) ||
      !isObject(run.metrics) ||
      !isObject(run.comparisons)
    ) {
      fail(studyId, `nonterminal or incomplete run ${run.run_id}`);
    }
    for (const key of [
      "complete_sha256",
      "config_sha256",
      "predictions_sha256",
      "split_indices_sha256",
      "validation_indices_sha256",
    ]) {
      if (!/^[0-9a-f]{64}$/.test(run.integrity[key] ?? "")) {
        fail(studyId, `invalid ${key} at ${run.run_id}`);
      }
    }
    if ("verdict" in run || "classification" in run) {
      fail(studyId, `single-seed run has an impermissible verdict at ${run.run_id}`);
    }
  }
  if ([0, 1, 2, 3, 4].some((seed) => !seeds.has(seed))) {
    fail(studyId, "frozen seed set is not exactly 0 through 4");
  }

  const extension = bundle.extension_vote;
  if (
    extension?.button_label !== "Vote to extend this paper" ||
    typeof extension?.question !== "string" ||
    !Array.isArray(extension?.choices) ||
    extension.choices.length !== 6 ||
    new Set(extension.choices.map((choice) => choice?.id)).size !== 6 ||
    extension.effect !==
      "Schedules new evidence and never rewrites the frozen result."
  ) {
    fail(studyId, "extension vote contract is missing or malformed");
  }
  if (
    !isObject(bundle.diagnostics?.posthoc_loss_contract) ||
    !bundle.diagnostics.posthoc_loss_contract.scope
      ?.toLowerCase()
      .includes("post-hoc") ||
    !isObject(bundle.diagnostics.posthoc_loss_contract.models)
  ) {
    fail(studyId, "post-hoc loss-contract diagnostic is not separately labeled");
  }

  if (!Array.isArray(bundle.artifacts)) fail(studyId, "artifacts are missing");
  const roles = new Set();
  const publicPaths = new Set();
  for (const artifact of bundle.artifacts) {
    if (!isObject(artifact) || roles.has(artifact.role)) {
      fail(studyId, `missing or duplicate artifact role ${artifact?.role}`);
    }
    roles.add(artifact.role);
    if (
      !safeRelative(artifact.path) ||
      !safeRelative(artifact.public_path) ||
      !artifact.public_path.startsWith(`studies/${studyId}/artifacts/`) ||
      publicPaths.has(artifact.public_path) ||
      !/^[0-9a-f]{64}$/.test(artifact.sha256 ?? "") ||
      !Number.isInteger(artifact.byte_count) ||
      artifact.byte_count < 1
    ) {
      fail(studyId, `unsafe or malformed artifact ${artifact?.role ?? "unknown"}`);
    }
    publicPaths.add(artifact.public_path);
    const artifactPath = resolve(publicDirectory, artifact.public_path);
    if (!artifactPath.startsWith(`${publicDirectory}${sep}`)) {
      fail(studyId, `artifact escaped public directory: ${artifact.public_path}`);
    }
    const artifactBytes = await readFile(artifactPath);
    if (
      artifactBytes.length !== artifact.byte_count ||
      digest(artifactBytes) !== artifact.sha256
    ) {
      fail(studyId, `artifact bytes or digest mismatch: ${artifact.public_path}`);
    }
    if (
      (artifact.media_type?.startsWith("text/") ||
        ["application/json", "application/yaml"].includes(artifact.media_type)) &&
      privateText.test(artifactBytes.toString("utf8"))
    ) {
      fail(studyId, `artifact contains private or unrelated text: ${artifact.public_path}`);
    }
  }
  for (const role of requiredAccuracyArtifactRoles) {
    if (!roles.has(role)) fail(studyId, `missing required artifact role ${role}`);
  }

  console.log(
    `validated study ${studyId}: ${runs.length} terminal accuracy runs, ` +
      `${bundle.classification.replication_outcome}, ` +
      `bundle ${digest(bundleBytes).slice(0, 12)}`,
  );
}

const files = (await readdir(publicationsDirectory))
  .filter((name) => /^study-[0-9]{3,}\.json$/.test(name))
  .sort();
if (files.length === 0) throw new Error("no NULSPEC publication bundles found");

for (const file of files) {
  const bundlePath = resolve(publicationsDirectory, file);
  const bundleBytes = await readFile(bundlePath);
  const bundleText = bundleBytes.toString("utf8");
  const bundle = JSON.parse(bundleText);
  const studyId = bundle?.study?.id ?? basename(file, ".json");

  if (privateText.test(bundleText)) fail(studyId, "bundle contains private or unrelated text");
  if (bundle.schema_version === accuracySchema) {
    await validateAccuracyBundle(bundle, bundleBytes, file, studyId);
    continue;
  }
  if (bundle.schema_version !== 1) fail(studyId, "schema_version must be 1");
  if (bundle.publication_status !== "ready") fail(studyId, "bundle is not ready");
  if (!/^[0-9]{3,}$/.test(studyId)) fail(studyId, "invalid study id");
  if (file !== `study-${studyId}.json`) fail(studyId, "filename does not match study id");
  if (!/^https:\/\/arxiv\.org\/abs\//.test(bundle.study?.paper?.url ?? "")) {
    fail(studyId, "paper URL is not canonical arXiv");
  }
  if (!/^[0-9a-f]{40}$/.test(bundle.source?.evidence_revision ?? "")) {
    fail(studyId, "evidence revision is not a full Git SHA");
  }
  if (!classifications.has(bundle.verdict?.classification)) {
    fail(studyId, "invalid study classification");
  }

  const navigation = bundle.evidence_navigation;
  if (
    !isObject(navigation) ||
    navigation.requested !== true ||
    navigation.implementation_owner !== "website_team" ||
    navigation.route_contract?.arm_detail !==
      "/studies/{study_id}/arms/{arm_id}" ||
    navigation.route_contract?.comparison_fragment !== "#comparison" ||
    navigation.route_contract?.execution_fragment !== "#execution" ||
    navigation.route_contract?.provenance_fragment !== "#provenance" ||
    navigation.route_contract?.evidence_fragment !== "#evidence" ||
    navigation.route_contract?.future_attempts_fragment !== "#attempts" ||
    navigation.matrix_interaction?.explicit_link_label !== "View evidence" ||
    navigation.arm_page_mvp?.status !==
      "implementable_from_current_publication_bundle" ||
    navigation.arm_page_mvp?.available_source?.join_key !== "arm_id" ||
    navigation.phase_two_evidence_index?.status !== "not_yet_public"
  ) {
    fail(studyId, "arm evidence navigation contract is missing or malformed");
  }

  const extension = bundle.extension_call_to_action;
  if (
    !isObject(extension) ||
    extension.requested !== true ||
    extension.implementation_owner !== "website_team" ||
    extension.button_label !== "Vote to extend this paper" ||
    typeof extension.prompt !== "string" ||
    extension.prompt.trim().length === 0 ||
    extension.prompt.length > 300 ||
    extension.selection_mode !== "single_choice" ||
    !Array.isArray(extension.options) ||
    extension.options.length === 0 ||
    extension.options.length > 12
  ) {
    fail(studyId, "extension vote contract is missing or malformed");
  }
  const extensionIds = new Set();
  const extensionPriorities = new Set();
  for (const option of extension.options) {
    if (
      !isObject(option) ||
      !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(option.id ?? "") ||
      extensionIds.has(option.id) ||
      typeof option.label !== "string" ||
      option.label.trim().length === 0 ||
      option.label.length > 120 ||
      typeof option.role !== "string" ||
      option.role.trim().length === 0 ||
      option.role.length > 120 ||
      !Number.isInteger(option.priority) ||
      option.priority < 1 ||
      extensionPriorities.has(option.priority) ||
      typeof option.summary !== "string" ||
      option.summary.trim().length === 0 ||
      option.summary.length > 700
    ) {
      fail(studyId, `invalid extension option ${option?.id ?? "unknown"}`);
    }
    extensionIds.add(option.id);
    extensionPriorities.add(option.priority);
  }

  const arms = bundle.arms;
  if (!Array.isArray(arms) || arms.length === 0) fail(studyId, "arms are missing");
  for (const arm of arms) {
    if (
      !isObject(arm) ||
      typeof arm.arm_id !== "string" ||
      !armRouteComponent.test(arm.arm_id)
    ) {
      fail(
        studyId,
        "unsafe arm route component " + (arm?.arm_id ?? "unknown"),
      );
    }
  }
  const armIds = new Set(arms.map((arm) => arm.arm_id));
  if (armIds.size !== arms.length) fail(studyId, "arm ids are not unique");
  const completion = bundle.completion;
  if (
    completion?.registered_arms !== arms.length ||
    completion?.terminal_arms !== arms.length ||
    completion?.claim_ready_arms !== arms.length
  ) {
    fail(studyId, "ready-state completion counts are not closed");
  }
  const frozen = bundle.frozen_primary_result;
  if (
    !isObject(frozen) ||
    frozen.registered_arms !== completion.registered_arms ||
    frozen.claim_ready_arms !== completion.claim_ready_arms ||
    frozen.may_be_rewritten_by_extension !== false
  ) {
    fail(studyId, "frozen primary result contract does not match completion");
  }
  if (
    !isObject(completion.gates) ||
    Object.keys(completion.gates).length === 0 ||
    !Object.values(completion.gates).every((value) => value === true)
  ) {
    fail(studyId, "all completion gates must be true");
  }

  const actualTrackCounts = new Map();
  for (const [index, arm] of arms.entries()) {
    const detailRoute = "/studies/" + studyId + "/arms/" + arm.arm_id;
    if (detailRoutes.has(detailRoute)) {
      fail(studyId, "duplicate arm detail route " + detailRoute);
    }
    detailRoutes.add(detailRoute);
    if (arm.ordinal !== index + 1) fail(studyId, `non-contiguous ordinal at ${arm.arm_id}`);
    if (!terminalExecutions.has(arm.execution)) fail(studyId, `non-terminal arm ${arm.arm_id}`);
    if (arm.claim_ready !== true) fail(studyId, `non-claim-ready arm ${arm.arm_id}`);
    if (arm.recovery_used !== (arm.execution === "completed_with_recovery")) {
      fail(studyId, `recovery flag contradicts execution at ${arm.arm_id}`);
    }
    if (!provenance.has(arm.provenance)) fail(studyId, `invalid provenance at ${arm.arm_id}`);
    if (!verdicts.has(arm.verdict)) fail(studyId, `invalid verdict at ${arm.arm_id}`);
    if (typeof arm.host !== "string" || !arm.host.startsWith("lab-")) {
      fail(studyId, `non-neutral host alias at ${arm.arm_id}`);
    }
    const metrics = arm.metrics;
    if (
      !isObject(metrics) ||
      !finiteNumber(metrics.published_reward_delta) ||
      !finiteNumber(metrics.release_reward_delta) ||
      !validInterval(metrics.release_prompt_bootstrap_95_ci) ||
      !finiteNumber(metrics.independent_paired_reward_delta) ||
      !validInterval(metrics.independent_paired_bootstrap_95_ci) ||
      !finiteNumber(metrics.independent_paired_sign_flip_pvalue_holm_15)
    ) {
      fail(studyId, `invalid quantitative metrics at ${arm.arm_id}`);
    }
    actualTrackCounts.set(arm.track, (actualTrackCounts.get(arm.track) ?? 0) + 1);
  }

  if (!Array.isArray(completion.tracks) || completion.tracks.length !== actualTrackCounts.size) {
    fail(studyId, "declared tracks do not match arm rows");
  }
  for (const track of completion.tracks) {
    const count = actualTrackCounts.get(track.id);
    if (
      count !== track.registered_arms ||
      count !== track.terminal_arms ||
      count !== track.claim_ready_arms
    ) {
      fail(studyId, `track ${track.id} counts do not close`);
    }
  }

  const matrixPath = resolve(
    root,
    "protocols",
    bundle.study.paper.arxiv_id,
    "matrix.csv",
  );
  const matrixBytes = await readFile(matrixPath);
  if (digest(matrixBytes) !== bundle.protocol.matrix_sha256) {
    fail(studyId, "matrix digest differs from the frozen protocol");
  }
  const matrixIds = matrixBytes
    .toString("utf8")
    .trim()
    .split("\n")
    .slice(1)
    .map((row) => row.split(",")[0]);
  if (
    matrixIds.length !== arms.length ||
    matrixIds.some((armId) => !armIds.has(armId))
  ) {
    fail(studyId, "publication arms differ from the frozen matrix");
  }

  if (!Array.isArray(bundle.artifacts)) fail(studyId, "artifacts are missing");
  const roles = new Set();
  const publicPaths = new Set();
  for (const artifact of bundle.artifacts) {
    if (!isObject(artifact) || roles.has(artifact.role)) {
      fail(studyId, `missing or duplicate artifact role ${artifact?.role}`);
    }
    roles.add(artifact.role);
    if (
      !safeRelative(artifact.public_path) ||
      !artifact.public_path.startsWith(`studies/${studyId}/artifacts/`) ||
      publicPaths.has(artifact.public_path)
    ) {
      fail(studyId, `unsafe or duplicate public artifact path ${artifact.public_path}`);
    }
    publicPaths.add(artifact.public_path);
    if (!/^[0-9a-f]{64}$/.test(artifact.sha256 ?? "")) {
      fail(studyId, `invalid artifact digest for ${artifact.role}`);
    }
    const artifactPath = resolve(publicDirectory, artifact.public_path);
    if (!artifactPath.startsWith(`${publicDirectory}${sep}`)) {
      fail(studyId, `artifact escaped public directory: ${artifact.public_path}`);
    }
    const artifactBytes = await readFile(artifactPath);
    if (digest(artifactBytes) !== artifact.sha256) {
      fail(studyId, `artifact digest mismatch: ${artifact.public_path}`);
    }
    if (
      (artifact.media_type?.startsWith("text/") ||
        ["application/json", "application/yaml"].includes(artifact.media_type)) &&
      privateText.test(artifactBytes.toString("utf8"))
    ) {
      fail(studyId, `artifact contains private or unrelated text: ${artifact.public_path}`);
    }
  }
  for (const role of requiredArtifactRoles) {
    if (!roles.has(role)) fail(studyId, `missing required artifact role ${role}`);
  }

  console.log(
    `validated study ${studyId}: ${arms.length} terminal claim-ready arms, ` +
      `${completion.tracks.length} tracks, ${bundle.verdict.classification}, ` +
      `bundle ${digest(bundleBytes).slice(0, 12)}`,
  );
}

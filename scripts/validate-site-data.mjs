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
]);
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

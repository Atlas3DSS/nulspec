import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const studyPath = resolve(root, "site-data/study-001.json");
const matrixPath = resolve(root, "protocols/2607.25091/matrix.csv");
const study = JSON.parse(await readFile(studyPath, "utf8"));
const matrixBytes = await readFile(matrixPath);
const matrixText = matrixBytes.toString("utf8");

const fail = (message) => {
  throw new Error(`study-001 validation failed: ${message}`);
};

if (study.study_id !== "001") fail("unexpected study id");
if (study.arms.length !== 15) fail(`expected 15 arms, found ${study.arms.length}`);

const armIds = new Set(study.arms.map((arm) => arm.arm_id));
if (armIds.size !== 15) fail("arm ids are not unique");

const frozenTrackR = matrixText
  .trim()
  .split("\n")
  .slice(1)
  .map((row) => row.split(","))
  .filter((row) => row[1] === "R")
  .map((row) => row[0]);

for (const armId of frozenTrackR) {
  if (!armIds.has(armId)) fail(`missing frozen Track R arm ${armId}`);
}

const expectedMatrixHash = createHash("sha256").update(matrixBytes).digest("hex");
if (study.protocol.matrix_sha256 !== expectedMatrixHash) {
  fail("matrix digest differs from the frozen protocol");
}

const validStates = new Set(["QUEUED", "RUNNING", "DONE", "FAILED", "ABORTED"]);
const validProvenance = new Set(["EXACT", "COMPAT"]);
const validVerdicts = new Set([null, "MATCH", "DIVERGES", "INCONCLUSIVE"]);

for (const [index, arm] of study.arms.entries()) {
  if (arm.ordinal !== index + 1) fail(`non-contiguous ordinal at ${arm.arm_id}`);
  if (!validStates.has(arm.state)) fail(`invalid state at ${arm.arm_id}`);
  if (!validProvenance.has(arm.provenance)) {
    fail(`invalid provenance at ${arm.arm_id}`);
  }
  if (!validVerdicts.has(arm.verdict)) fail(`invalid verdict at ${arm.arm_id}`);
  if (!arm.gpu || !arm.host) fail(`missing hardware assignment at ${arm.arm_id}`);
}

if (study.state !== "REPORTED" && study.arms.some((arm) => arm.verdict !== null)) {
  fail("verdicts must remain gated until the study is REPORTED");
}

if (!study.deviations.some((item) => item.id === "D-001")) {
  fail("Blackwell compatibility deviation is missing");
}

console.log(
  `validated study ${study.study_id}: 15 frozen Track R arms, ` +
    `${study.deviations.length} deviations, no premature verdicts`,
);

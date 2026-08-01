import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const queuePath = resolve(process.cwd(), "public/data/paper-queue.json");
const queue = JSON.parse(await readFile(queuePath, "utf8"));

const fail = (message) => {
  throw new Error(`paper queue validation failed: ${message}`);
};
const isObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const nonEmptyString = (value, maximumLength) =>
  typeof value === "string" &&
  value.trim().length > 0 &&
  value.length <= maximumLength;
const stringList = (value, maximumItems, maximumLength) =>
  Array.isArray(value) &&
  value.length <= maximumItems &&
  value.every((item) => nonEmptyString(item, maximumLength));
const httpsUrl = (value) => {
  if (!nonEmptyString(value, 500)) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
};
const optionalString = (value, maximumLength) =>
  value === undefined || value === null || value === "" ||
  nonEmptyString(value, maximumLength);
const optionalUrl = (value) =>
  value === undefined || value === null || value === "" || httpsUrl(value);

if (!isObject(queue) || queue.schema_version !== 1) {
  fail("schema_version must be 1");
}
if (
  queue.generated_at_utc !== null &&
  (typeof queue.generated_at_utc !== "string" ||
    Number.isNaN(Date.parse(queue.generated_at_utc)))
) {
  fail("generated_at_utc must be null or a valid timestamp");
}
if (
  !isObject(queue.voting) ||
  typeof queue.voting.enabled !== "boolean" ||
  !nonEmptyString(queue.voting.policy_version, 80)
) {
  fail("voting policy is invalid");
}
if (!Array.isArray(queue.papers) || queue.papers.length > 500) {
  fail("papers must be an array with at most 500 entries");
}

const identifiers = new Set();
for (const [index, paper] of queue.papers.entries()) {
  const location = `papers[${index}]`;
  if (!isObject(paper)) fail(`${location} must be an object`);
  if (!nonEmptyString(paper.id, 160)) fail(`${location}.id is invalid`);
  if (identifiers.has(paper.id)) fail(`${location}.id is duplicated`);
  identifiers.add(paper.id);
  if (!nonEmptyString(paper.title, 400)) fail(`${location}.title is invalid`);
  if (!httpsUrl(paper.url)) fail(`${location}.url must be HTTPS`);
  if (!optionalString(paper.source_id, 160)) {
    fail(`${location}.source_id is invalid`);
  }
  if (!stringList(paper.authors, 100, 160)) {
    fail(`${location}.authors is invalid`);
  }
  if (
    !nonEmptyString(paper.published_at, 40) ||
    Number.isNaN(Date.parse(paper.published_at))
  ) {
    fail(`${location}.published_at is invalid`);
  }
  if (!optionalString(paper.venue, 160)) fail(`${location}.venue is invalid`);
  if (!stringList(paper.topics, 16, 80)) fail(`${location}.topics is invalid`);
  if (!nonEmptyString(paper.summary, 2_000)) fail(`${location}.summary is invalid`);
  if (!nonEmptyString(paper.replication_case, 1_500)) {
    fail(`${location}.replication_case is invalid`);
  }
  if (!nonEmptyString(paper.audience_case, 1_500)) {
    fail(`${location}.audience_case is invalid`);
  }
  if (!optionalUrl(paper.code_url)) fail(`${location}.code_url must be HTTPS`);
  if (!optionalUrl(paper.data_url)) fail(`${location}.data_url must be HTTPS`);
  if (!optionalString(paper.estimated_hardware, 240)) {
    fail(`${location}.estimated_hardware is invalid`);
  }
  if (!optionalString(paper.estimated_runtime, 240)) {
    fail(`${location}.estimated_runtime is invalid`);
  }
  if (!Number.isSafeInteger(paper.vote_count) || paper.vote_count < 0) {
    fail(`${location}.vote_count must be a non-negative integer`);
  }
  if (typeof paper.viewer_has_voted !== "boolean") {
    fail(`${location}.viewer_has_voted must be boolean`);
  }
}

console.log(`Validated paper queue snapshot: ${queue.papers.length} candidate(s).`);

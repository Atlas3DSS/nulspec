import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const doc = JSON.parse(
  await readFile(resolve(root, "site-data/random-acts/random-acts.public.json"), "utf8"),
);
const fail = (message) => {
  throw new Error(`random acts data validation failed: ${message}`);
};
const publishedStatuses = new Set(["approved", "sent", "replied"]);
const forbidden = /quincy|labrun|devbox|wtatum|orwel|monkeypc|workboard|\/home\/|\/mnt\/|192\.168\.|follow_on|message_draft/i;

if (doc.schema_version !== "random-acts-v1") fail("schema_version must be random-acts-v1");
if (!Array.isArray(doc.acts)) fail("acts must be an array");
if (forbidden.test(JSON.stringify(doc))) fail("public data contains private infrastructure or owner-only fields");

const slugs = new Set();
for (const act of doc.acts) {
  if (!/^[a-z0-9-]+$/.test(act.slug) || slugs.has(act.slug)) fail(`bad or duplicate slug ${act.slug}`);
  slugs.add(act.slug);
  if (!publishedStatuses.has(act.owner_status)) fail(`${act.slug} is not owner-approved`);
  for (const key of ["issue_url", "repo_url"]) {
    const url = new URL(act[key]);
    if (url.protocol !== "https:" || url.hostname !== "github.com") fail(`${act.slug}.${key} must be an https GitHub URL`);
  }
  if (!Array.isArray(act.headline_items) || act.headline_items.length === 0) fail(`${act.slug} has no headline numbers`);
  if (act.report_path) {
    const report = await readFile(resolve(root, "public", act.report_path.replace(/^\//, ""))).catch(() => null);
    if (!report) fail(`${act.slug} report is missing: ${act.report_path}`);
  }
}

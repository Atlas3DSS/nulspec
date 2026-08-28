import { createHash } from "node:crypto";
import { readdir, readFile, stat } from "node:fs/promises";
import { join, relative, resolve } from "node:path";

const root = process.cwd();
const outputDirectory = resolve(root, "out");
const postRoute = "blog/scheduling-is-all-you-need";
const postDirectory = resolve(outputDirectory, postRoute);
const sweepDirectory = resolve(postDirectory, "integer-boundary-sweep");
const title =
  "Scheduling is all you need: use sparsity to save time while controlling loss.";
const retiredTopLevelPaths = [
  "data",
  "fable-refusals",
  "methodology",
  "operations",
  "papers",
  "review",
  "selection",
  "sitemap.xml",
  "studies",
];
const prohibitedPostCopy = [
  "human review",
  "private review notes",
  "interpretation boundary",
  "what this page does not claim",
  "quality conclusions",
  "human verdict",
  "publication disabled",
  "unpublished",
];

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectFiles(path)));
    } else if (entry.isFile()) {
      files.push(path);
    }
  }
  return files;
}

const files = await collectFiles(outputDirectory);
const relativeFiles = files.map((path) => relative(outputDirectory, path));
const home = await readFile(resolve(outputDirectory, "index.html"), "utf8");
const post = await readFile(resolve(postDirectory, "index.html"), "utf8");

for (const phrase of [
  "AI enthusiasts doing things.",
  "/blog/scheduling-is-all-you-need/",
  "h3-sparsity-timing.svg",
]) {
  if (!home.includes(phrase)) {
    throw new Error(`generated home page omits required copy or link: ${phrase}`);
  }
}

for (const phrase of [
  title,
  "Euler / Simple",
  "Sparse Kitchen at 30% video KV",
  "Exact fixed prompt",
  "What each sparse sequence returned to the clock",
  "Every integer handoff, three at a time",
  "-step Turbo gallery",
]) {
  if (!post.includes(phrase)) {
    throw new Error(`generated H3 post omits required copy: ${phrase}`);
  }
}
for (const turbo of [4, 8]) {
  if (!post.includes(`id="sweep-turbo-${turbo}"`)) {
    throw new Error(`generated H3 post omits the Turbo ${turbo} gallery`);
  }
}

if ((post.match(/<video/g) ?? []).length !== 12) {
  throw new Error("generated H3 post must contain six headline and six active gallery videos");
}
if ((post.match(/type="checkbox"/g) ?? []).length !== 12) {
  throw new Error("every generated H3 video card must expose a comparison checkbox");
}
if ((post.match(/<track/g) ?? []).length !== 0) {
  throw new Error("generated H3 post must not contain caption tracks");
}

for (const phrase of prohibitedPostCopy) {
  if (post.toLowerCase().includes(phrase)) {
    throw new Error(`generated H3 post contains removed meta commentary: ${phrase}`);
  }
}

if (post.indexOf("Exact fixed prompt") < post.indexOf("What each sparse sequence returned to the clock")) {
  throw new Error("the exact fixed prompt must remain at the bottom of the post");
}
if (post.indexOf("Every integer handoff, three at a time") < post.indexOf("Exact fixed prompt")) {
  throw new Error("the integer boundary galleries must follow the fixed prompt at the bottom");
}

for (const retiredPath of retiredTopLevelPaths) {
  if (
    relativeFiles.some(
      (path) => path === retiredPath || path.startsWith(`${retiredPath}/`),
    )
  ) {
    throw new Error(`retired public output remains: ${retiredPath}`);
  }
}

const manifest = JSON.parse(
  await readFile(resolve(postDirectory, "manifest.json"), "utf8"),
);
if (manifest.schema !== "nulspec_h3_schedule_note_v1" || manifest.cases?.length !== 6) {
  throw new Error("H3 manifest has an invalid schema or case count");
}

for (const item of manifest.cases) {
  const path = resolve(postDirectory, item.file);
  const metadata = await stat(path);
  if (!metadata.isFile() || metadata.size === 0) {
    throw new Error(`H3 video is absent or empty: ${item.file}`);
  }
  const digest = createHash("sha256").update(await readFile(path)).digest("hex");
  if (digest !== item.sha256) {
    throw new Error(`H3 video digest mismatch: ${item.file}`);
  }
}

const sweepManifest = JSON.parse(
  await readFile(resolve(sweepDirectory, "manifest.json"), "utf8"),
);
const sweepFamilies = sweepManifest.families ?? [];
const sweepCases = sweepFamilies.flatMap((family) => family.cases ?? []);
if (
  sweepManifest.schema !== "nulspec_h3_integer_boundary_gallery_v1" ||
  sweepManifest.case_count !== 55 ||
  sweepCases.length !== 55 ||
  JSON.stringify(sweepFamilies.map((family) => family.case_count)) !==
    JSON.stringify([21, 34])
) {
  throw new Error("generated integer boundary gallery manifest is invalid");
}
for (const item of sweepCases) {
  const path = resolve(sweepDirectory, item.file);
  const metadata = await stat(path);
  if (!metadata.isFile() || metadata.size !== item.bytes) {
    throw new Error(`integer boundary video is absent or has the wrong size: ${item.file}`);
  }
  const digest = createHash("sha256").update(await readFile(path)).digest("hex");
  if (digest !== item.sha256) {
    throw new Error(`integer boundary video digest mismatch: ${item.file}`);
  }
}

const graph = await readFile(
  resolve(postDirectory, "h3-sparsity-timing.svg"),
  "utf8",
);
for (const marker of ["−24.5 s", "−57.6 s", "H3 WALL TIME"]) {
  if (!graph.includes(marker)) {
    throw new Error(`H3 timing graph omits marker: ${marker}`);
  }
}

for (const [label, html] of [["home", home], ["post", post]]) {
  if (/noindex|nofollow/i.test(html)) {
    throw new Error(`${label} unexpectedly blocks search indexing`);
  }
}

const robots = await readFile(resolve(outputDirectory, "robots.txt"), "utf8");
if (!/User-agent:\s*\*/i.test(robots) || !/Allow:\s*\//i.test(robots)) {
  throw new Error("robots.txt does not permit crawling");
}
if (/Disallow:\s*\//i.test(robots)) {
  throw new Error("robots.txt still disallows the public site");
}

console.log(
  `validated minimal journal output in ${relativeFiles.length} files with 61 hash-bound H3 videos`,
);

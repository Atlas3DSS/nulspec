import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { join, relative, resolve } from "node:path";

const root = process.cwd();
const appDirectory = resolve(root, "app");
const publicDirectory = resolve(root, "public");
const postRoute = "blog/scheduling-is-all-you-need";
const postPublicDirectory = resolve(publicDirectory, postRoute);
const sweepPublicDirectory = resolve(postPublicDirectory, "integer-boundary-sweep");
const sweepManifestPath = resolve(sweepPublicDirectory, "manifest.json");
const title =
  "Scheduling is all you need: use sparsity to save time while controlling loss.";
const retiredRoutes = [
  "fable-refusals/page.tsx",
  "methodology/page.tsx",
  "operations/page.tsx",
  "papers/page.tsx",
  "review/login/page.tsx",
  "review/page.tsx",
  "selection/page.tsx",
  "sitemap.ts",
  "studies/[id]/arms/[armId]/page.tsx",
  "studies/[id]/page.tsx",
];
const retiredPublicDirectories = [
  "data",
  "fable-refusals",
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
const expectedAssets = [
  "all_sparse_8_00001_.mp4",
  "atlas-caption.vtt",
  "current_sage_4_00001_.mp4",
  "current_sage_8_00001_.mp4",
  "h3-sparsity-timing.svg",
  "manifest.json",
  "sparse2_dense2_4nfe_00001_.mp4",
  "sparse2_dense4_6nfe_00001_.mp4",
  "sparse4_dense4_8nfe_00001_.mp4",
];

async function collectFiles(directory) {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }

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

const home = await readFile(resolve(appDirectory, "site-home.tsx"), "utf8");
const post = await readFile(resolve(appDirectory, postRoute, "page.tsx"), "utf8");
const gallery = await readFile(
  resolve(appDirectory, postRoute, "integer-boundary-galleries.tsx"),
  "utf8",
);
const errors = [];

for (const phrase of [
  "AI enthusiasts doing things.",
  "/blog/scheduling-is-all-you-need/",
  "h3-sparsity-timing.svg",
]) {
  if (!home.includes(phrase)) {
    errors.push(`home page omits required copy or link: ${phrase}`);
  }
}

for (const phrase of [
  "55-render addendum",
  "-step Turbo gallery",
  "const pageSize = 3",
  "Previous three",
  "Next three",
]) {
  if (!gallery.includes(phrase)) {
    errors.push(`integer boundary gallery omits required copy or behavior: ${phrase}`);
  }
}

if (gallery.includes("<track") || gallery.includes("atlas-caption.vtt")) {
  errors.push("integer boundary gallery reuses the original clip caption track");
}

for (const phrase of [
  title,
  "Euler / Simple",
  "Sparse Kitchen at 30% video KV",
  "Exact fixed prompt",
  "What each sparse sequence returned to the clock",
]) {
  if (!post.includes(phrase)) {
    errors.push(`H3 post omits required copy: ${phrase}`);
  }
}

const normalizedPost = post.toLowerCase();
for (const phrase of prohibitedPostCopy) {
  if (normalizedPost.includes(phrase)) {
    errors.push(`H3 post contains removed meta commentary: ${phrase}`);
  }
}

for (const control of ["<select", "<textarea", "localStorage", "Export review JSON"]) {
  if (post.includes(control)) {
    errors.push(`H3 post contains removed review control: ${control}`);
  }
}

const appFiles = (await collectFiles(appDirectory)).filter((path) =>
  /\.(?:css|tsx?)$/.test(path),
);
const activeAppPaths = new Set(
  appFiles.map((path) => relative(appDirectory, path)),
);
for (const retiredRoute of retiredRoutes) {
  if (activeAppPaths.has(retiredRoute)) {
    errors.push(`retired public route remains in app/: ${retiredRoute}`);
  }
}

for (const retiredDirectory of retiredPublicDirectories) {
  const retiredFiles = await collectFiles(
    resolve(publicDirectory, retiredDirectory),
  );
  if (retiredFiles.length > 0) {
    errors.push(
      `retired public directory still contains deployable files: ${retiredDirectory}`,
    );
  }
}

const postAssets = (await readdir(postPublicDirectory, { withFileTypes: true }))
  .filter((entry) => entry.isFile())
  .map((entry) => entry.name)
  .sort();
if (JSON.stringify(postAssets) !== JSON.stringify(expectedAssets)) {
  errors.push(
    `H3 public assets differ from the expected set: ${postAssets.join(", ")}`,
  );
}

const sweepManifest = JSON.parse(await readFile(sweepManifestPath, "utf8"));
const sweepFamilies = sweepManifest.families ?? [];
const sweepCases = sweepFamilies.flatMap((family) => family.cases ?? []);
const sweepDelivery = sweepManifest.delivery_encoding ?? {};
if (
  sweepManifest.schema !== "nulspec_h3_integer_boundary_gallery_v1" ||
  sweepManifest.case_count !== 55 ||
  sweepCases.length !== 55 ||
  JSON.stringify(sweepFamilies.map((family) => family.case_count)) !==
    JSON.stringify([21, 34])
) {
  errors.push("integer boundary sweep manifest has the wrong schema or family counts");
}
if (
  sweepDelivery.video_codec !== "H.264/AVC" ||
  sweepDelivery.video_crf !== 27 ||
  sweepDelivery.audio_codec !== "AAC" ||
  sweepDelivery.audio_bitrate_kbps !== 64 ||
  JSON.stringify(sweepDelivery.resolution) !== JSON.stringify([768, 768]) ||
  sweepDelivery.frame_rate !== 24
) {
  errors.push("integer boundary sweep manifest omits its web delivery encoding");
}

const sweepFiles = (await readdir(sweepPublicDirectory, { withFileTypes: true }))
  .filter((entry) => entry.isFile())
  .map((entry) => entry.name)
  .sort();
const expectedSweepFiles = ["manifest.json", ...sweepCases.map((item) => item.file)].sort();
if (JSON.stringify(sweepFiles) !== JSON.stringify(expectedSweepFiles)) {
  errors.push("integer boundary sweep assets differ from its public manifest");
}

const seenSweepIds = new Set();
for (const item of sweepCases) {
  if (
    seenSweepIds.has(item.id) ||
    !/^t[48]_n(?:04|06|08|12)_s\d{2}_d\d{2}$/.test(item.id) ||
    item.file !== `${item.id}.mp4` ||
    item.sparse_nfe + item.dense_nfe !== item.total_nfe ||
    !Number.isSafeInteger(item.source_bytes) ||
    item.source_bytes < item.bytes ||
    !/^[0-9a-f]{64}$/.test(item.source_sha256 ?? "")
  ) {
    errors.push(`invalid integer boundary case metadata: ${item.id}`);
    continue;
  }
  seenSweepIds.add(item.id);
  const bytes = await readFile(resolve(sweepPublicDirectory, item.file));
  const digest = createHash("sha256").update(bytes).digest("hex");
  if (bytes.length !== item.bytes || digest !== item.sha256) {
    errors.push(`integer boundary video failed byte/hash validation: ${item.file}`);
  }
}

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(
    `validated minimal NULSPEC home, H3 post, and 55-case gallery across ${appFiles.length} app files`,
  );
}

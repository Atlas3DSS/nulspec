import { readdir, readFile } from "node:fs/promises";
import { join, relative, resolve } from "node:path";

const root = process.cwd();
const appDirectory = resolve(root, "app");
const publicDirectory = resolve(root, "public");
const postRoute = "blog/scheduling-is-all-you-need";
const postPublicDirectory = resolve(publicDirectory, postRoute);
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

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(
    `validated minimal NULSPEC home and H3 post across ${appFiles.length} app files`,
  );
}

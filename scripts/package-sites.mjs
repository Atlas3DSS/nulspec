import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { createReadStream } from "node:fs";
import { access, mkdir, readFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const root = process.cwd();
const openNext = resolve(root, ".open-next");
const worker = resolve(openNext, "worker.js");
const assets = resolve(openNext, "assets");
const hostingConfig = resolve(root, ".openai", "hosting.json");

await access(worker);
if (!(await stat(assets)).isDirectory()) {
  throw new Error(".open-next/assets must be a directory");
}

const hosting = JSON.parse(await readFile(hostingConfig, "utf8"));
if (typeof hosting.project_id !== "string" || hosting.project_id.length === 0) {
  throw new Error(".openai/hosting.json must contain a project_id");
}

const sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], {
  cwd: root,
  encoding: "utf8",
}).trim();
const trackedChanges = execFileSync(
  "git",
  ["status", "--porcelain", "--untracked-files=no"],
  { cwd: root, encoding: "utf8" },
).trim();

if (trackedChanges.length > 0) {
  throw new Error(
    "Refusing to package a Sites artifact while tracked files differ from HEAD",
  );
}

const outputDirectory = resolve(root, ".artifacts", "sites");
const output = resolve(
  process.env.NULSPEC_SITES_ARCHIVE ??
    resolve(outputDirectory, `nulspec-sites-${sourceCommit}.tar`),
);

await mkdir(dirname(output), { recursive: true });
execFileSync(
  "tar",
  ["-cf", output, ".open-next", ".openai/hosting.json"],
  { cwd: root, stdio: "inherit" },
);

const digest = createHash("sha256");
for await (const chunk of createReadStream(output)) {
  digest.update(chunk);
}

const archive = await stat(output);
console.log(
  JSON.stringify(
    {
      archive: output,
      bytes: archive.size,
      commit_sha: sourceCommit,
      project_id: hosting.project_id,
      sha256: digest.digest("hex"),
    },
    null,
    2,
  ),
);

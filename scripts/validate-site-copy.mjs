import { readdir, readFile } from "node:fs/promises";
import { join, relative } from "node:path";

const sourceRoots = [
  "app",
  "components",
  "lib",
  "public",
  "site-data/publications",
];
const prohibitedPhrases = [
  "accelerationalists",
  "a complete matrix, not a favorable checkpoint",
  "a deviation hidden is a claim faked",
  "a paper is not a vibe",
  "artifact is the argument",
  "buy the lab monkey",
  "checking the work",
  "curious enough to check",
  "deeper evidence is not yet public",
  "deterministic comparison, reported independently",
  "every useful objection should become a reproducible test",
  "is a versioned statement",
  "extensions remain fenced",
  "fastest route runs through",
  "follow or challenge the work",
  "hash-bound artifacts supporting this selected arm",
  "keep the apparatus alive",
  "little more runway",
  "make rerunning cheaper",
  "material differences stay attached to the result",
  "new evidence may extend this record",
  "no hidden reruns",
  "no pay-to-confirm",
  "no success-only drawer",
  "null result is a result",
  "null reference",
  "number every deviation",
  "observed hardware, neutral lab identities",
  "paper intake",
  "publish the miss",
  "put a claim on the bench",
  "relaying…",
  "result cooperates",
  "see the spread before reading the decimals",
  "seen a result you want tested",
  "silently imputed",
  "success-only drawer",
  "support buys compute, not conclusions",
  "the terminal state and recovery flag stay visible",
  "this page narrows the evidence; it does not widen the claim",
  "vote relay",
  "we rerun the experiments",
  "you are reading marketing",
];
const requiredPhrases = [
  "Automated consistency audits have zero scientific decision weight.",
  "Current intake predates this randomized policy.",
  "Detailed attempt records are not yet public",
  "Published claims, independently tested.",
  "Reward-difference estimates and conditional 95% intervals",
];

async function collectSourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectSourceFiles(path)));
    } else if (entry.isFile() && /\.(?:tsx?|md|json)$/.test(path)) {
      files.push(path);
    }
  }
  return files;
}

const files = (
  await Promise.all(sourceRoots.map((root) => collectSourceFiles(root)))
).flat();
const sources = await Promise.all(
  files.map(async (path) => ({ path, text: await readFile(path, "utf8") })),
);
const errors = [];

for (const source of sources) {
  const normalized = source.text.toLowerCase();
  for (const phrase of prohibitedPhrases) {
    if (normalized.includes(phrase.toLowerCase())) {
      errors.push(
        `${relative(process.cwd(), source.path)} contains prohibited public copy: ${phrase}`,
      );
    }
  }
}

const combined = sources.map((source) => source.text).join("\n");
for (const phrase of requiredPhrases) {
  const count = combined.split(phrase).length - 1;
  if (count !== 1) {
    errors.push(`required public copy must appear exactly once: ${phrase} (found ${count})`);
  }
}

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(
    `validated public copy in ${files.length} source and artifact files: no prohibited phrases`,
  );
}

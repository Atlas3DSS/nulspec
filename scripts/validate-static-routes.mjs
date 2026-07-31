import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const publicationsDirectory = resolve(root, "site-data", "publications");
const outputDirectory = resolve(root, "out");
const routeComponent = /^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$/;
const expectedRoutes = new Set();

for (const file of (await readdir(publicationsDirectory)).sort()) {
  if (!/^study-[0-9]{3,}\.json$/.test(file)) continue;
  const bundle = JSON.parse(
    await readFile(resolve(publicationsDirectory, file), "utf8"),
  );
  const studyId = bundle?.study?.id;
  if (typeof studyId !== "string" || !/^[0-9]{3,}$/.test(studyId)) {
    throw new Error("publication has an unsafe study route component: " + file);
  }
  for (const arm of bundle.arms ?? []) {
    if (
      typeof arm.arm_id !== "string" ||
      !routeComponent.test(arm.arm_id)
    ) {
      throw new Error(
        "publication has an unsafe arm route component: " +
          String(arm?.arm_id),
      );
    }
    const route = "/studies/" + studyId + "/arms/" + arm.arm_id;
    if (expectedRoutes.has(route)) {
      throw new Error("duplicate expected arm route: " + route);
    }
    expectedRoutes.add(route);
    const page = resolve(outputDirectory, route.slice(1), "index.html");
    const html = await readFile(page, "utf8");
    if (
      !html.includes(arm.arm_id) ||
      !html.includes("Deeper evidence is not yet public")
    ) {
      throw new Error("arm page does not identify its bound evidence: " + route);
    }
  }
}

const actualRoutes = new Set();
const studiesRoot = resolve(outputDirectory, "studies");
for (const studyEntry of await readdir(studiesRoot, { withFileTypes: true })) {
  if (!studyEntry.isDirectory()) continue;
  const armsRoot = resolve(studiesRoot, studyEntry.name, "arms");
  let armEntries;
  try {
    armEntries = await readdir(armsRoot, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") continue;
    throw error;
  }
  for (const armEntry of armEntries) {
    if (!armEntry.isDirectory()) continue;
    const route =
      "/studies/" + studyEntry.name + "/arms/" + armEntry.name;
    await readFile(resolve(armsRoot, armEntry.name, "index.html"));
    actualRoutes.add(route);
  }
}

const missing = [...expectedRoutes].filter((route) => !actualRoutes.has(route));
const unknown = [...actualRoutes].filter((route) => !expectedRoutes.has(route));
if (missing.length > 0 || unknown.length > 0) {
  throw new Error(
    "arm route manifest mismatch; missing=" +
      JSON.stringify(missing) +
      " unknown=" +
      JSON.stringify(unknown),
  );
}

console.log(
  "validated " + actualRoutes.size + " static arm evidence routes",
);

import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const staticOutput = resolve(root, "out");
const sitesOutput = resolve(root, ".open-next");
const sitesAssets = resolve(sitesOutput, "assets");
const hostingConfig = resolve(root, ".openai", "hosting.json");

const hosting = JSON.parse(await readFile(hostingConfig, "utf8"));

if (typeof hosting.project_id !== "string" || hosting.project_id.length === 0) {
  throw new Error(".openai/hosting.json must contain a project_id");
}

await rm(sitesOutput, { recursive: true, force: true });
await mkdir(sitesOutput, { recursive: true });
await cp(staticOutput, sitesAssets, { recursive: true });

const worker = `const FILE_EXTENSION = /\\.[^/]+$/;

function resolveAssetPath(pathname) {
  if (pathname === "/") {
    return "/index.html";
  }

  if (pathname.endsWith("/")) {
    return \`\${pathname}index.html\`;
  }

  if (!FILE_EXTENSION.test(pathname)) {
    return \`\${pathname}/index.html\`;
  }

  return pathname;
}

async function fetchAsset(request, env, pathname) {
  const url = new URL(request.url);
  url.pathname = pathname;
  return env.ASSETS.fetch(new Request(url, request));
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }

    const { pathname } = new URL(request.url);
    const response = await fetchAsset(request, env, resolveAssetPath(pathname));

    if (response.status !== 404) {
      return response;
    }

    const fallback = await fetchAsset(request, env, "/404/");
    return new Response(fallback.body, {
      status: 404,
      headers: fallback.headers,
    });
  },
};
`;

await writeFile(resolve(sitesOutput, "worker.js"), worker);

console.log(
  `Prepared ChatGPT Sites artifact for ${hosting.project_id} from ${staticOutput}`,
);

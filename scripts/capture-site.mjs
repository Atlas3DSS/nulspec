import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const require = createRequire(import.meta.url);
const baseUrl = process.env.NULSPEC_TEST_URL ?? "http://127.0.0.1:4321";
const outputDir = resolve(process.cwd(), ".artifacts/screenshots");
const browserPath =
  process.env.NULSPEC_CHROME_PATH ?? "/usr/bin/google-chrome-stable";

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: browserPath,
  headless: true,
});

const scenarios = [
  {
    name: "home-desktop",
    path: "/",
    width: 1440,
    height: 900,
    expectedLedgerRows: 30,
    expectedEvidenceLinks: 30,
    expectedNominationFields: 2,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 7,
    expectedArmSections: 0,
  },
  {
    name: "home-mobile",
    path: "/",
    width: 390,
    height: 844,
    expectedLedgerRows: 30,
    expectedEvidenceLinks: 30,
    expectedNominationFields: 2,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 7,
    expectedArmSections: 0,
  },
  {
    name: "study-desktop",
    path: "/studies/260725091",
    width: 1440,
    height: 900,
    expectedLedgerRows: 30,
    expectedEvidenceLinks: 30,
    expectedNominationFields: 0,
    expectedExtensionOptions: 5,
    expectedSignalVerdicts: 7,
    expectedArmSections: 0,
  },
  {
    name: "study-mobile",
    path: "/studies/260725091",
    width: 390,
    height: 844,
    expectedLedgerRows: 30,
    expectedEvidenceLinks: 30,
    expectedNominationFields: 0,
    expectedExtensionOptions: 5,
    expectedSignalVerdicts: 7,
    expectedArmSections: 0,
  },
  {
    name: "arm-evidence-desktop",
    path: "/studies/260725091/arms/R-pythia-70m-tinystories-s42",
    width: 1440,
    height: 900,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
  },
  {
    name: "arm-evidence-mobile",
    path: "/studies/260725091/arms/R-pythia-70m-tinystories-s42",
    width: 390,
    height: 844,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
  },
];

const report = [];
let failed = false;

for (const scenario of scenarios) {
  const page = await browser.newPage({
    viewport: { width: scenario.width, height: scenario.height },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });

  const response = await page.goto(`${baseUrl}${scenario.path}`, {
    waitUntil: "networkidle",
  });
  await page.evaluate(() => document.fonts.ready);

  const diagnostics = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const overflowingElements = [...document.querySelectorAll("body *")]
      .filter((element) => {
        if (element.closest(".table-scroll")) return false;
        if (element.closest(".nomination-form__trap")) return false;
        if (element.closest(".extension-vote__trap")) return false;
        const rect = element.getBoundingClientRect();
        return rect.left < -1 || rect.right > viewportWidth + 1;
      })
      .slice(0, 12)
      .map((element) => ({
        tag: element.tagName,
        className: element.className,
        right: Math.round(element.getBoundingClientRect().right),
        width: Math.round(element.getBoundingClientRect().width),
      }));

    return {
      title: document.title,
      statusText: document.querySelector('[role="status"]')?.textContent?.trim(),
      horizontalOverflow:
        document.body.scrollWidth > viewportWidth ||
        overflowingElements.length > 0,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: viewportWidth,
      ledgerRows: document.querySelectorAll(".run-table tbody tr").length,
      evidenceLinkLabels: [
        ...document.querySelectorAll(".run-evidence-link"),
      ].map((element) => element.textContent?.trim()),
      focusableEvidenceLinks: [
        ...document.querySelectorAll(".run-evidence-link"),
      ].filter(
        (element) =>
          element.tabIndex >= 0 &&
          typeof element.getAttribute("href") === "string",
      ).length,
      uniqueEvidenceTargets: new Set(
        [...document.querySelectorAll(".run-evidence-link")].map((element) =>
          element.getAttribute("href"),
        ),
      ).size,
      brandMarks: document.querySelectorAll(".wordmark__mark").length,
      nominationFields: [
        ...document.querySelectorAll(".nomination-form__field input"),
      ].map((element) => element.getAttribute("name")),
      signalVerdicts: [...document.querySelectorAll(".run-verdict")].filter(
        (element) => getComputedStyle(element).color === "rgb(92, 232, 255)",
      ).length,
      extensionOptions: document.querySelectorAll(
        '.extension-vote input[name="extension-option"]',
      ).length,
      extensionButton: document.querySelector(".extension-vote button")
        ?.textContent?.trim(),
      armSections: [
        "comparison",
        "execution",
        "provenance",
        "evidence",
        "limitations",
      ].filter((id) => document.getElementById(id)),
      deeperEvidenceHeading: document.querySelector(".arm-unavailable h3")
        ?.textContent?.trim(),
      overflowingElements,
    };
  });

  await page.screenshot({
    path: resolve(outputDir, `${scenario.name}-viewport.png`),
    fullPage: false,
  });
  await page.screenshot({
    path: resolve(outputDir, `${scenario.name}-full.png`),
    fullPage: true,
  });

  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const accessibility = await page.evaluate(async () => {
    const result = await window.axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
      },
    });
    return result.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      help: violation.help,
      nodes: violation.nodes.map((node) => node.target),
    }));
  });

  const scenarioFailed =
    !response?.ok() ||
    diagnostics.horizontalOverflow ||
    diagnostics.ledgerRows !== scenario.expectedLedgerRows ||
    diagnostics.evidenceLinkLabels.length !== scenario.expectedEvidenceLinks ||
    diagnostics.evidenceLinkLabels.some((label) => label !== "View evidence →") ||
    diagnostics.focusableEvidenceLinks !== scenario.expectedEvidenceLinks ||
    diagnostics.uniqueEvidenceTargets !== scenario.expectedEvidenceLinks ||
    diagnostics.brandMarks !== 2 ||
    diagnostics.nominationFields.length !== scenario.expectedNominationFields ||
    (scenario.path === "/" &&
      diagnostics.nominationFields.join(",") !== "email,paper") ||
    diagnostics.extensionOptions !== scenario.expectedExtensionOptions ||
    (scenario.expectedExtensionOptions > 0 &&
      diagnostics.extensionButton !== "Vote to extend this paper") ||
    diagnostics.signalVerdicts !== scenario.expectedSignalVerdicts ||
    diagnostics.armSections.length !== scenario.expectedArmSections ||
    (scenario.expectedArmSections > 0 &&
      diagnostics.deeperEvidenceHeading !== "Deeper evidence is not yet public.") ||
    accessibility.length > 0;
  failed ||= scenarioFailed;
  report.push({
    ...scenario,
    status: response?.status(),
    diagnostics,
    accessibility,
    passed: !scenarioFailed,
  });
  await page.close();
}

const removedLogoLab = await fetch(`${baseUrl}/logo-lab`, {
  redirect: "manual",
});
if (removedLogoLab.status !== 404) {
  failed = true;
}

const unknownArm = await fetch(
  baseUrl + "/studies/260725091/arms/not-a-published-arm",
  { redirect: "manual" },
);
if (unknownArm.status !== 404) {
  failed = true;
}

await browser.close();
await writeFile(
  resolve(outputDir, "browser-report.json"),
  `${JSON.stringify(report, null, 2)}\n`,
);

for (const item of report) {
  console.log(
    `${item.passed ? "PASS" : "FAIL"} ${item.name}: HTTP ${item.status}, ` +
      `${item.diagnostics.ledgerRows} ledger rows, ` +
      `${item.accessibility.length} accessibility violations`,
  );
}

console.log(
  `${removedLogoLab.status === 404 ? "PASS" : "FAIL"} removed-logo-lab: ` +
    `HTTP ${removedLogoLab.status}`,
);

console.log(
  (unknownArm.status === 404 ? "PASS" : "FAIL") +
    " unknown-arm: HTTP " +
    unknownArm.status,
);

if (failed) process.exitCode = 1;

import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const require = createRequire(import.meta.url);
const baseUrl = process.env.NULSPEC_TEST_URL ?? "http://127.0.0.1:4321";
const outputDir = resolve(process.cwd(), ".artifacts/screenshots");
const browserPath =
  process.env.NULSPEC_CHROME_PATH ?? "/usr/bin/google-chrome-stable";
const accuracyPublicationAvailable = existsSync(
  resolve(process.cwd(), "site-data/publications/study-260723346.json"),
);

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: browserPath,
  headless: true,
});

const testCandidatePapers = Array.from({ length: 100 }, (_, index) => ({
  id: `test-paper-${String(index + 1).padStart(3, "0")}`,
  title: `Computational replication candidate ${String(index + 1).padStart(3, "0")}`,
  url: `https://example.org/papers/${index + 1}`,
  source_id: `TEST:${String(index + 1).padStart(3, "0")}`,
  authors: [`Researcher ${index + 1}`, "Second Author"],
  published_at: new Date(Date.UTC(2026, 6, 31) - index * 86_400_000).toISOString(),
  venue: index % 2 === 0 ? "Test archive" : "Test journal",
  topics: index % 3 === 0 ? ["simulation", "statistics"] : ["evaluation"],
  summary:
    "This synthetic browser-test entry verifies that the candidate queue remains compact and readable with a full production-sized response.",
  replication_case:
    "The inputs, implementation, and quantitative endpoint are available for an end-to-end computational test.",
  audience_case:
    "The claim could affect research decisions beyond the paper's immediate specialty.",
  code_url: `https://example.org/code/${index + 1}`,
  data_url: index % 4 === 0 ? `https://example.org/data/${index + 1}` : undefined,
  estimated_hardware: index % 2 === 0 ? "1 × 24 GB GPU" : "CPU only",
  estimated_runtime: `${(index % 12) + 1} compute-hours`,
  vote_count: index === 73 ? 900 : (index * 17) % 113,
  viewer_has_voted: false,
}));

const scenarios = [
  {
    name: "home-desktop",
    path: "/",
    width: 1440,
    height: 900,
    expectedLedgerRows: accuracyPublicationAvailable ? 5 : 30,
    expectedEvidenceLinks: accuracyPublicationAvailable ? 5 : 30,
    expectedNominationFields: 2,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: accuracyPublicationAvailable ? 0 : 7,
    expectedArmSections: 0,
    expectedHorizontalRegions: 1,
  },
  {
    name: "home-mobile",
    path: "/",
    width: 390,
    height: 844,
    expectedLedgerRows: accuracyPublicationAvailable ? 5 : 30,
    expectedEvidenceLinks: accuracyPublicationAvailable ? 5 : 30,
    expectedNominationFields: 2,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: accuracyPublicationAvailable ? 0 : 7,
    expectedArmSections: 0,
    expectedHorizontalRegions: 1,
  },
  {
    name: "home-narrow",
    path: "/",
    width: 320,
    height: 700,
    expectedLedgerRows: accuracyPublicationAvailable ? 5 : 30,
    expectedEvidenceLinks: accuracyPublicationAvailable ? 5 : 30,
    expectedNominationFields: 2,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: accuracyPublicationAvailable ? 0 : 7,
    expectedArmSections: 0,
    expectedHorizontalRegions: 1,
  },
  {
    name: "accuracy-study-desktop",
    path: "/studies/260723346",
    width: 1440,
    height: 900,
    expectedLedgerRows: 5,
    expectedEvidenceLinks: 5,
    expectedNominationFields: 0,
    expectedExtensionOptions: 6,
    expectedSignalVerdicts: 0,
    expectedArmSections: 0,
    expectedHorizontalRegions: 2,
    expectedAccuracyVariance: 1,
  },
  {
    name: "accuracy-study-mobile",
    path: "/studies/260723346",
    width: 390,
    height: 844,
    expectedLedgerRows: 5,
    expectedEvidenceLinks: 5,
    expectedNominationFields: 0,
    expectedExtensionOptions: 6,
    expectedSignalVerdicts: 0,
    expectedArmSections: 0,
    expectedHorizontalRegions: 2,
    expectedAccuracyVariance: 1,
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
    expectedHorizontalRegions: 2,
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
    expectedHorizontalRegions: 2,
  },
  {
    name: "study-tablet",
    path: "/studies/260725091",
    width: 768,
    height: 900,
    expectedLedgerRows: 30,
    expectedEvidenceLinks: 30,
    expectedNominationFields: 0,
    expectedExtensionOptions: 5,
    expectedSignalVerdicts: 7,
    expectedArmSections: 0,
    expectedHorizontalRegions: 2,
  },
  {
    name: "arm-evidence-desktop",
    path: "/studies/260725091/arms/R-pythia-70m-tinystories-s42#comparison",
    width: 1440,
    height: 900,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
    expectedArmTabs: 5,
    expectedActiveTab: "Comparison",
    expectedUnavailableHeading: "Detailed attempt records are not yet public",
    expectedIntervalPlots: 1,
    expectedVisibleIntervalPlots: 1,
    expectedHorizontalRegions: 0,
  },
  {
    name: "arm-evidence-mobile",
    path: "/studies/260725091/arms/R-pythia-70m-tinystories-s42#provenance",
    width: 390,
    height: 844,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
    expectedArmTabs: 5,
    expectedActiveTab: "Provenance",
    expectedUnavailableHeading: "Detailed attempt records are not yet public",
    expectedIntervalPlots: 1,
    expectedVisibleIntervalPlots: 0,
    expectedHorizontalRegions: 0,
  },
  {
    name: "arm-interval-mobile",
    path: "/studies/260725091/arms/R-pythia-70m-tinystories-s42#comparison",
    width: 390,
    height: 844,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
    expectedArmTabs: 5,
    expectedActiveTab: "Comparison",
    expectedUnavailableHeading: "Detailed attempt records are not yet public",
    expectedIntervalPlots: 1,
    expectedVisibleIntervalPlots: 1,
    expectedHorizontalRegions: 0,
  },
  {
    name: "arm-interval-narrow",
    path: "/studies/260725091/arms/R-pythia-70m-tinystories-s42#comparison",
    width: 320,
    height: 700,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
    expectedArmTabs: 5,
    expectedActiveTab: "Comparison",
    expectedUnavailableHeading: "Detailed attempt records are not yet public",
    expectedIntervalPlots: 1,
    expectedVisibleIntervalPlots: 1,
    expectedHorizontalRegions: 0,
  },
  {
    name: "accuracy-run-desktop",
    path: "/studies/260723346/arms/seed-0#comparison",
    width: 1440,
    height: 900,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
    expectedArmTabs: 5,
    expectedActiveTab: "Comparison",
    expectedIntervalPlots: 0,
    expectedVisibleIntervalPlots: 0,
    expectedHorizontalRegions: 2,
    expectedAccuracyBars: 4,
    expectedSingleSeedLabel: true,
  },
  {
    name: "accuracy-run-mobile",
    path: "/studies/260723346/arms/seed-3#provenance",
    width: 390,
    height: 844,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 5,
    expectedArmTabs: 5,
    expectedActiveTab: "Provenance",
    expectedIntervalPlots: 0,
    expectedVisibleIntervalPlots: 0,
    expectedHorizontalRegions: 2,
    expectedAccuracyBars: 4,
    expectedSingleSeedLabel: true,
  },
  {
    name: "papers-desktop",
    path: "/papers",
    width: 1440,
    height: 900,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 0,
    expectedHorizontalRegions: 0,
    expectedCandidateRows: 25,
    voteResponse: "success",
  },
  {
    name: "papers-mobile-rate-limit",
    path: "/papers",
    width: 390,
    height: 844,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 0,
    expectedHorizontalRegions: 0,
    expectedCandidateRows: 25,
    voteResponse: "rate-limit",
  },
  {
    name: "papers-narrow",
    path: "/papers",
    width: 320,
    height: 700,
    expectedLedgerRows: 0,
    expectedEvidenceLinks: 0,
    expectedNominationFields: 0,
    expectedExtensionOptions: 0,
    expectedSignalVerdicts: 0,
    expectedArmSections: 0,
    expectedHorizontalRegions: 0,
    expectedCandidateRows: 25,
    voteResponse: "success",
  },
].filter(
  (scenario) =>
    accuracyPublicationAvailable || !scenario.name.startsWith("accuracy-"),
);

const report = [];
let failed = false;

for (const scenario of scenarios) {
  const page = await browser.newPage({
    viewport: { width: scenario.width, height: scenario.height },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });

  if (scenario.expectedCandidateRows) {
    const voteCounts = new Map(
      testCandidatePapers.map((paper) => [paper.id, paper.vote_count]),
    );
    await page.route("**/api/paper-queue", async (route) => {
      await route.fulfill({
        contentType: "application/json",
        json: {
          schema_version: 1,
          generated_at_utc: "2026-07-31T23:00:00Z",
          voting: {
            enabled: true,
            policy_version: "browser-test-v1",
          },
          papers: testCandidatePapers.map((paper) => ({
            ...paper,
            vote_count: voteCounts.get(paper.id),
          })),
        },
        status: 200,
      });
    });
    await page.route("**/api/paper-votes", async (route) => {
      if (scenario.voteResponse === "rate-limit") {
        await route.fulfill({
          contentType: "application/json",
          headers: { "Retry-After": "120" },
          json: { error: "rate_limited" },
          status: 429,
        });
        return;
      }

      const request = route.request().postDataJSON();
      const currentCount = voteCounts.get(request.paper_id);
      if (currentCount === undefined) {
        await route.fulfill({
          contentType: "application/json",
          json: { error: "not_found" },
          status: 404,
        });
        return;
      }
      const nextCount = currentCount + 1;
      voteCounts.set(request.paper_id, nextCount);
      await route.fulfill({
        contentType: "application/json",
        json: {
          ok: true,
          paper_id: request.paper_id,
          vote_count: nextCount,
          duplicate: false,
          reference: "pv_browser_test",
        },
        status: 201,
      });
    });
  }

  const response = await page.goto(`${baseUrl}${scenario.path}`, {
    waitUntil: "networkidle",
  });
  await page.evaluate(() => document.fonts.ready);
  if (scenario.expectedCandidateRows) {
    await page.waitForFunction(
      (expected) =>
        document.querySelectorAll(".paper-candidate").length === expected,
      scenario.expectedCandidateRows,
    );
  }
  if (scenario.expectedActiveTab) {
    await page.waitForFunction(
      (expected) =>
        document
          .querySelector('.arm-tabs [role="tab"][aria-selected="true"]')
          ?.textContent?.trim() === expected,
      scenario.expectedActiveTab,
    );
  }

  const diagnostics = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const overflowingElements = [...document.querySelectorAll("body *")]
      .filter((element) => {
        if (element.closest(".table-scroll")) return false;
        if (element.closest(".arm-tabs__list")) return false;
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
      nominationButton: document.querySelector(".nomination-form__submit")
        ?.textContent?.trim(),
      homeHeading: document.querySelector(".hero h1")?.textContent?.trim(),
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
      armTabs: document.querySelectorAll('.arm-tabs [role="tab"]').length,
      visibleArmPanels: document.querySelectorAll(
        '.arm-tabs [role="tabpanel"]:not([hidden])',
      ).length,
      activeArmTab: document
        .querySelector('.arm-tabs [role="tab"][aria-selected="true"]')
        ?.textContent?.trim(),
      stickyTabPosition: document.querySelector(".arm-tabs__sticky")
        ? getComputedStyle(document.querySelector(".arm-tabs__sticky")).position
        : undefined,
      intervalPlots: document.querySelectorAll(".arm-interval-plot").length,
      intervalPlotHeading: document.querySelector(".arm-interval-plot h3")
        ?.textContent?.trim(),
      visibleIntervalPlots: [...document.querySelectorAll(".arm-interval-plot")]
        .filter((element) => element.getClientRects().length > 0).length,
      accuracyVariancePlots: document.querySelectorAll(".accuracy-variance").length,
      accuracyResultBars: document.querySelectorAll(".accuracy-result-bar").length,
      singleSeedLabel: document
        .querySelector(".accuracy-arm-outcomes")
        ?.textContent?.includes("No per-seed replication verdict is assigned."),
      candidateRows: document.querySelectorAll(".paper-candidate").length,
      candidateSummary: document
        .querySelector(".paper-queue-summary")
        ?.textContent?.trim(),
      candidateFirstId: document
        .querySelector(".paper-candidate")
        ?.getAttribute("data-paper-id"),
      candidateVoteButtons: document.querySelectorAll(
        ".paper-candidate__vote button",
      ).length,
      closedCandidateDetails: document.querySelectorAll(
        ".paper-candidate__details:not([open])",
      ).length,
      candidateSortState: [...document.querySelectorAll(".paper-sort button")].map(
        (element) => ({
          label: element.textContent?.trim(),
          pressed: element.getAttribute("aria-pressed"),
        }),
      ),
      horizontalRegions: [
        ...document.querySelectorAll(".horizontal-scroll-region"),
      ].map((region) => {
        const content = region.querySelector(".table-scroll");
        const controls = region.querySelector(
          ".horizontal-scroll-region__controls",
        );
        const range = controls?.querySelector('input[type="range"]');
        const buttons = controls?.querySelectorAll("button");
        const maximumScroll = content.scrollWidth - content.clientWidth;
        return {
          maximumScroll,
          controlsHidden: controls.hidden,
          rangeMaximum: Number(range?.max),
          leftDisabled: buttons?.[0]?.disabled,
          rightDisabled: buttons?.[1]?.disabled,
        };
      }),
      intervalPlotContainment: [
        ...document.querySelectorAll(".arm-interval-plot"),
      ]
        .filter((element) => element.getClientRects().length > 0)
        .map((element) => {
          const plotRect = element.getBoundingClientRect();
          const shellRect = element.closest(".shell")?.getBoundingClientRect();
          return {
            withinViewport:
              plotRect.left >= -1 && plotRect.right <= viewportWidth + 1,
            withinShell:
              Boolean(shellRect) &&
              plotRect.left >= shellRect.left - 1 &&
              plotRect.right <= shellRect.right + 1,
          };
        }),
      bodyFontSize: Number.parseFloat(getComputedStyle(document.body).fontSize),
      primaryHeadingFontSize: Number.parseFloat(
        getComputedStyle(
          document.querySelector(
            ".hero h1, .study-hero h1, .arm-hero h1, .paper-queue-hero h1",
          ) ??
            document.body,
        ).fontSize,
      ),
      overflowingElements,
    };
  });

  const horizontalInteraction = await page.evaluate(async () => {
    const region = [...document.querySelectorAll(".horizontal-scroll-region")]
      .find((element) => {
        const content = element.querySelector(".table-scroll");
        return content.scrollWidth > content.clientWidth + 1;
      });
    if (!region) return undefined;

    const content = region.querySelector(".table-scroll");
    const range = region.querySelector('input[type="range"]');
    const rightButton = region.querySelector(
      ".horizontal-scroll-region__controls button:last-child",
    );
    rightButton?.click();
    await new Promise(requestAnimationFrame);
    const result = {
      movedRight: content.scrollLeft > 1,
      rangeSynchronized:
        Math.abs(Number(range?.value) - content.scrollLeft) < 2,
    };
    content.scrollLeft = 0;
    await new Promise(requestAnimationFrame);
    return result;
  });

  let tabInteraction;
  if (scenario.expectedArmTabs) {
    tabInteraction = await page.evaluate(async (expectedActiveTab) => {
      const evidenceTab = [...document.querySelectorAll(".arm-tabs [role=tab]")]
        .find((element) => element.textContent?.trim() === "Evidence");
      const expectedTab = [...document.querySelectorAll(".arm-tabs [role=tab]")]
        .find((element) => element.textContent?.trim() === expectedActiveTab);
      const before = window.scrollY;
      const beforeTabTop = document
        .querySelector(".arm-tabs__sticky")
        ?.getBoundingClientRect().top;
      evidenceTab?.click();
      await new Promise(requestAnimationFrame);
      const after = window.scrollY;
      const maximumScroll = document.documentElement.scrollHeight - innerHeight;
      const afterTabTop = document
        .querySelector(".arm-tabs__sticky")
        ?.getBoundingClientRect().top;
      const evidenceSelected = evidenceTab?.getAttribute("aria-selected") === "true";
      expectedTab?.click();
      await new Promise(requestAnimationFrame);
      return {
        clickPreservedScroll:
          Math.abs(after - Math.min(before, maximumScroll)) < 2 &&
          (maximumScroll < before || Math.abs(afterTabTop - beforeTabTop) < 2),
        evidenceSelected,
        restoredActiveTab:
          expectedTab?.getAttribute("aria-selected") === "true",
      };
    }, scenario.expectedActiveTab);
  }

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

  let paperInteraction;
  if (scenario.expectedCandidateRows) {
    const newestFirstId = await page
      .locator(".paper-candidate")
      .first()
      .getAttribute("data-paper-id");
    await page.getByRole("button", { name: "Most votes" }).click();
    await page.waitForFunction(
      () =>
        document
          .querySelector(".paper-candidate")
          ?.getAttribute("data-paper-id") === "test-paper-074",
    );
    const mostVoted = page.locator(".paper-candidate").first();
    const countBefore = Number(
      await mostVoted.locator(".paper-candidate__vote strong").textContent(),
    );
    await mostVoted.locator(".paper-candidate__vote button").click();

    if (scenario.voteResponse === "rate-limit") {
      await page.waitForFunction(() =>
        document
          .querySelector(".paper-vote-notice")
          ?.textContent?.includes("network has been reached"),
      );
    } else {
      await page.waitForFunction(
        () =>
          document.querySelector(".paper-candidate__vote button")?.textContent ===
          "Recorded",
      );
    }

    const countAfter = Number(
      await mostVoted.locator(".paper-candidate__vote strong").textContent(),
    );
    const voteButtonText = await mostVoted
      .locator(".paper-candidate__vote button")
      .textContent();
    const voteNotice = await page.locator(".paper-vote-notice").textContent();
    await page.getByRole("button", { name: "Next →" }).click();
    const nextPageRows = await page.locator(".paper-candidate").count();
    const paginationText = await page
      .locator(".paper-queue-pagination span")
      .textContent();

    paperInteraction = {
      newestFirstId,
      mostVotedFirstId: "test-paper-074",
      countBefore,
      countAfter,
      voteButtonText,
      voteNotice,
      nextPageRows,
      paginationText,
    };
  }

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
    (scenario.path === "/" &&
      diagnostics.nominationButton !== "Submit nomination") ||
    (scenario.path === "/" &&
      diagnostics.homeHeading !== "No acceleration without replication.") ||
    diagnostics.extensionOptions !== scenario.expectedExtensionOptions ||
    (scenario.expectedExtensionOptions > 0 &&
      diagnostics.extensionButton !== "Vote to extend this paper") ||
    diagnostics.signalVerdicts !== scenario.expectedSignalVerdicts ||
    diagnostics.candidateRows !== (scenario.expectedCandidateRows ?? 0) ||
    (scenario.expectedCandidateRows > 0 &&
      (!diagnostics.candidateSummary?.includes("100 papers") ||
        diagnostics.candidateFirstId !== "test-paper-001" ||
        diagnostics.candidateVoteButtons !== 25 ||
        diagnostics.closedCandidateDetails !== 25 ||
        diagnostics.candidateSortState[0]?.pressed !== "true" ||
        diagnostics.candidateSortState[1]?.pressed !== "false" ||
        paperInteraction?.newestFirstId !== "test-paper-001" ||
        paperInteraction?.mostVotedFirstId !== "test-paper-074" ||
        paperInteraction?.countBefore !== 900 ||
        paperInteraction?.nextPageRows !== 25 ||
        !paperInteraction?.paginationText?.includes("26–50 of 100") ||
        (scenario.voteResponse === "success" &&
          (paperInteraction?.countAfter !== 901 ||
            paperInteraction?.voteButtonText !== "Recorded")) ||
        (scenario.voteResponse === "rate-limit" &&
          (paperInteraction?.countAfter !== 900 ||
            !paperInteraction?.voteNotice?.includes(
              "network has been reached",
            ))))) ||
    diagnostics.armSections.length !== scenario.expectedArmSections ||
    (scenario.expectedUnavailableHeading &&
      diagnostics.deeperEvidenceHeading !== scenario.expectedUnavailableHeading) ||
    diagnostics.armTabs !== (scenario.expectedArmTabs ?? 0) ||
    diagnostics.horizontalRegions.length !== scenario.expectedHorizontalRegions ||
    diagnostics.horizontalRegions.some(
      (region) =>
        region.controlsHidden !== (region.maximumScroll <= 1) ||
        (region.maximumScroll > 1 &&
          (Math.abs(region.rangeMaximum - region.maximumScroll) > 2 ||
            !region.leftDisabled ||
            region.rightDisabled)),
    ) ||
    (diagnostics.horizontalRegions.some((region) => region.maximumScroll > 1) &&
      (!horizontalInteraction?.movedRight ||
        !horizontalInteraction.rangeSynchronized)) ||
    diagnostics.intervalPlotContainment.some(
      (plot) => !plot.withinViewport || !plot.withinShell,
    ) ||
    diagnostics.bodyFontSize > 16 ||
    (scenario.path === "/" &&
      diagnostics.primaryHeadingFontSize > (scenario.width <= 760 ? 46 : 77)) ||
    (scenario.path.startsWith("/studies/") &&
      !scenario.path.includes("/arms/") &&
      diagnostics.primaryHeadingFontSize > (scenario.width <= 760 ? 40 : 62)) ||
    (scenario.path.includes("/arms/") &&
      diagnostics.primaryHeadingFontSize > (scenario.width <= 760 ? 37 : 54)) ||
    (scenario.path === "/papers" &&
      diagnostics.primaryHeadingFontSize > (scenario.width <= 760 ? 42 : 62)) ||
    diagnostics.visibleArmPanels !== (scenario.expectedArmTabs ? 1 : 0) ||
    diagnostics.activeArmTab !== scenario.expectedActiveTab ||
    diagnostics.stickyTabPosition !==
      (scenario.expectedArmTabs ? "sticky" : undefined) ||
    diagnostics.intervalPlots !==
      (scenario.expectedIntervalPlots ?? (scenario.expectedArmTabs ? 1 : 0)) ||
    ((scenario.expectedIntervalPlots ?? (scenario.expectedArmTabs ? 1 : 0)) > 0 &&
      diagnostics.intervalPlotHeading !==
        "Reward-difference estimates and conditional 95% intervals") ||
    diagnostics.visibleIntervalPlots !==
      (scenario.expectedVisibleIntervalPlots ?? 0) ||
    diagnostics.accuracyVariancePlots !==
      (scenario.expectedAccuracyVariance ?? 0) ||
    diagnostics.accuracyResultBars !== (scenario.expectedAccuracyBars ?? 0) ||
    diagnostics.singleSeedLabel !==
      (scenario.expectedSingleSeedLabel ? true : undefined) ||
    (scenario.expectedArmTabs &&
      (!tabInteraction?.clickPreservedScroll ||
        !tabInteraction.evidenceSelected ||
        !tabInteraction.restoredActiveTab)) ||
    accessibility.length > 0;
  failed ||= scenarioFailed;
  report.push({
    ...scenario,
    status: response?.status(),
    diagnostics,
    horizontalInteraction,
    tabInteraction,
    paperInteraction,
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

const unknownAccuracyArm = await fetch(
  baseUrl + "/studies/260723346/arms/seed-99",
  { redirect: "manual" },
);
if (unknownAccuracyArm.status !== 404) {
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

console.log(
  (unknownAccuracyArm.status === 404 ? "PASS" : "FAIL") +
    " unknown-accuracy-arm: HTTP " +
    unknownAccuracyArm.status,
);

if (failed) process.exitCode = 1;

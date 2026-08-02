import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const require = createRequire(import.meta.url);
const baseUrl = process.env.NULSPEC_TEST_URL ?? "http://127.0.0.1:4321";
const browserPath =
  process.env.NULSPEC_CHROME_PATH ?? "/usr/bin/google-chrome-stable";
const outputDir = resolve(process.cwd(), ".artifacts/review-screenshots");
const hash = (character) => character.repeat(64);

await mkdir(outputDir, { recursive: true });

const baseTask = {
  task_id: "study-260723346-r1",
  supersedes_task_id: null,
  superseded_by: null,
  packet_sha256: hash("a"),
  imported_at: "2026-08-01T18:20:00Z",
  priority: "urgent",
  queued_reason:
    "The final reviewer refused before returning findings, and neither supplemental response produced a schema-valid PASS decision.",
  submitted_at_utc: "2026-08-01T18:16:18Z",
  study: {
    study_id: "260723346",
    paper_title:
      "SPRKD: Effective Knowledge Distillation for Deep Neural Networks via Saddle Region Approximation",
    paper_url: "https://arxiv.org/abs/2607.23346v1",
    arxiv_id: "2607.23346v1",
    replication_assessment: "Not replicated",
    method_assessment: "Inconclusive",
  },
  source: {
    source_revision: "b".repeat(40),
    repository_url: "https://github.com/example/research",
    pull_request_url: "https://github.com/example/research/pull/18",
    review_packet_sha256: hash("c"),
    final_peer_review_sha256: hash("d"),
    supplemental_review_consensus_sha256: hash("e"),
    fable_action_closure_sha256: null,
  },
  brief:
    "# One-page result\n\nThe public final-result recipe did not reproduce the reported stable result. Five independent seeds showed substantial fresh-training variance.\n\nThe intended method remains inconclusive rather than disproved. A post-hoc loss-contract correction is reported separately and cannot rewrite the frozen classification.",
  evidence: [
    {
      id: "one-page",
      label: "One-page result",
      kind: "brief",
      url: "https://github.com/example/research/blob/revision/ONE_PAGE.md",
      sha256: hash("1"),
      summary: "Decision-oriented outcome and interpretation.",
    },
    {
      id: "report",
      label: "Full replication report",
      kind: "report",
      url: "https://github.com/example/research/blob/revision/REPORT.md",
      sha256: hash("2"),
      summary: "Methods, deviations, all runs, uncertainty, and limits.",
    },
    {
      id: "ledger",
      label: "External review ledger",
      kind: "ledger",
      url: "https://github.com/example/research/blob/revision/EXTERNAL_REVIEW_LEDGER.md",
      sha256: hash("3"),
      summary: "Append-only reviewer attempts, costs, and trace hashes.",
    },
  ],
  review_events: [
    {
      event_id: "FABLE-REFUSAL-20260801-001",
      reviewer: "Fable",
      provider: "Anthropic",
      model: "claude-fable-5",
      outcome: "reviewer_safeguard_refusal",
      validation: "technical_hard_fail",
      summary:
        "The one permitted final review was refused before any substantive finding was returned.",
      cost_usd: 3.224742,
      trace_sha256: hash("4"),
      consensus_eligible: false,
    },
    {
      event_id: "OR-REVIEW-20260801-001",
      reviewer: "GLM",
      provider: "OpenRouter",
      model: "z-ai/glm-versioned",
      outcome: "PASS",
      validation: "completed_invalid",
      summary:
        "The response declared PASS but paired it with the FAIL-only next step.",
      cost_usd: 0.04710276,
      trace_sha256: hash("5"),
      consensus_eligible: true,
    },
    {
      event_id: "OR-REVIEW-20260801-002",
      reviewer: "Kimi",
      provider: "OpenRouter",
      model: "moonshotai/kimi-versioned",
      outcome: "PASS",
      validation: "completed_invalid",
      summary: "The response reached its output limit before the JSON object closed.",
      cost_usd: 1.123173,
      trace_sha256: hash("6"),
      consensus_eligible: true,
    },
  ],
  review_cost_total_usd: 0,
  publication_gate: {
    reason:
      "The fail-closed reviewer contract now requires a human disposition of the exact packet.",
    question: "Should this exact release proceed or remain blocked?",
    status: "awaiting_human",
    action_allowed: true,
    decision: null,
  },
  author_email_gate: {
    subject: "Independent replication attempt of the paper experiment",
    body:
      "# Draft author email — not sent\n\nHello authors,\n\nWe attempted an independent replication of your reported result. Our frozen final-epoch result did not reproduce the table, while the intended method remains inconclusive.\n\nWe would value corrections and advice on how this first replication could be more useful and fair.\n\nBest,\n\nThe NULSPEC team\n",
    draft_sha256: hash("7"),
    recipients: [
      { name: "Corresponding author", email: "author@example.org" },
    ],
    status: "blocked_by_publication",
    action_allowed: false,
    decision: null,
  },
  complete: false,
  decisions: [],
};

// Use an exact finite value rather than letting a fixture typo obscure layout tests.
baseTask.review_cost_total_usd = baseTask.review_events.reduce(
  (total, event) => total + event.cost_usd,
  0,
);

const scenarios = [
  { name: "review-login-desktop", path: "/review/login", width: 1440, height: 900, kind: "login" },
  { name: "review-login-mobile", path: "/review/login", width: 390, height: 844, kind: "login" },
  { name: "review-login-narrow", path: "/review/login", width: 320, height: 700, kind: "login" },
  { name: "review-inbox-desktop", path: "/review", width: 1440, height: 900, kind: "inbox", exerciseDecision: true },
  { name: "review-inbox-mobile", path: "/review", width: 390, height: 844, kind: "inbox" },
  { name: "review-inbox-narrow", path: "/review", width: 320, height: 700, kind: "inbox" },
];

const browser = await chromium.launch({ executablePath: browserPath, headless: true });
const report = [];
let failed = false;

for (const scenario of scenarios) {
  const page = await browser.newPage({
    viewport: { width: scenario.width, height: scenario.height },
    reducedMotion: "reduce",
  });
  let decisionRequest;
  let task = structuredClone(baseTask);

  await page.route("**/api/review/session", async (route) => {
    if (scenario.kind === "login") {
      await route.fulfill({
        contentType: "application/json",
        json: { ok: false, error: "authentication_required" },
        status: 401,
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      json: {
        ok: true,
        reviewer: { username: "reviewer.one", display_name: "Reviewer One" },
        csrf_token: "browser-csrf-token",
        expires_at: "2026-08-02T06:00:00Z",
      },
      status: 200,
    });
  });

  await page.route("**/api/review/login", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { ok: false, error: "invalid_credentials" },
      status: 401,
    });
  });

  await page.route("**/api/review/tasks/*/decisions", async (route) => {
    decisionRequest = route.request().postDataJSON();
    task.publication_gate = {
      ...task.publication_gate,
      status: "approved",
      action_allowed: false,
      decision: {
        decision_id: "NHR-20260801-ABCDEF12",
        task_id: task.task_id,
        gate: "publication",
        decision: "APPROVE_RELEASE",
        reviewer_username: "reviewer.one",
        reviewer_display_name: "Reviewer One",
        notes: decisionRequest.notes,
        binding_sha256: task.packet_sha256,
        record_sha256: hash("8"),
        record: { schema_version: "nulspec-human-publication-disposition-v1" },
        decided_at: "2026-08-01T19:30:00Z",
      },
    };
    task.author_email_gate = {
      ...task.author_email_gate,
      status: "awaiting_human",
      action_allowed: true,
    };
    task.decisions = [task.publication_gate.decision];
    await route.fulfill({
      contentType: "application/json",
      json: { ok: true, task },
      status: 201,
    });
  });

  await page.route("**/api/review/tasks", async (route) => {
    const publicationWaiting = task.publication_gate.status === "awaiting_human" ? 1 : 0;
    const emailWaiting = task.author_email_gate.status === "awaiting_human" ? 1 : 0;
    await route.fulfill({
      contentType: "application/json",
      json: {
        ok: true,
        schema_version: "nulspec-human-review-inbox-v1",
        summary: {
          papers_waiting: publicationWaiting,
          emails_waiting: emailWaiting,
          emails_blocked: publicationWaiting,
          completed_tasks: 0,
          total_tasks: 1,
        },
        tasks: [task],
        recent_activity: [
          {
            event_type: "task_imported",
            username: null,
            task_id: task.task_id,
            gate: null,
            detail: { packet_sha256: task.packet_sha256 },
            created_at: "2026-08-01T18:20:00Z",
          },
        ],
      },
      status: 200,
    });
  });

  const response = await page.goto(`${baseUrl}${scenario.path}`, {
    waitUntil: "networkidle",
  });
  await page.evaluate(() => document.fonts.ready);
  if (scenario.kind === "inbox") {
    await page.waitForSelector("[data-review-task]");
  } else {
    await page.waitForSelector(".review-login-form input:not([disabled])");
  }

  let interaction;
  if (scenario.kind === "login" && scenario.width === 1440) {
    await page.getByLabel("Username").fill("reviewer.one");
    await page.getByLabel("Password").fill("wrong password value");
    await page.getByRole("button", { name: "Open review inbox" }).click();
    await page.waitForFunction(() =>
      document.querySelector('[role="status"]')?.textContent?.includes("not accepted"),
    );
    interaction = {
      genericError: await page.locator('[role="status"]').textContent(),
    };
  }

  if (scenario.exerciseDecision) {
    await page.getByLabel("Approve this release").check();
    await page.getByLabel("Decision rationale").fill(
      "I reviewed the exact evidence packet and the technical refusal returned no substantive finding.",
    );
    await page.getByText("I reviewed the evidence bound to task").click();
    await page.getByRole("button", { name: "Record final decision" }).click();
    await page.waitForFunction(() =>
      document.body.textContent?.includes("Approved") &&
      document.body.textContent?.includes("Awaiting Human"),
    );
    interaction = {
      decisionRequest,
      emailActionUnlocked:
        (await page.getByLabel("Approve exact draft").count()) === 1,
    };
  }

  const diagnostics = await page.evaluate((kind) => {
    const viewportWidth = document.documentElement.clientWidth;
    const overflowing = [...document.querySelectorAll("body *")]
      .filter((element) => {
        if (element.closest("pre")) return false;
        const rect = element.getBoundingClientRect();
        return rect.left < -1 || rect.right > viewportWidth + 1;
      })
      .slice(0, 10)
      .map((element) => ({
        tag: element.tagName,
        className: element.className,
        left: Math.round(element.getBoundingClientRect().left),
        right: Math.round(element.getBoundingClientRect().right),
      }));
    return {
      title: document.title,
      horizontalOverflow:
        document.documentElement.scrollWidth > viewportWidth || overflowing.length > 0,
      overflowing,
      brandMarks: document.querySelectorAll(".wordmark__mark").length,
      forms: document.querySelectorAll("form").length,
      loginFields: [...document.querySelectorAll(".review-login-form input")].map(
        (element) => element.getAttribute("name"),
      ),
      accountCreationLinks: [...document.querySelectorAll("a")].filter((element) =>
        /sign up|register|reset|invite|create account/i.test(element.textContent ?? ""),
      ).length,
      taskCount: document.querySelectorAll("[data-review-task]").length,
      evidenceCount: document.querySelectorAll(".review-evidence-list li").length,
      eventCount: document.querySelectorAll(".review-event-list article").length,
      gateCount: document.querySelectorAll(".review-gate").length,
      emailDrafts: document.querySelectorAll(".review-email-envelope pre").length,
      primaryHeadingSize: Number.parseFloat(
        getComputedStyle(document.querySelector("h1") ?? document.body).fontSize,
      ),
      kind,
    };
  }, scenario.kind);

  await page.screenshot({
    path: resolve(outputDir, `${scenario.name}.png`),
    fullPage: false,
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
      nodes: violation.nodes.map((node) => node.target),
    }));
  });

  const expected = scenario.kind === "login"
    ? diagnostics.forms === 1 &&
      diagnostics.loginFields.join(",") === "username,password" &&
      diagnostics.taskCount === 0
    : diagnostics.taskCount === 1 &&
      diagnostics.evidenceCount === 3 &&
      diagnostics.eventCount === 3 &&
      diagnostics.gateCount === 2 &&
      diagnostics.emailDrafts === 1;
  const interactionPassed = !scenario.exerciseDecision || (
    interaction?.decisionRequest?.gate === "publication" &&
    interaction?.decisionRequest?.decision === "APPROVE_RELEASE" &&
    interaction?.decisionRequest?.confirmed === true &&
    interaction?.decisionRequest?.binding_sha256 === hash("a") &&
    interaction?.emailActionUnlocked === true
  );
  const passed = Boolean(response?.ok()) &&
    !diagnostics.horizontalOverflow &&
    diagnostics.brandMarks === 1 &&
    diagnostics.accountCreationLinks === 0 &&
    diagnostics.primaryHeadingSize <= (scenario.width <= 620 ? 55 : 88) &&
    expected &&
    interactionPassed &&
    accessibility.length === 0;
  failed ||= !passed;
  report.push({ scenario, status: response?.status(), diagnostics, interaction, accessibility, passed });
  await page.close();
}

await browser.close();
await writeFile(
  resolve(outputDir, "review-browser-report.json"),
  `${JSON.stringify(report, null, 2)}\n`,
);

for (const item of report) {
  console.log(
    `${item.passed ? "PASS" : "FAIL"} ${item.scenario.name}: HTTP ${item.status}, ` +
      `${item.diagnostics.taskCount} tasks, ${item.accessibility.length} accessibility violations`,
  );
}

if (failed) process.exitCode = 1;

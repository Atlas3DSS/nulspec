export const PAPER_QUEUE_ENDPOINT = "/api/paper-queue";
export const PAPER_VOTE_ENDPOINT = "/api/paper-votes";
export const PAPER_QUEUE_FALLBACK = "/data/paper-queue.json";
export const PAPER_QUEUE_PAGE_SIZE = 25;

export type PaperQueueSort = "newest" | "votes";

export interface CandidatePaper {
  id: string;
  title: string;
  url: string;
  source_id?: string;
  authors: string[];
  published_at: string;
  venue?: string;
  topics: string[];
  summary: string;
  replication_case: string;
  audience_case: string;
  code_url?: string;
  data_url?: string;
  estimated_hardware?: string;
  estimated_runtime?: string;
  vote_count: number;
  viewer_has_voted: boolean;
}

export interface PaperQueuePayload {
  schema_version: 1;
  generated_at_utc: string | null;
  voting: {
    enabled: boolean;
    policy_version: string;
  };
  papers: CandidatePaper[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(
  record: Record<string, unknown>,
  key: string,
  maximumLength: number,
) {
  const value = record[key];
  if (
    typeof value !== "string" ||
    value.trim().length === 0 ||
    value.length > maximumLength
  ) {
    throw new Error(`Candidate paper field ${key} is invalid.`);
  }
  return value.trim();
}

function optionalString(
  record: Record<string, unknown>,
  key: string,
  maximumLength: number,
) {
  const value = record[key];
  if (value === undefined || value === null || value === "") return undefined;
  if (typeof value !== "string" || value.length > maximumLength) {
    throw new Error(`Candidate paper field ${key} is invalid.`);
  }
  return value.trim() || undefined;
}

function stringList(
  record: Record<string, unknown>,
  key: string,
  maximumItems: number,
  maximumLength: number,
) {
  const value = record[key];
  if (!Array.isArray(value) || value.length > maximumItems) {
    throw new Error(`Candidate paper field ${key} is invalid.`);
  }
  return value.map((item) => {
    if (
      typeof item !== "string" ||
      item.trim().length === 0 ||
      item.length > maximumLength
    ) {
      throw new Error(`Candidate paper field ${key} is invalid.`);
    }
    return item.trim();
  });
}

function httpsUrl(value: string, key: string) {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`Candidate paper field ${key} is invalid.`);
  }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password) {
    throw new Error(`Candidate paper field ${key} is invalid.`);
  }
  return parsed.toString();
}

function parsePaper(value: unknown): CandidatePaper {
  if (!isRecord(value)) throw new Error("Candidate paper must be an object.");

  const publishedAt = requiredString(value, "published_at", 40);
  if (Number.isNaN(Date.parse(publishedAt))) {
    throw new Error("Candidate paper field published_at is invalid.");
  }

  const voteCount = value.vote_count;
  if (!Number.isSafeInteger(voteCount) || Number(voteCount) < 0) {
    throw new Error("Candidate paper field vote_count is invalid.");
  }

  const optionalUrls = {
    code_url: optionalString(value, "code_url", 500),
    data_url: optionalString(value, "data_url", 500),
  };

  return {
    id: requiredString(value, "id", 160),
    title: requiredString(value, "title", 400),
    url: httpsUrl(requiredString(value, "url", 500), "url"),
    source_id: optionalString(value, "source_id", 160),
    authors: stringList(value, "authors", 100, 160),
    published_at: publishedAt,
    venue: optionalString(value, "venue", 160),
    topics: stringList(value, "topics", 16, 80),
    summary: requiredString(value, "summary", 2_000),
    replication_case: requiredString(value, "replication_case", 1_500),
    audience_case: requiredString(value, "audience_case", 1_500),
    code_url: optionalUrls.code_url
      ? httpsUrl(optionalUrls.code_url, "code_url")
      : undefined,
    data_url: optionalUrls.data_url
      ? httpsUrl(optionalUrls.data_url, "data_url")
      : undefined,
    estimated_hardware: optionalString(value, "estimated_hardware", 240),
    estimated_runtime: optionalString(value, "estimated_runtime", 240),
    vote_count: Number(voteCount),
    viewer_has_voted: value.viewer_has_voted === true,
  };
}

export function parsePaperQueuePayload(value: unknown): PaperQueuePayload {
  if (!isRecord(value) || value.schema_version !== 1) {
    throw new Error("Candidate paper response has an unsupported schema.");
  }
  if (!Array.isArray(value.papers) || value.papers.length > 500) {
    throw new Error("Candidate paper response has an invalid paper list.");
  }
  if (!isRecord(value.voting)) {
    throw new Error("Candidate paper response has an invalid voting policy.");
  }

  const generatedAt = value.generated_at_utc;
  if (
    generatedAt !== null &&
    (typeof generatedAt !== "string" || Number.isNaN(Date.parse(generatedAt)))
  ) {
    throw new Error("Candidate paper response has an invalid generation time.");
  }

  const policyVersion = value.voting.policy_version;
  if (
    typeof value.voting.enabled !== "boolean" ||
    typeof policyVersion !== "string" ||
    policyVersion.trim().length === 0 ||
    policyVersion.length > 80
  ) {
    throw new Error("Candidate paper response has an invalid voting policy.");
  }

  const papers = value.papers.map(parsePaper);
  const identifiers = new Set(papers.map((paper) => paper.id));
  if (identifiers.size !== papers.length) {
    throw new Error("Candidate paper response contains duplicate identifiers.");
  }

  return {
    schema_version: 1,
    generated_at_utc: generatedAt,
    voting: {
      enabled: value.voting.enabled,
      policy_version: policyVersion.trim(),
    },
    papers,
  };
}

export function sortCandidatePapers(
  papers: CandidatePaper[],
  sort: PaperQueueSort,
) {
  return [...papers].sort((left, right) => {
    const dateDifference =
      Date.parse(right.published_at) - Date.parse(left.published_at);
    const voteDifference = right.vote_count - left.vote_count;
    if (sort === "votes") {
      return voteDifference || dateDifference || left.id.localeCompare(right.id);
    }
    return dateDifference || voteDifference || left.id.localeCompare(right.id);
  });
}

export function formatPaperDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
}

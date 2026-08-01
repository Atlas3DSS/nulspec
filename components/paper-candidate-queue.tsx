"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  PAPER_QUEUE_ENDPOINT,
  PAPER_QUEUE_FALLBACK,
  PAPER_QUEUE_PAGE_SIZE,
  PAPER_VOTE_ENDPOINT,
  formatPaperDate,
  parsePaperQueuePayload,
  sortCandidatePapers,
  type CandidatePaper,
  type PaperQueuePayload,
  type PaperQueueSort,
} from "@/lib/paper-queue";

const PRODUCTION_ORIGIN = "https://nulspec.com";

type QueueSource = "live" | "snapshot";

interface QueueLoadResult {
  payload: PaperQueuePayload;
  source: QueueSource;
}

interface VoteResponse {
  duplicate?: boolean;
  paper_id?: string;
  reference?: string;
  vote_count?: number;
}

function canonicalApiEndpoint(path: string) {
  if (
    typeof window !== "undefined" &&
    window.location.hostname.endsWith(".chatgpt.site")
  ) {
    return PRODUCTION_ORIGIN + path;
  }
  return path;
}

async function fetchQueue(signal: AbortSignal): Promise<QueueLoadResult> {
  const sources = [
    { endpoint: canonicalApiEndpoint(PAPER_QUEUE_ENDPOINT), source: "live" as const },
    { endpoint: PAPER_QUEUE_FALLBACK, source: "snapshot" as const },
  ];
  let lastError: Error | undefined;

  for (const source of sources) {
    try {
      const response = await fetch(source.endpoint, {
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal,
      });
      if (!response.ok) {
        throw new Error(`Candidate paper request returned ${response.status}.`);
      }
      return {
        payload: parsePaperQueuePayload(await response.json()),
        source: source.source,
      };
    } catch (error) {
      if (signal.aborted) throw error;
      lastError = error instanceof Error ? error : new Error("Request failed.");
    }
  }

  throw lastError ?? new Error("Candidate paper data is unavailable.");
}

function authorLine(paper: CandidatePaper) {
  if (paper.authors.length === 0) return "Authors not supplied";
  if (paper.authors.length <= 3) return paper.authors.join(", ");
  return `${paper.authors.slice(0, 3).join(", ")} +${paper.authors.length - 3} more`;
}

function queueTimestamp(value: string | null) {
  if (!value) return "Awaiting first candidate set";
  return `Updated ${new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value))} UTC`;
}

export function PaperCandidateQueue() {
  const [papers, setPapers] = useState<CandidatePaper[]>([]);
  const [sort, setSort] = useState<PaperQueueSort>("newest");
  const [page, setPage] = useState(1);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [queueSource, setQueueSource] = useState<QueueSource>("snapshot");
  const [votingEnabled, setVotingEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [votingPaperId, setVotingPaperId] = useState<string | null>(null);
  const [voteNotice, setVoteNotice] = useState("");

  async function load(signal: AbortSignal, requestedSort?: PaperQueueSort) {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await fetchQueue(signal);
      setPapers(result.payload.papers);
      setGeneratedAt(result.payload.generated_at_utc);
      setVotingEnabled(result.payload.voting.enabled);
      setQueueSource(result.source);
      setPage(1);
      if (requestedSort) setSort(requestedSort);
    } catch (error) {
      if (signal.aborted) return;
      setLoadError(
        error instanceof Error
          ? error.message
          : "Candidate paper data is unavailable.",
      );
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }

  useEffect(() => {
    const requestedSort = new URLSearchParams(window.location.search).get("sort");
    const controller = new AbortController();
    void fetchQueue(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setPapers(result.payload.papers);
        setGeneratedAt(result.payload.generated_at_utc);
        setVotingEnabled(result.payload.voting.enabled);
        setQueueSource(result.source);
        if (requestedSort === "votes") setSort("votes");
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setLoadError(
          error instanceof Error
            ? error.message
            : "Candidate paper data is unavailable.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const sortedPapers = useMemo(
    () => sortCandidatePapers(papers, sort),
    [papers, sort],
  );
  const pageCount = Math.max(
    1,
    Math.ceil(sortedPapers.length / PAPER_QUEUE_PAGE_SIZE),
  );
  const safePage = Math.min(page, pageCount);
  const pageStart = (safePage - 1) * PAPER_QUEUE_PAGE_SIZE;
  const visiblePapers = sortedPapers.slice(
    pageStart,
    pageStart + PAPER_QUEUE_PAGE_SIZE,
  );

  function selectSort(nextSort: PaperQueueSort) {
    setSort(nextSort);
    setPage(1);
    const url = new URL(window.location.href);
    if (nextSort === "newest") url.searchParams.delete("sort");
    else url.searchParams.set("sort", nextSort);
    window.history.replaceState(window.history.state, "", url);
  }

  async function refreshQueue() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12_000);
    await load(controller.signal);
    window.clearTimeout(timeout);
  }

  async function submitVote(paper: CandidatePaper) {
    if (!votingEnabled || paper.viewer_has_voted || votingPaperId) return;

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12_000);
    setVotingPaperId(paper.id);
    setVoteNotice(`Submitting vote for ${paper.title}.`);

    try {
      const response = await fetch(canonicalApiEndpoint(PAPER_VOTE_ENDPOINT), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_id: paper.id, company: "" }),
        signal: controller.signal,
      });
      const payload = (await response.json().catch(() => null)) as VoteResponse | null;

      if (!response.ok) {
        if (response.status === 404 || response.status === 422) {
          throw new Error("This candidate is no longer open for voting. Refresh the queue.");
        }
        if (response.status === 429) {
          const retryAfter = Number(response.headers.get("Retry-After"));
          const retryText = Number.isFinite(retryAfter)
            ? ` Try again in about ${Math.max(1, Math.ceil(retryAfter / 60))} minute(s).`
            : " Try again later.";
          throw new Error("The voting limit for this network has been reached." + retryText);
        }
        throw new Error("The vote could not be recorded. Try again.");
      }

      const returnedCount = payload?.vote_count;
      setPapers((current) =>
        current.map((item) =>
          item.id === paper.id
            ? {
                ...item,
                viewer_has_voted: true,
                vote_count:
                  Number.isSafeInteger(returnedCount) && Number(returnedCount) >= 0
                    ? Number(returnedCount)
                    : item.vote_count + (payload?.duplicate ? 0 : 1),
              }
            : item,
        ),
      );
      setVoteNotice(
        payload?.duplicate
          ? `A vote for ${paper.title} was already recorded for this network.`
          : `Vote recorded for ${paper.title}.`,
      );
    } catch (error) {
      setVoteNotice(
        error instanceof Error && error.name !== "AbortError"
          ? error.message
          : "The vote submission timed out. Try again.",
      );
    } finally {
      window.clearTimeout(timeout);
      setVotingPaperId(null);
    }
  }

  return (
    <section className="paper-queue-section" aria-labelledby="candidate-list-heading">
      <div className="shell">
        <div className="paper-queue-toolbar">
          <div>
            <p className="section-kicker" id="candidate-list-heading">
              Candidate list
            </p>
            <p className="paper-queue-summary">
              <strong>{papers.length}</strong> papers · {queueTimestamp(generatedAt)}
              {queueSource === "snapshot" ? " · published snapshot" : " · live totals"}
            </p>
          </div>
          <div className="paper-queue-controls">
            <div className="paper-sort" aria-label="Sort candidate papers">
              <button
                aria-pressed={sort === "newest"}
                onClick={() => selectSort("newest")}
                type="button"
              >
                Newest first
              </button>
              <button
                aria-pressed={sort === "votes"}
                onClick={() => selectSort("votes")}
                type="button"
              >
                Most votes
              </button>
            </div>
            <button
              className="paper-queue-refresh"
              disabled={loading}
              onClick={() => void refreshQueue()}
              type="button"
            >
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>

        <p className="paper-vote-policy">
          Voting does not require an account. The service processes the request IP
          address to limit repeat and high-frequency voting; addresses are not included
          in the public totals.
        </p>

        <p className="paper-vote-notice" role="status">
          {voteNotice}
        </p>

        {loadError ? (
          <div className="paper-queue-message" role="alert">
            <h2>Candidate data is unavailable</h2>
            <p>{loadError}</p>
            <button className="button button--secondary" onClick={() => void refreshQueue()} type="button">
              Try again
            </button>
          </div>
        ) : null}

        {!loadError && loading && papers.length === 0 ? (
          <div className="paper-queue-message" role="status">
            <h2>Loading candidate papers</h2>
            <p>Retrieving the current candidate set and vote totals.</p>
          </div>
        ) : null}

        {!loadError && !loading && papers.length === 0 ? (
          <div className="paper-queue-message">
            <h2>No candidate papers have been published yet</h2>
            <p>The queue will appear here when the first reviewed candidate set is available.</p>
            <Link className="button button--secondary" href="/#nominate">
              Nominate a paper
            </Link>
          </div>
        ) : null}

        {visiblePapers.length > 0 ? (
          <ol className="paper-candidate-list" start={pageStart + 1}>
            {visiblePapers.map((paper, index) => {
              const isVoting = votingPaperId === paper.id;
              const isDisabled =
                !votingEnabled || paper.viewer_has_voted || votingPaperId !== null;
              return (
                <li className="paper-candidate" data-paper-id={paper.id} key={paper.id}>
                  <span className="paper-candidate__number" aria-hidden="true">
                    {String(pageStart + index + 1).padStart(3, "0")}
                  </span>
                  <article className="paper-candidate__body">
                    <div className="paper-candidate__meta">
                      <time dateTime={paper.published_at}>
                        {formatPaperDate(paper.published_at)}
                      </time>
                      {paper.venue ? <span>{paper.venue}</span> : null}
                      {paper.source_id ? <span>{paper.source_id}</span> : null}
                      {paper.topics.map((topic) => (
                        <span className="paper-topic" key={topic}>{topic}</span>
                      ))}
                    </div>
                    <h2>
                      <a href={paper.url}>{paper.title}</a>
                    </h2>
                    <p className="paper-candidate__authors">{authorLine(paper)}</p>
                    <p className="paper-candidate__summary">{paper.summary}</p>
                    <details className="paper-candidate__details">
                      <summary>Replication assessment</summary>
                      <div className="paper-candidate__detail-grid">
                        <div>
                          <h3>Replication case</h3>
                          <p>{paper.replication_case}</p>
                        </div>
                        <div>
                          <h3>Audience relevance</h3>
                          <p>{paper.audience_case}</p>
                        </div>
                        <div>
                          <h3>Estimated resources</h3>
                          <p>
                            {paper.estimated_hardware ?? "Hardware estimate pending"}
                            {paper.estimated_runtime
                              ? ` · ${paper.estimated_runtime}`
                              : ""}
                          </p>
                          <p className="paper-candidate__artifact-links">
                            {paper.code_url ? <a href={paper.code_url}>Code ↗</a> : null}
                            {paper.data_url ? <a href={paper.data_url}>Data ↗</a> : null}
                          </p>
                        </div>
                      </div>
                    </details>
                  </article>
                  <div className="paper-candidate__vote">
                    <strong>{paper.vote_count.toLocaleString("en")}</strong>
                    <span>{paper.vote_count === 1 ? "vote" : "votes"}</span>
                    <button
                      aria-label={`Vote to replicate ${paper.title}`}
                      disabled={isDisabled}
                      onClick={() => void submitVote(paper)}
                      type="button"
                    >
                      {paper.viewer_has_voted
                        ? "Recorded"
                        : isVoting
                          ? "Submitting…"
                          : votingEnabled
                            ? "+1 vote"
                            : "Voting soon"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : null}

        {sortedPapers.length > PAPER_QUEUE_PAGE_SIZE ? (
          <nav className="paper-queue-pagination" aria-label="Candidate paper pages">
            <button
              disabled={safePage === 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              type="button"
            >
              ← Previous
            </button>
            <span>
              Showing {pageStart + 1}–{Math.min(pageStart + PAPER_QUEUE_PAGE_SIZE, sortedPapers.length)} of {sortedPapers.length}
            </span>
            <button
              disabled={safePage === pageCount}
              onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
              type="button"
            >
              Next →
            </button>
          </nav>
        ) : null}
      </div>
    </section>
  );
}

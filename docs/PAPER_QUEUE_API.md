# Candidate paper queue API

The public candidate page reads paper metadata and current vote totals at
runtime. This keeps candidate ingestion independent of the website build and
allows the first set of 100 papers to appear as soon as the backend publishes
it.

The page uses two endpoints:

- `GET /api/paper-queue` returns the current candidate set and vote totals.
- `POST /api/paper-votes` records one anonymous vote for a candidate.

On the owner-only `*.chatgpt.site` mirror, requests go to the canonical
`https://nulspec.com` origin. The API must allow that exact mirror origin and
`https://nulspec.com`; it must not use a wildcard CORS policy.

## Queue response

`GET /api/paper-queue` responds with `200 application/json`:

```json
{
  "schema_version": 1,
  "generated_at_utc": "2026-07-31T23:00:00Z",
  "voting": {
    "enabled": true,
    "policy_version": "anonymous-network-v1"
  },
  "papers": [
    {
      "id": "arxiv-2607-12345",
      "title": "Example computational paper",
      "url": "https://arxiv.org/abs/2607.12345",
      "source_id": "arXiv:2607.12345",
      "authors": ["A. Researcher", "B. Researcher"],
      "published_at": "2026-07-29T00:00:00Z",
      "venue": "arXiv",
      "topics": ["machine learning", "evaluation"],
      "summary": "A factual summary of the study and its primary claim.",
      "replication_case": "Why the result can be tested end to end with accessible code, data, and compute.",
      "audience_case": "Who would use the result and why independent verification matters.",
      "code_url": "https://github.com/example/project",
      "data_url": "https://huggingface.co/datasets/example/data",
      "estimated_hardware": "1 × 24 GB GPU",
      "estimated_runtime": "8 GPU-hours",
      "vote_count": 41,
      "viewer_has_voted": false
    }
  ]
}
```

Requirements:

- `id` is an opaque, stable identifier. It must not change when metadata is
  corrected.
- `url`, `code_url`, and `data_url` use HTTPS. Code and data URLs are optional.
- `authors` and `topics` are arrays and may be empty.
- `published_at` and `generated_at_utc` are ISO 8601 timestamps. The generation
  time may be `null` in a static snapshot.
- `vote_count` is a non-negative integer.
- `viewer_has_voted` reflects the current requester's network/session state.
- A response may contain up to 500 candidates. The frontend sorts and paginates
  the response locally in pages of 25.
- Candidates do not have to be AI papers or arXiv papers. The contract is
  source-neutral so the replication program can expand to other computational
  fields.

The response should use `Cache-Control: private, no-store` while
`viewer_has_voted` is requester-specific. A future public-cache endpoint may
separate paper totals from viewer state without changing the paper objects.

## Vote request

`POST /api/paper-votes` accepts `application/json`:

```json
{
  "paper_id": "arxiv-2607-12345",
  "company": ""
}
```

`company` is a honeypot. A non-empty value should be rejected without recording
a vote.

A new vote responds with `201` (or `200`):

```json
{
  "ok": true,
  "paper_id": "arxiv-2607-12345",
  "vote_count": 42,
  "duplicate": false,
  "reference": "pv_opaque_reference"
}
```

A repeated vote for the same paper should be idempotent and return `200` with
`duplicate: true` and the unchanged current count. The frontend treats both
responses as a recorded vote.

Supported error states:

- `400` — malformed JSON or unexpected fields
- `404` — candidate does not exist
- `413` — request body too large
- `415` — unsupported content type
- `422` — voting is closed for this candidate
- `429` — network or global rate limit reached; include `Retry-After` in seconds
- `503` — voting is temporarily unavailable

Error bodies may include a short `error` string, but the frontend does not
display server-provided error text.

## Initial anonymous-vote policy

The POC backend should persist votes and enforce both duplicate and burst
controls:

1. Normalize the client address only after it has crossed the trusted reverse
   proxy boundary.
2. Derive a keyed HMAC-SHA256 network digest. Do not store a raw address or an
   unkeyed hash of it.
3. Enforce a unique constraint on `(paper_id, network_digest)`.
4. Limit the number of distinct-paper votes from one digest over a rolling
   window, and apply a separate global burst limit.
5. Return `429` with `Retry-After` when a burst limit is reached.
6. Trust the client-IP forwarding header only from the loopback proxy.

The exact limits are backend policy. A practical low-traffic starting point is
10 distinct-paper votes per network per hour plus a conservative global burst
limit. Shared networks will occasionally collide; the UI describes the rule as
a network limit instead of claiming a person-level identity check.

## Upgrade hooks

`voting.policy_version` makes a policy change visible without a schema change.
The stable paper ID, `viewer_has_voted`, idempotent duplicate response, and
separate vote endpoint leave room for signed anonymous sessions, challenge
tokens, device attestation, or accounts later. Those controls should remain
server decisions; the frontend only needs the same request and response shape.

## Static handoff

The repository retains the last static snapshot at
`site-data/public-archive/data/paper-queue.json`. The build validates that
archived file, but placeholder mode does not deploy it. A later public-site
release can promote a validated snapshot when voting endpoints are restored.

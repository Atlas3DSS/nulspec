# Human-review dashboard

## Purpose

The private dashboard at `/review/login` is the final human workspace for
release-governance tasks. It shows, in one place:

- papers waiting for a human publication disposition;
- the precise reason each release is blocked;
- the one-page research brief, linked evidence, immutable hashes, external
  reviewer outcomes, retained trace hashes, and provider costs;
- exact author-email drafts and their bound recipient lists;
- separate publication and email actions; and
- append-only decisions and queue history.

There is no registration, invitation, password-reset, account-discovery, or
profile-management surface. Accounts are provisioned only by an operator in a
root-owned environment file.

## Gate semantics

The dashboard implements two deliberately separate transitions.

1. A `HARD_FAIL` or another configured release block requires a human to record
   either `APPROVE_RELEASE` or `KEEP_BLOCKED` against the immutable task packet.
   Approval is release governance only; it cannot change scientific evidence,
   a protocol, number, classification, or claim.
2. Only an approved publication can expose the email action. The exact draft
   and recipient list then receive `APPROVE_SEND` or `RETURN_FOR_REVISION`.
   `APPROVE_SEND` authorizes later operator dispatch but does not send mail.

Every gate accepts one decision. It cannot be overwritten. Material changes
require a new task ID and a newly hashed task packet. An email with no recipient
list remains visibly blocked even after publication approval.

## Architecture and threat boundary

The canonical website is a static Next.js export. The two reviewer pages are
therefore data-free client shells. They contain no account data, task packet,
email draft, or decision at build time. Caddy proxies only `GET` and `POST`
requests under `/api/review/*` to the existing loopback Flask service.

The service keeps a dedicated SQLite database under `/var/lib/multibot` with
mode `0600`, WAL journaling, full synchronous writes, foreign keys, and
append-only gate decisions. Task imports and machine exports are CLI operations;
there is no public task-creation endpoint.

Authentication uses:

- operator-created Werkzeug scrypt password hashes, never plaintext passwords;
- an opaque 256-bit session token whose SHA-256—not the token—is stored;
- a `Secure`, `HttpOnly`, host-only, `SameSite=Strict` cookie;
- server-derived per-session CSRF tokens plus exact same-origin checks for every
  state-changing request;
- durable per-client and per-username login throttling, generic credential
  errors, and a two-slot scrypt concurrency guard; and
- server-side session revocation on logout or account removal.

Caddy applies `no-store`, `noindex`, a restrictive review-page Content Security
Policy, a 16 KiB request limit, and the site's existing HSTS, frame, MIME, and
permissions headers. The application repeats no-cache and response-hardening
headers on every private API response.

## Provision reviewer accounts

Use the service virtual environment so the CLI and production runtime use the
same pinned Flask and Werkzeug packages.

```bash
/srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py hash-password
```

Create a root-readable file outside the repository. Paste only the generated
scrypt hash into each account record. Use neutral reviewer display labels if a
decision export will enter a public research repository.

```json
{
  "schema_version": "nulspec-reviewer-accounts-v1",
  "accounts": [
    {
      "username": "reviewer.one",
      "display_name": "NULSPEC human reviewer 01",
      "password_hash": "scrypt:32768:8:1$replace-with-generated-value",
      "roles": ["reviewer"]
    }
  ]
}
```

Encode the envelope and generate an independent service pepper:

```bash
/srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py encode-accounts \
  --input /etc/nulspec-review-accounts.json

/srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py generate-pepper
```

Copy both emitted assignments into `/etc/nulspec-review.env`, alongside the
non-secret settings in `infra/multibot/nulspec-review.env.example`, then set
ownership to `root:root` and mode `0600`. Validate without printing either
secret:

```bash
set -a
. /etc/nulspec-review.env
set +a
NULSPEC_REVIEW_DB_PATH=:memory: /srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py check-config
```

The `:memory:` override validates credentials, scrypt parameters, pepper,
origins, cookie policy, and session settings without opening or changing the
live service database as root.

The service intentionally has no default account and stays disabled when the
environment file is absent or invalid.

## Queue a study

The standard adapter reads the frozen research handoff, one-page explainer,
report, protocol, verification log, final review, supplemental consensus,
external-review ledger, and author-email draft. It verifies the task schema and
reproduces the external-review cost total from the append-only events.

Keep the recipient file private:

```json
[
  {"name": "Corresponding author", "email": "author@example.org"}
]
```

Build and inspect the private task before import:

```bash
/srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py build-study-task \
  --study-root /path/to/study \
  --task-id STUDYID-release-r1 \
  --priority high \
  --source-revision FULL_GIT_COMMIT \
  --repository-url https://github.com/ORG/REPOSITORY \
  --pull-request-url https://github.com/ORG/REPOSITORY/pull/NUMBER \
  --study-repo-path research/replications/ARXIV_ID \
  --recipients /etc/nulspec-review-recipients/STUDYID.json \
  --output /var/lib/multibot/review-intake/STUDYID-release-r1.json

/srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py validate-packet \
  --packet /var/lib/multibot/review-intake/STUDYID-release-r1.json
```

Import is idempotent for identical bytes and fails if an existing task ID is
present with different content:

```bash
chown multibot:multibot \
  /var/lib/multibot/review-intake/STUDYID-release-r1.json

sudo -u multibot /srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py import-task \
  --packet /var/lib/multibot/review-intake/STUDYID-release-r1.json
```

Never run an import against the live SQLite database as root. The service user
must own the database, WAL files, intake directory, and export directory.

If any bound content changes, build a new task ID and explicitly name the active
packet it replaces:

```bash
/srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py build-study-task \
  --study-root /path/to/study \
  --task-id STUDYID-release-r2 \
  --supersedes-task-id STUDYID-release-r1 \
  --priority high \
  --source-revision FULL_GIT_COMMIT \
  --repository-url https://github.com/ORG/REPOSITORY \
  --pull-request-url https://github.com/ORG/REPOSITORY/pull/NUMBER \
  --study-repo-path research/replications/ARXIV_ID \
  --recipients /etc/nulspec-review-recipients/STUDYID.json \
  --output /var/lib/multibot/review-intake/STUDYID-release-r2.json
```

The service rejects an implicit replacement. After import, the old packet stays
visible as immutable history but cannot receive a decision; only the new active
packet is actionable.

## Export decisions back to research

After review, export the machine records to a private staging path:

```bash
sudo -u multibot /srv/multibot/venv/bin/python \
  /srv/multibot/current/nulspec_review.py export-decisions \
  --task-id STUDYID-release-r1 \
  --output /var/lib/multibot/review-exports/STUDYID-release-r1.json
```

The export binds the task packet, source revision, final review, supplemental
consensus, publication disposition, exact email draft, and a hash of the
recipient list. It omits recipient addresses from each machine decision record.
Research must validate and commit the applicable disposition before its own
release or dispatch gate opens. A dashboard decision alone never edits Git,
deploys the public site, or invokes the mail worker.

## Installation and validation

1. Install `nulspec_review.py`, `nulspec_review_store.py`, and the updated
   `server.py` with the existing multibot release.
2. Install `25-nulspec-review.conf` as a `multibot.service` drop-in, run
   `systemctl daemon-reload`, validate the environment, and restart the service.
3. Install and validate the updated Caddy configuration before reloading Caddy.
4. Deploy the static site only from a merged, validated revision.
5. Verify unauthenticated API requests return `401`, unknown account routes
   return `404`, login responses set all cookie attributes, and the login and
   dashboard layouts pass at 320, 390, and desktop widths.

Focused backend validation:

```bash
pytest -q tests/test_nulspec_review.py
```

Full repository validation remains required before merge.

## Recovery

Back up the review database with SQLite's online backup mechanism or while the
loopback service is stopped. Preserve the database, its WAL state, private task
packets, and exported decisions with mode `0600`. Restoring a prior static site
release does not restore private decisions; the database is deliberately
separate from `/srv/nulspec/current`.

Removing an account from the environment and reloading the service invalidates
its sessions at the next authenticated request. Rotating the pepper invalidates
every session and changes pseudonymous account/client digests; do that only as
an explicit security event.

## Implementation error record

### HREVIEW-LOCAL-001 — Wrong interpreter in first adapter smoke

The first read-only adapter smoke invoked the host's generic `python` command,
whose package path did not include Flask. Import stopped immediately with
`ModuleNotFoundError`; no task file or database row was created. The smoke was
re-run with the project-compatible Python 3 interpreter. It built the current
study packet, validated the exact packet hash, projected six review events and
seven evidence records, and reproduced the recorded external-review cost total.
This was a local validation-command error, not an error in a paper, upstream
repository, scientific result, reviewer response, or production service.

### HREVIEW-LOCAL-002 — Documentation patch used stale context

The first combined documentation patch expected a sentence that was not in the
current decision log and failed atomically. No file was partially changed. The
additions were split into exact-context patches and applied successfully.

### HREVIEW-LOCAL-003 — Node validation preceded dependency installation

The first typecheck and lint attempt in the new worktree ran before its locked
Node dependencies had been installed, so `tsc` and `eslint` were not found.
No source file changed. `npm ci` completed with zero audited vulnerabilities;
typecheck, lint, data validation, copy validation, and the static build then
passed.

### HREVIEW-LOCAL-004 — First local preview port was occupied

The first static-preview command attempted to bind the repository's usual local
test port and stopped with `address already in use`. It did not signal, replace,
or inspect the process already using that port. The review preview used a
different loopback port, completed all browser checks, and was stopped normally.

### HREVIEW-LOCAL-005 — Browser fixture contained an invalid draft number

While authoring the synthetic browser fixture, its temporary cost placeholder
contained an invalid JavaScript numeric token. It was corrected to a computed
sum before the script was executed. `node --check` then passed, and all six
desktop/mobile/narrow browser scenarios completed with zero accessibility or
overflow findings. This fixture never enters the application bundle or a
research result.

### HREVIEW-LOCAL-006 — Focused verification referenced a missing worktree venv

The first post-supersession verification command assumed the new Git worktree
contained its own `.venv`. The shell stopped at the missing executable before
running a formatter or test, and no file changed. The same focused formatter,
lint, and test sequence was immediately run with the installed repository tools;
all checks passed. This was our local command-path error, not an upstream or
research-code error.

### HREVIEW-LOCAL-007 — Combined validation used a nonexistent package alias

After data and copy checks passed, a combined validation command invoked
`npm run validate:repo`; this repository exposes its hygiene check as a Python
script rather than that package alias. npm stopped before the build step and no
source file changed. The hygiene script and remaining named build checks were
then invoked directly. This was our local command-name error.

### HREVIEW-LOCAL-008 — PR metadata check requested an unsupported CLI field

After draft PR creation, the first read-only verification query requested
`headRefOid`, which is unavailable in the host's installed GitHub CLI version.
The query stopped with its supported-field list; it did not modify the PR or
repository. Verification was repeated using fields supported by that version.

### HREVIEW-LOCAL-009 — Installed GitHub CLI lacks check-watch support

The first attempt to wait for PR checks used `gh pr checks --watch`, which is
not available in the host's GitHub CLI version. The command rejected the flag
before contacting or changing the PR. The two checks were then polled through
supported read-only PR metadata and both completed successfully.

### HREVIEW-EXTERNAL-001 — GitHub App could not create the draft PR

The preferred GitHub App call returned `403 Resource not accessible by
integration` after the branch was already pushed. No repository or PR state was
partially created by that call. The authenticated GitHub CLI fallback then
created draft PR #23 from the same pushed commit. This is recorded as an
external integration limitation rather than a NULSPEC source or research error.

## Pre-existing validation limitation

### HREVIEW-BASE-001 — Ignored upstream checkout absent from local worktree

The repository-wide local test run completed with **59 passed and 1 failed**.
The sole failure was the pre-existing
`tests/test_protocol.py::test_released_statistics_are_exactly_reconstructable`,
which expects the ignored reconstructed upstream file
`paper_repro/SLM-RL-Agents/results/all_results.json`. The focused review,
nomination, and mail suites passed. CI reconstructs the pinned upstream checkout
before running the full suite, so this local fixture absence is not attributed
to the dashboard and does not change a research result.

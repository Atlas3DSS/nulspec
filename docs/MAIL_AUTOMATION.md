# NULSPEC research mail automation

NULSPEC sends a single transactional result email when a nominated arXiv paper
appears in a completed public replication. Replies and delivery notices are
relayed to the private research-intake Discord channel. The system does not
send newsletters or marketing mail.

## Data flow

1. The nomination endpoint validates an email address and canonical arXiv URL.
2. It writes the nomination to `/var/lib/multibot/nulspec-mail.sqlite3` before
   acknowledging the request, then posts the private Discord intake embed.
3. The canonical site deployment writes a bounded `result_notification` into
   `release.json` from the reviewed publication bundle.
4. `nulspec-mail.service` matches the base arXiv ID, queues a stable message,
   and sends it through authenticated TLS SMTP.
5. After delivery, the database removes the raw contact address and retains
   only its SHA-256 deduplication digest, reference, paper ID, and audit state.
6. The IMAP poller forwards new replies to the private Discord channel. It
   lists attachment names but does not retain or forward attachment bodies.
   `allowed_mentions` is disabled.

Client IP addresses are used only by the in-process rate limiter and are never
written to the mail database. Existing provider mailbox content is skipped when
the IMAP cursor is initialized, preventing setup and welcome messages from
being relayed.

## Provider and DNS gate

Create `research@nulspec.com` at PurelyMail, fund the account, and make two
separate application passwords: one for SMTP and one for IMAP. Add the exact MX,
SPF, DKIM, and ownership records shown by PurelyMail to the authoritative
GoDaddy DNS zone. Preserve unrelated A, NS, SOA, and `_domainconnect` records.

There must be only one SPF TXT record at the zone apex. Merge PurelyMail's
include mechanism into an existing SPF policy instead of adding a second SPF
record. Keep DMARC in monitoring or quarantine mode until SPF and DKIM both
pass from a real completion-message test.

Install the two app passwords in `/etc/nulspec-mail.env` using
`nulspec-mail.env.example` as the shape. The live file is root-owned mode 0600
and is never committed.

## Safe activation

The service is installed disabled until DNS and credentials are ready. Before
enabling it:

```bash
sudo systemctl start nulspec-mail-backfill.service
sudo systemctl enable --now nulspec-mail.service
```

The backfill unit reads historical nomination embeds from Discord and emits
counts only; it does not print contact addresses. The mail service's
`ExecStartPre` validates credentials and the live publication contract before
the worker starts. Run the backfill before the initial mail-worker start so a
previously completed matching publication can generate its pending result
email.

After activation, verify `systemctl status`, zero error-priority journal lines,
the SQLite `PRAGMA quick_check`, one test delivery, SPF/DKIM/DMARC headers, and
one reply relay. Never paste an app password into a shell argument or log.

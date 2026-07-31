"""Durable, privacy-limited state for NULSPEC research correspondence."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REFERENCE_RE = re.compile(r"^NLS-[0-9]{8}-[A-F0-9]{6}$")
MESSAGE_ID_RE = re.compile(r"^<[A-Za-z0-9._@-]{1,240}>$")
ARXIV_VERSION_RE = re.compile(r"v[0-9]+$", re.IGNORECASE)


class MailStoreError(RuntimeError):
    """The correspondence database could not preserve a required transition."""


def utc_text(value: datetime) -> str:
    """Serialize one timestamp as an unambiguous UTC value."""
    if value.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def base_arxiv_id(arxiv_id: str) -> str:
    """Return the paper identity shared by all arXiv versions."""
    value = arxiv_id.strip().lower()
    if not value:
        raise ValueError("arXiv identifier is empty")
    return ARXIV_VERSION_RE.sub("", value)


def contact_digest(email: str) -> str:
    """Retain a deterministic deduplication key after contact redaction."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NominationClaim:
    reference: str
    created: bool
    discord_message_id: str | None


@dataclass(frozen=True)
class PendingNotification:
    outbox_id: int
    reference: str
    contact_email: str
    submitted_at: str
    study_id: str
    message_id: str
    notice: dict[str, object]
    attempts: int


class NominationStore:
    """Coordinate the intake process and mail worker through SQLite WAL state."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            database_path = Path(self.path)
            database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
            check_same_thread=False,
        )
        if self.path != ":memory:":
            Path(self.path).chmod(0o600)
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 10000")
            if self.path != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL")
                self._connection.execute("PRAGMA synchronous = FULL")
            self._initialize()

    def _initialize(self) -> None:
        self._connection.execute("PRAGMA secure_delete = ON")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS nominations (
                reference TEXT PRIMARY KEY,
                contact_email TEXT,
                contact_sha256 TEXT NOT NULL,
                arxiv_id TEXT NOT NULL,
                arxiv_base_id TEXT NOT NULL,
                paper_url TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                discord_message_id TEXT,
                notified_at TEXT,
                UNIQUE(contact_sha256, arxiv_base_id)
            );

            CREATE INDEX IF NOT EXISTS nominations_by_paper
                ON nominations(arxiv_base_id, discord_message_id);

            CREATE TABLE IF NOT EXISTS notification_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL REFERENCES nominations(reference),
                study_id TEXT NOT NULL,
                message_id TEXT NOT NULL UNIQUE,
                notice_json TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued'
                    CHECK(state IN ('queued', 'sending', 'retry', 'sent')),
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at REAL NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                UNIQUE(reference, study_id)
            );

            CREATE INDEX IF NOT EXISTS outbox_ready
                ON notification_outbox(state, next_attempt_at, id);

            CREATE TABLE IF NOT EXISTS mailbox_state (
                mailbox TEXT PRIMARY KEY,
                uidvalidity INTEGER NOT NULL,
                high_water_uid INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inbound_messages (
                mailbox TEXT NOT NULL,
                uidvalidity INTEGER NOT NULL,
                uid INTEGER NOT NULL,
                message_id TEXT,
                state TEXT NOT NULL
                    CHECK(state IN ('pending', 'delivered')),
                discord_message_id TEXT,
                received_at TEXT NOT NULL,
                PRIMARY KEY(mailbox, uidvalidity, uid)
            );

            PRAGMA user_version = 1;
            """
        )

    def _rollback(self) -> None:
        if self._connection.in_transaction:
            self._connection.execute("ROLLBACK")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def claim_nomination(
        self,
        *,
        reference: str,
        email: str,
        arxiv_id: str,
        paper_url: str,
        submitted_at: datetime,
    ) -> NominationClaim:
        """Create a durable intake row or return the matching prior claim."""
        if not REFERENCE_RE.fullmatch(reference):
            raise ValueError("nomination reference is invalid")
        email_value = email.strip().lower()
        values = (
            reference,
            email_value,
            contact_digest(email_value),
            arxiv_id,
            base_arxiv_id(arxiv_id),
            paper_url,
            utc_text(submitted_at),
        )
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                cursor = self._connection.execute(
                    """
                    INSERT INTO nominations(
                        reference, contact_email, contact_sha256, arxiv_id,
                        arxiv_base_id, paper_url, submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(contact_sha256, arxiv_base_id) DO NOTHING
                    """,
                    values,
                )
                row = self._connection.execute(
                    """
                    SELECT reference, discord_message_id
                    FROM nominations
                    WHERE contact_sha256 = ? AND arxiv_base_id = ?
                    """,
                    (values[2], values[4]),
                ).fetchone()
                self._connection.execute("COMMIT")
            except (sqlite3.Error, OSError) as exc:
                self._rollback()
                raise MailStoreError("could not record nomination") from exc
        if row is None:
            raise MailStoreError("nomination disappeared after insertion")
        return NominationClaim(
            reference=str(row["reference"]),
            created=cursor.rowcount == 1,
            discord_message_id=(
                str(row["discord_message_id"])
                if row["discord_message_id"] is not None
                else None
            ),
        )

    def mark_discord_delivered(self, reference: str, message_id: str) -> None:
        if not message_id:
            raise ValueError("Discord message ID is empty")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    "SELECT discord_message_id FROM nominations WHERE reference = ?",
                    (reference,),
                ).fetchone()
                if row is None:
                    raise MailStoreError("nomination reference is unknown")
                prior = row["discord_message_id"]
                if prior is not None and str(prior) != message_id:
                    raise MailStoreError("nomination has a different Discord message")
                self._connection.execute(
                    """
                    UPDATE nominations
                    SET discord_message_id = ?
                    WHERE reference = ?
                    """,
                    (message_id, reference),
                )
                self._connection.execute("COMMIT")
            except (MailStoreError, sqlite3.Error, OSError):
                self._rollback()
                raise

    def import_delivered_nomination(
        self,
        *,
        reference: str,
        email: str,
        arxiv_id: str,
        paper_url: str,
        submitted_at: datetime,
        discord_message_id: str,
    ) -> bool:
        """Import one embed created before durable intake was introduced."""
        claim = self.claim_nomination(
            reference=reference,
            email=email,
            arxiv_id=arxiv_id,
            paper_url=paper_url,
            submitted_at=submitted_at,
        )
        if claim.discord_message_id is None:
            self.mark_discord_delivered(claim.reference, discord_message_id)
        return claim.created

    @staticmethod
    def _notice_json(notice: Mapping[str, object]) -> str:
        return json.dumps(notice, sort_keys=True, separators=(",", ":"))

    def queue_publication_notices(
        self,
        notices: Iterable[Mapping[str, object]],
        *,
        now: datetime,
    ) -> int:
        """Snapshot result notices for every delivered matching nomination."""
        queued = 0
        created_at = utc_text(now)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                for notice in notices:
                    study_id = str(notice["study_id"])
                    arxiv_base = base_arxiv_id(str(notice["arxiv_id"]))
                    payload = self._notice_json(notice)
                    rows = self._connection.execute(
                        """
                        SELECT reference
                        FROM nominations
                        WHERE arxiv_base_id = ?
                          AND discord_message_id IS NOT NULL
                          AND contact_email IS NOT NULL
                        """,
                        (arxiv_base,),
                    ).fetchall()
                    for row in rows:
                        reference = str(row["reference"])
                        message_id = (
                            f"<completion.{reference.lower()}.{study_id}@nulspec.com>"
                        )
                        if not MESSAGE_ID_RE.fullmatch(message_id):
                            raise ValueError("generated mail message ID is invalid")
                        cursor = self._connection.execute(
                            """
                            INSERT INTO notification_outbox(
                                reference, study_id, message_id, notice_json,
                                created_at
                            ) VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(reference, study_id) DO NOTHING
                            """,
                            (
                                reference,
                                study_id,
                                message_id,
                                payload,
                                created_at,
                            ),
                        )
                        queued += int(cursor.rowcount == 1)
                self._connection.execute("COMMIT")
            except (KeyError, TypeError, ValueError, sqlite3.Error, OSError) as exc:
                self._rollback()
                raise MailStoreError("could not queue publication notices") from exc
        return queued

    def recover_interrupted_notifications(self, *, now: float) -> int:
        """Make an interrupted SMTP attempt retryable with its stable Message-ID."""
        with self._lock:
            cursor = self._connection.execute(
                """
                UPDATE notification_outbox
                SET state = 'retry', next_attempt_at = ?,
                    last_error = 'worker restarted during delivery'
                WHERE state = 'sending'
                """,
                (now,),
            )
            return cursor.rowcount

    def lease_notification(self, *, now: float) -> PendingNotification | None:
        """Atomically claim the next due result message for SMTP delivery."""
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT o.id, o.reference, o.study_id, o.message_id,
                           o.notice_json, o.attempts, n.contact_email,
                           n.submitted_at
                    FROM notification_outbox AS o
                    JOIN nominations AS n ON n.reference = o.reference
                    WHERE o.state IN ('queued', 'retry')
                      AND o.next_attempt_at <= ?
                      AND n.contact_email IS NOT NULL
                    ORDER BY o.id
                    LIMIT 1
                    """,
                    (now,),
                ).fetchone()
                if row is None:
                    self._connection.execute("COMMIT")
                    return None
                notice = json.loads(str(row["notice_json"]))
                if not isinstance(notice, dict):
                    raise MailStoreError("queued result notice is invalid")
                self._connection.execute(
                    """
                    UPDATE notification_outbox
                    SET state = 'sending', attempts = attempts + 1,
                        last_error = NULL
                    WHERE id = ?
                    """,
                    (row["id"],),
                )
                self._connection.execute("COMMIT")
            except MailStoreError:
                self._rollback()
                raise
            except (json.JSONDecodeError, sqlite3.Error, OSError) as exc:
                self._rollback()
                raise MailStoreError("could not lease notification") from exc
        return PendingNotification(
            outbox_id=int(row["id"]),
            reference=str(row["reference"]),
            contact_email=str(row["contact_email"]),
            submitted_at=str(row["submitted_at"]),
            study_id=str(row["study_id"]),
            message_id=str(row["message_id"]),
            notice=notice,
            attempts=int(row["attempts"]) + 1,
        )

    def retry_notification(
        self,
        outbox_id: int,
        *,
        next_attempt_at: float,
        error: str,
    ) -> None:
        safe_error = " ".join(error.split())[:240] or "delivery failed"
        with self._lock:
            cursor = self._connection.execute(
                """
                UPDATE notification_outbox
                SET state = 'retry', next_attempt_at = ?, last_error = ?
                WHERE id = ? AND state = 'sending'
                """,
                (next_attempt_at, safe_error, outbox_id),
            )
            if cursor.rowcount != 1:
                raise MailStoreError("notification is not leased")

    def complete_notification(
        self,
        outbox_id: int,
        *,
        sent_at: datetime,
    ) -> None:
        """Commit delivery and redact the no-longer-needed raw contact address."""
        timestamp = utc_text(sent_at)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT reference
                    FROM notification_outbox
                    WHERE id = ? AND state = 'sending'
                    """,
                    (outbox_id,),
                ).fetchone()
                if row is None:
                    raise MailStoreError("notification is not leased")
                self._connection.execute(
                    """
                    UPDATE notification_outbox
                    SET state = 'sent', sent_at = ?, last_error = NULL
                    WHERE id = ?
                    """,
                    (timestamp, outbox_id),
                )
                self._connection.execute(
                    """
                    UPDATE nominations
                    SET contact_email = NULL, notified_at = ?
                    WHERE reference = ?
                    """,
                    (timestamp, row["reference"]),
                )
                self._connection.execute("COMMIT")
            except (MailStoreError, sqlite3.Error, OSError):
                self._rollback()
                raise

    def mailbox_cursor(
        self,
        *,
        mailbox: str,
        uidvalidity: int,
        initial_high_water_uid: int,
        now: datetime,
    ) -> tuple[int, bool]:
        """Return a cursor, initializing changed mailboxes past existing mail."""
        timestamp = utc_text(now)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT uidvalidity, high_water_uid
                FROM mailbox_state WHERE mailbox = ?
                """,
                (mailbox,),
            ).fetchone()
            if row is not None and int(row["uidvalidity"]) == uidvalidity:
                return int(row["high_water_uid"]), False
            self._connection.execute(
                """
                INSERT INTO mailbox_state(
                    mailbox, uidvalidity, high_water_uid, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(mailbox) DO UPDATE SET
                    uidvalidity = excluded.uidvalidity,
                    high_water_uid = excluded.high_water_uid,
                    updated_at = excluded.updated_at
                """,
                (mailbox, uidvalidity, initial_high_water_uid, timestamp),
            )
            return initial_high_water_uid, True

    def inbound_delivered(
        self,
        *,
        mailbox: str,
        uidvalidity: int,
        uid: int,
    ) -> bool:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT state FROM inbound_messages
                WHERE mailbox = ? AND uidvalidity = ? AND uid = ?
                """,
                (mailbox, uidvalidity, uid),
            ).fetchone()
            return row is not None and row["state"] == "delivered"

    def begin_inbound(
        self,
        *,
        mailbox: str,
        uidvalidity: int,
        uid: int,
        message_id: str | None,
        received_at: datetime,
    ) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO inbound_messages(
                    mailbox, uidvalidity, uid, message_id, state, received_at
                ) VALUES (?, ?, ?, ?, 'pending', ?)
                ON CONFLICT(mailbox, uidvalidity, uid) DO UPDATE SET
                    message_id = excluded.message_id
                WHERE inbound_messages.state = 'pending'
                """,
                (
                    mailbox,
                    uidvalidity,
                    uid,
                    message_id,
                    utc_text(received_at),
                ),
            )

    def complete_inbound(
        self,
        *,
        mailbox: str,
        uidvalidity: int,
        uid: int,
        discord_message_id: str,
        now: datetime,
    ) -> None:
        timestamp = utc_text(now)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                cursor = self._connection.execute(
                    """
                    UPDATE inbound_messages
                    SET state = 'delivered', discord_message_id = ?
                    WHERE mailbox = ? AND uidvalidity = ? AND uid = ?
                    """,
                    (discord_message_id, mailbox, uidvalidity, uid),
                )
                if cursor.rowcount != 1:
                    raise MailStoreError("inbound message was not recorded")
                self._connection.execute(
                    """
                    UPDATE mailbox_state
                    SET high_water_uid = MAX(high_water_uid, ?), updated_at = ?
                    WHERE mailbox = ? AND uidvalidity = ?
                    """,
                    (uid, timestamp, mailbox, uidvalidity),
                )
                self._connection.execute("COMMIT")
            except (MailStoreError, sqlite3.Error, OSError):
                self._rollback()
                raise

    def reference_for_message_id(self, message_id: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT reference FROM notification_outbox WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()
            return str(row["reference"]) if row is not None else None

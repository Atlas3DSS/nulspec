"""Durable, hash-bound state for the private NULSPEC human-review inbox."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LEGACY_TASK_SCHEMA = "nulspec-human-review-task-v1"
TASK_SCHEMA = "nulspec-human-review-task-v2"
PUBLICATION_DISPOSITION_SCHEMA = "nulspec-human-publication-disposition-v1"
EMAIL_APPROVAL_SCHEMA = "nulspec-author-email-human-approval-v1"
EMAIL_DISPOSITION_SCHEMA = "nulspec-author-email-human-disposition-v1"

TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
STUDY_ID_RE = re.compile(r"^[0-9]{3,32}$")
ARXIV_ID_RE = re.compile(r"^[0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
EMAIL_RE = re.compile(r"^[^\s@]{1,128}@[^\s@]{1,190}$")

MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_BRIEF_CHARS = 160_000
MAX_EMAIL_CHARS = 100_000
MAX_NOTES_CHARS = 4_000


class ReviewStoreError(RuntimeError):
    """The review database could not preserve a required transition."""


class ReviewPacketError(ValueError):
    """A task packet is incomplete, unsafe, or internally inconsistent."""


class ReviewDecisionConflict(ReviewStoreError):
    """An immutable gate already has a decision."""


@dataclass(frozen=True)
class ReviewerAccount:
    username: str
    display_name: str
    password_hash: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class SessionRecord:
    username: str
    created_at: float
    expires_at: float


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_text(canonical_json(value))


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewPacketError(f"{label} must be an object")
    return value


def _exact_keys(
    value: Mapping[str, object],
    *,
    required: set[str],
    optional: set[str] | None = None,
    label: str,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        raise ReviewPacketError(f"{label} is missing {sorted(missing)}")
    if unknown:
        raise ReviewPacketError(f"{label} has unexpected fields {sorted(unknown)}")


def _text(
    value: object,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = 2_000,
) -> str:
    if not isinstance(value, str):
        raise ReviewPacketError(f"{label} must be text")
    if len(value) < minimum or len(value) > maximum or not value.strip():
        raise ReviewPacketError(f"{label} has an invalid length")
    if "\x00" in value:
        raise ReviewPacketError(f"{label} contains a null byte")
    return value


def _optional_text(
    value: object,
    label: str,
    *,
    maximum: int = 2_000,
) -> str | None:
    if value is None:
        return None
    return _text(value, label, maximum=maximum)


def _sha(value: object, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _text(value, label, maximum=64)
    if not SHA256_RE.fullmatch(text):
        raise ReviewPacketError(f"{label} must be a lowercase SHA-256 digest")
    return text


def _https_url(value: object, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _text(value, label, maximum=2_048)
    parsed = urlparse(text)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        raise ReviewPacketError(f"{label} must be an absolute HTTPS URL")
    return text


def _timestamp(value: object, label: str) -> str:
    text = _text(value, label, maximum=40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewPacketError(f"{label} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReviewPacketError(f"{label} must include a timezone")
    return text


def _nonnegative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReviewPacketError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > 1_000_000:
        raise ReviewPacketError(f"{label} is out of range")
    return number


def validate_task_packet(packet: object) -> dict[str, Any]:
    """Validate and normalize one private review task without changing meaning."""
    value = _object(packet, "task packet")
    _exact_keys(
        value,
        required={
            "schema_version",
            "task_id",
            "supersedes_task_id",
            "priority",
            "queued_reason",
            "submitted_at_utc",
            "study",
            "source",
            "brief",
            "evidence",
            "review_events",
            "publication_gate",
            "author_email_gate",
        },
        label="task packet",
    )
    schema_version = value["schema_version"]
    if schema_version not in {LEGACY_TASK_SCHEMA, TASK_SCHEMA}:
        raise ReviewPacketError("task packet has an unsupported schema version")
    task_id = _text(value["task_id"], "task_id", maximum=96)
    if not TASK_ID_RE.fullmatch(task_id):
        raise ReviewPacketError("task_id is unsafe")
    supersedes_task_id = value["supersedes_task_id"]
    if supersedes_task_id is not None:
        supersedes_task_id = _text(supersedes_task_id, "supersedes_task_id", maximum=96)
        if (
            not TASK_ID_RE.fullmatch(supersedes_task_id)
            or supersedes_task_id == task_id
        ):
            raise ReviewPacketError("supersedes_task_id is unsafe")
    if value["priority"] not in {"normal", "high", "urgent"}:
        raise ReviewPacketError("priority must be normal, high, or urgent")
    _text(value["queued_reason"], "queued_reason", maximum=4_000)
    _timestamp(value["submitted_at_utc"], "submitted_at_utc")

    study = _object(value["study"], "study")
    _exact_keys(
        study,
        required={
            "study_id",
            "paper_title",
            "paper_url",
            "arxiv_id",
            "replication_assessment",
            "method_assessment",
        },
        label="study",
    )
    study_id = _text(study["study_id"], "study.study_id", maximum=32)
    if not STUDY_ID_RE.fullmatch(study_id):
        raise ReviewPacketError("study.study_id is unsafe")
    _text(study["paper_title"], "study.paper_title", maximum=500)
    _https_url(study["paper_url"], "study.paper_url")
    arxiv_id = _text(study["arxiv_id"], "study.arxiv_id", maximum=32)
    if not ARXIV_ID_RE.fullmatch(arxiv_id):
        raise ReviewPacketError("study.arxiv_id is invalid")
    _text(
        study["replication_assessment"],
        "study.replication_assessment",
        maximum=160,
    )
    _text(study["method_assessment"], "study.method_assessment", maximum=160)

    source = _object(value["source"], "source")
    if schema_version == LEGACY_TASK_SCHEMA:
        source_keys = {
            "source_revision",
            "repository_url",
            "pull_request_url",
            "review_packet_sha256",
            "final_peer_review_sha256",
            "supplemental_review_consensus_sha256",
            "fable_action_closure_sha256",
        }
    else:
        source_keys = {
            "source_revision",
            "repository_url",
            "pull_request_url",
            "review_packet_sha256",
            "release_review_consensus_sha256",
        }
    _exact_keys(source, required=source_keys, label="source")
    revision = _text(source["source_revision"], "source.source_revision", maximum=64)
    if not REVISION_RE.fullmatch(revision):
        raise ReviewPacketError("source.source_revision must be a Git object digest")
    _https_url(source["repository_url"], "source.repository_url")
    _https_url(source["pull_request_url"], "source.pull_request_url", optional=True)
    _sha(source["review_packet_sha256"], "source.review_packet_sha256")
    if schema_version == LEGACY_TASK_SCHEMA:
        _sha(source["final_peer_review_sha256"], "source.final_peer_review_sha256")
        _sha(
            source["supplemental_review_consensus_sha256"],
            "source.supplemental_review_consensus_sha256",
            optional=True,
        )
        _sha(
            source["fable_action_closure_sha256"],
            "source.fable_action_closure_sha256",
            optional=True,
        )
    else:
        _sha(
            source["release_review_consensus_sha256"],
            "source.release_review_consensus_sha256",
        )

    brief = _text(value["brief"], "brief", maximum=MAX_BRIEF_CHARS)
    if len(brief.encode("utf-8")) > MAX_BRIEF_CHARS * 2:
        raise ReviewPacketError("brief is too large")

    evidence = value["evidence"]
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 40:
        raise ReviewPacketError("evidence must contain 1 to 40 items")
    evidence_ids: set[str] = set()
    for index, raw_item in enumerate(evidence):
        item = _object(raw_item, f"evidence[{index}]")
        _exact_keys(
            item,
            required={"id", "label", "kind", "url", "sha256", "summary"},
            label=f"evidence[{index}]",
        )
        item_id = _text(item["id"], f"evidence[{index}].id", maximum=64)
        if not TASK_ID_RE.fullmatch(item_id) or item_id in evidence_ids:
            raise ReviewPacketError("evidence IDs must be unique and URL-safe")
        evidence_ids.add(item_id)
        _text(item["label"], f"evidence[{index}].label", maximum=180)
        if item["kind"] not in {
            "brief",
            "report",
            "protocol",
            "review",
            "trace",
            "ledger",
            "artifact",
        }:
            raise ReviewPacketError(f"evidence[{index}].kind is unsupported")
        _https_url(item["url"], f"evidence[{index}].url")
        _sha(item["sha256"], f"evidence[{index}].sha256")
        _text(item["summary"], f"evidence[{index}].summary", maximum=1_000)

    review_events = value["review_events"]
    if not isinstance(review_events, list) or len(review_events) > 40:
        raise ReviewPacketError("review_events must be an array of at most 40 items")
    event_ids: set[str] = set()
    for index, raw_event in enumerate(review_events):
        event = _object(raw_event, f"review_events[{index}]")
        _exact_keys(
            event,
            required={
                "event_id",
                "reviewer",
                "provider",
                "model",
                "outcome",
                "validation",
                "summary",
                "cost_usd",
                "trace_sha256",
                "consensus_eligible",
            },
            label=f"review_events[{index}]",
        )
        event_id = _text(
            event["event_id"], f"review_events[{index}].event_id", maximum=96
        )
        if event_id in event_ids:
            raise ReviewPacketError("review event IDs must be unique")
        event_ids.add(event_id)
        for key in ("reviewer", "provider", "model", "outcome", "validation"):
            _text(event[key], f"review_events[{index}].{key}", maximum=240)
        _text(event["summary"], f"review_events[{index}].summary", maximum=2_000)
        _nonnegative_number(event["cost_usd"], f"review_events[{index}].cost_usd")
        _sha(event["trace_sha256"], f"review_events[{index}].trace_sha256")
        if not isinstance(event["consensus_eligible"], bool):
            raise ReviewPacketError(
                f"review_events[{index}].consensus_eligible must be boolean"
            )

    publication = _object(value["publication_gate"], "publication_gate")
    _exact_keys(
        publication,
        required={"reason", "question"},
        label="publication_gate",
    )
    _text(publication["reason"], "publication_gate.reason", maximum=6_000)
    _text(publication["question"], "publication_gate.question", maximum=1_000)

    email = _object(value["author_email_gate"], "author_email_gate")
    _exact_keys(
        email,
        required={"subject", "body", "draft_sha256", "recipients"},
        label="author_email_gate",
    )
    _text(email["subject"], "author_email_gate.subject", maximum=300)
    body = _text(email["body"], "author_email_gate.body", maximum=MAX_EMAIL_CHARS)
    draft_sha = _sha(email["draft_sha256"], "author_email_gate.draft_sha256")
    if draft_sha != sha256_text(body):
        raise ReviewPacketError(
            "author email draft digest does not match its exact body"
        )
    recipients = email["recipients"]
    if not isinstance(recipients, list) or len(recipients) > 30:
        raise ReviewPacketError("author_email_gate.recipients is invalid")
    recipient_emails: set[str] = set()
    for index, raw_recipient in enumerate(recipients):
        recipient = _object(raw_recipient, f"author_email_gate.recipients[{index}]")
        _exact_keys(
            recipient,
            required={"name", "email"},
            label=f"author_email_gate.recipients[{index}]",
        )
        _text(
            recipient["name"],
            f"author_email_gate.recipients[{index}].name",
            maximum=180,
        )
        address = _text(
            recipient["email"],
            f"author_email_gate.recipients[{index}].email",
            maximum=320,
        ).lower()
        if not EMAIL_RE.fullmatch(address) or address in recipient_emails:
            raise ReviewPacketError(
                "author email recipients must be unique valid addresses"
            )
        recipient_emails.add(address)

    encoded = canonical_json(value).encode("utf-8")
    if len(encoded) > MAX_PACKET_BYTES:
        raise ReviewPacketError("task packet exceeds the private inbox size limit")
    return json.loads(encoded)


class ReviewStore:
    """Coordinate reviewer sessions and append-only decisions through SQLite."""

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
        self._connection.row_factory = sqlite3.Row
        if self.path != ":memory:":
            Path(self.path).chmod(0o600)
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 10000")
            self._connection.execute("PRAGMA secure_delete = ON")
            if self.path != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL")
                self._connection.execute("PRAGMA synchronous = FULL")
            self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS review_tasks (
                task_id TEXT PRIMARY KEY,
                study_id TEXT NOT NULL,
                supersedes_task_id TEXT REFERENCES review_tasks(task_id),
                priority TEXT NOT NULL,
                packet_sha256 TEXT NOT NULL UNIQUE,
                packet_json TEXT NOT NULL,
                imported_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS review_tasks_by_study
                ON review_tasks(study_id, imported_at);
            CREATE TABLE IF NOT EXISTS review_decisions (
                decision_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES review_tasks(task_id),
                gate TEXT NOT NULL CHECK(gate IN ('publication', 'author_email')),
                decision TEXT NOT NULL,
                reviewer_username TEXT NOT NULL,
                reviewer_display_name TEXT NOT NULL,
                notes TEXT NOT NULL,
                binding_sha256 TEXT NOT NULL,
                record_sha256 TEXT NOT NULL UNIQUE,
                record_json TEXT NOT NULL,
                decided_at TEXT NOT NULL,
                UNIQUE(task_id, gate)
            );

            CREATE INDEX IF NOT EXISTS review_decisions_by_time
                ON review_decisions(decided_at DESC, decision_id DESC);

            CREATE TABLE IF NOT EXISTS review_sessions (
                token_sha256 TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                last_seen_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS review_sessions_by_expiry
                ON review_sessions(expires_at);

            CREATE TABLE IF NOT EXISTS review_login_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_digest TEXT NOT NULL,
                subject_digest TEXT NOT NULL,
                failed_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS review_failures_by_ip
                ON review_login_failures(ip_digest, failed_at);
            CREATE INDEX IF NOT EXISTS review_failures_by_subject
                ON review_login_failures(subject_digest, failed_at);

            CREATE TABLE IF NOT EXISTS review_audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                username TEXT,
                task_id TEXT,
                gate_name TEXT,
                client_digest TEXT,
                detail_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS review_audit_by_time
                ON review_audit_events(id DESC);

            PRAGMA user_version = 2;
            """
        )
        columns = {
            str(row["name"])
            for row in self._connection.execute(
                "PRAGMA table_info(review_tasks)"
            ).fetchall()
        }
        if "supersedes_task_id" not in columns:
            self._connection.execute(
                """
                ALTER TABLE review_tasks
                ADD COLUMN supersedes_task_id TEXT
                    REFERENCES review_tasks(task_id)
                """
            )
            self._connection.execute("PRAGMA user_version = 2")
        self._connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS review_task_supersession
            ON review_tasks(supersedes_task_id)
            WHERE supersedes_task_id IS NOT NULL
            """
        )

    def _rollback(self) -> None:
        if self._connection.in_transaction:
            self._connection.execute("ROLLBACK")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _audit(
        self,
        event_type: str,
        *,
        created_at: str,
        username: str | None = None,
        task_id: str | None = None,
        gate: str | None = None,
        client_digest: str | None = None,
        detail: Mapping[str, object] | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO review_audit_events(
                event_type, username, task_id, gate_name, client_digest,
                detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                username,
                task_id,
                gate,
                client_digest,
                canonical_json(detail or {}),
                created_at,
            ),
        )

    def import_task(self, packet: object, *, now: datetime) -> bool:
        normalized = validate_task_packet(packet)
        packet_json = canonical_json(normalized)
        packet_sha = sha256_text(packet_json)
        task_id = str(normalized["task_id"])
        study_id = str(normalized["study"]["study_id"])
        supersedes_task_id = normalized["supersedes_task_id"]
        imported_at = utc_text(now)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                prior = self._connection.execute(
                    "SELECT packet_sha256 FROM review_tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                if prior is not None:
                    if str(prior["packet_sha256"]) != packet_sha:
                        raise ReviewStoreError(
                            "task ID already binds a different immutable packet"
                        )
                    self._connection.execute("COMMIT")
                    return False
                active = self._connection.execute(
                    """
                    SELECT current.task_id, current.study_id
                    FROM review_tasks AS current
                    WHERE current.study_id = ?
                      AND NOT EXISTS (
                          SELECT 1 FROM review_tasks AS newer
                          WHERE newer.supersedes_task_id = current.task_id
                      )
                    """,
                    (study_id,),
                ).fetchall()
                if len(active) > 1:
                    raise ReviewStoreError(
                        "study has multiple active tasks; repair the inbox chain"
                    )
                if supersedes_task_id is None and active:
                    raise ReviewStoreError(
                        "study already has an active task; supersession must be explicit"
                    )
                if supersedes_task_id is not None:
                    if not active or str(active[0]["task_id"]) != supersedes_task_id:
                        raise ReviewStoreError(
                            "supersedes_task_id must name the study's active task"
                        )
                self._connection.execute(
                    """
                    INSERT INTO review_tasks(
                        task_id, study_id, supersedes_task_id, priority,
                        packet_sha256, packet_json, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        study_id,
                        supersedes_task_id,
                        normalized["priority"],
                        packet_sha,
                        packet_json,
                        imported_at,
                    ),
                )
                self._audit(
                    "task_imported",
                    created_at=imported_at,
                    task_id=task_id,
                    detail={
                        "packet_sha256": packet_sha,
                        "supersedes_task_id": supersedes_task_id,
                    },
                )
                self._connection.execute("COMMIT")
            except (ReviewStoreError, sqlite3.Error, OSError):
                self._rollback()
                raise
        return True

    @staticmethod
    def _task_row(row: sqlite3.Row) -> dict[str, Any]:
        packet = json.loads(str(row["packet_json"]))
        return {
            "task_id": str(row["task_id"]),
            "study_id": str(row["study_id"]),
            "supersedes_task_id": (
                str(row["supersedes_task_id"])
                if row["supersedes_task_id"] is not None
                else None
            ),
            "priority": str(row["priority"]),
            "packet_sha256": str(row["packet_sha256"]),
            "imported_at": str(row["imported_at"]),
            "packet": packet,
        }

    @staticmethod
    def _decision_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "decision_id": str(row["decision_id"]),
            "task_id": str(row["task_id"]),
            "gate": str(row["gate"]),
            "decision": str(row["decision"]),
            "reviewer_username": str(row["reviewer_username"]),
            "reviewer_display_name": str(row["reviewer_display_name"]),
            "notes": str(row["notes"]),
            "binding_sha256": str(row["binding_sha256"]),
            "record_sha256": str(row["record_sha256"]),
            "record": json.loads(str(row["record_json"])),
            "decided_at": str(row["decided_at"]),
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM review_tasks
                ORDER BY CASE priority
                    WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,
                    imported_at, task_id
                """
            ).fetchall()
            decision_rows = self._connection.execute(
                "SELECT * FROM review_decisions ORDER BY decided_at, decision_id"
            ).fetchall()
        decisions: dict[str, list[dict[str, Any]]] = {}
        superseded_by = {
            str(row["supersedes_task_id"]): str(row["task_id"])
            for row in rows
            if row["supersedes_task_id"] is not None
        }
        for row in decision_rows:
            decision = self._decision_row(row)
            decisions.setdefault(decision["task_id"], []).append(decision)
        result = []
        for row in rows:
            task = self._task_row(row)
            task["superseded_by"] = superseded_by.get(task["task_id"])
            task["decisions"] = decisions.get(task["task_id"], [])
            result.append(task)
        return result

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM review_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            decision_rows = self._connection.execute(
                """
                SELECT * FROM review_decisions
                WHERE task_id = ? ORDER BY decided_at, decision_id
                """,
                (task_id,),
            ).fetchall()
            superseding = self._connection.execute(
                """
                SELECT task_id FROM review_tasks
                WHERE supersedes_task_id = ?
                """,
                (task_id,),
            ).fetchone()
        task = self._task_row(row)
        task["superseded_by"] = (
            str(superseding["task_id"]) if superseding is not None else None
        )
        task["decisions"] = [self._decision_row(item) for item in decision_rows]
        return task

    def record_decision(
        self,
        *,
        decision_id: str,
        task_id: str,
        gate: str,
        decision: str,
        reviewer_username: str,
        reviewer_display_name: str,
        notes: str,
        binding_sha256: str,
        record: Mapping[str, object],
        now: datetime,
        client_digest: str,
    ) -> dict[str, Any]:
        decided_at = utc_text(now)
        record_json = canonical_json(record)
        record_sha = sha256_text(record_json)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                task = self._connection.execute(
                    "SELECT packet_sha256 FROM review_tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                if task is None:
                    raise ReviewStoreError("review task is unknown")
                if str(task["packet_sha256"]) != binding_sha256:
                    raise ReviewStoreError("review task binding changed")
                superseding = self._connection.execute(
                    """
                    SELECT task_id FROM review_tasks
                    WHERE supersedes_task_id = ?
                    """,
                    (task_id,),
                ).fetchone()
                if superseding is not None:
                    raise ReviewDecisionConflict(
                        "review task was superseded by a newer immutable packet"
                    )
                prior = self._connection.execute(
                    """
                    SELECT decision_id FROM review_decisions
                    WHERE task_id = ? AND gate = ?
                    """,
                    (task_id, gate),
                ).fetchone()
                if prior is not None:
                    raise ReviewDecisionConflict(
                        f"{gate} already has an immutable decision"
                    )
                self._connection.execute(
                    """
                    INSERT INTO review_decisions(
                        decision_id, task_id, gate, decision,
                        reviewer_username, reviewer_display_name, notes,
                        binding_sha256, record_sha256, record_json, decided_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id,
                        task_id,
                        gate,
                        decision,
                        reviewer_username,
                        reviewer_display_name,
                        notes,
                        binding_sha256,
                        record_sha,
                        record_json,
                        decided_at,
                    ),
                )
                self._audit(
                    f"{gate}_decision",
                    created_at=decided_at,
                    username=reviewer_username,
                    task_id=task_id,
                    gate=gate,
                    client_digest=client_digest,
                    detail={
                        "decision": decision,
                        "decision_id": decision_id,
                        "record_sha256": record_sha,
                    },
                )
                self._connection.execute("COMMIT")
            except (ReviewStoreError, sqlite3.Error, OSError):
                self._rollback()
                raise
        task = self.get_task(task_id)
        if task is None:
            raise ReviewStoreError("review task disappeared after decision")
        return task

    def create_session(
        self,
        *,
        token_sha256: str,
        username: str,
        now: float,
        expires_at: float,
        client_digest: str,
        now_text: str,
    ) -> None:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    "DELETE FROM review_sessions WHERE expires_at <= ?", (now,)
                )
                self._connection.execute(
                    """
                    INSERT INTO review_sessions(
                        token_sha256, username, created_at, expires_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (token_sha256, username, now, expires_at, now),
                )
                self._audit(
                    "login_succeeded",
                    created_at=now_text,
                    username=username,
                    client_digest=client_digest,
                )
                self._connection.execute("COMMIT")
            except (sqlite3.Error, OSError):
                self._rollback()
                raise

    def get_session(self, token_sha256: str, *, now: float) -> SessionRecord | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT username, created_at, expires_at, last_seen_at
                FROM review_sessions WHERE token_sha256 = ?
                """,
                (token_sha256,),
            ).fetchone()
            if row is None:
                return None
            if float(row["expires_at"]) <= now:
                self._connection.execute(
                    "DELETE FROM review_sessions WHERE token_sha256 = ?",
                    (token_sha256,),
                )
                return None
            if now - float(row["last_seen_at"]) >= 300:
                self._connection.execute(
                    """
                    UPDATE review_sessions SET last_seen_at = ?
                    WHERE token_sha256 = ?
                    """,
                    (now, token_sha256),
                )
        return SessionRecord(
            username=str(row["username"]),
            created_at=float(row["created_at"]),
            expires_at=float(row["expires_at"]),
        )

    def revoke_session(
        self,
        token_sha256: str,
        *,
        username: str,
        now_text: str,
        client_digest: str,
    ) -> None:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    "DELETE FROM review_sessions WHERE token_sha256 = ?",
                    (token_sha256,),
                )
                self._audit(
                    "logout",
                    created_at=now_text,
                    username=username,
                    client_digest=client_digest,
                )
                self._connection.execute("COMMIT")
            except (sqlite3.Error, OSError):
                self._rollback()
                raise

    def login_retry_after(
        self,
        *,
        ip_digest: str,
        subject_digest: str,
        now: float,
        window_seconds: int,
        ip_limit: int,
        subject_limit: int,
    ) -> int | None:
        cutoff = now - window_seconds
        with self._lock:
            self._connection.execute(
                "DELETE FROM review_login_failures WHERE failed_at < ?", (cutoff,)
            )
            rows = self._connection.execute(
                """
                SELECT ip_digest, subject_digest, failed_at
                FROM review_login_failures
                WHERE failed_at >= ? AND (ip_digest = ? OR subject_digest = ?)
                ORDER BY failed_at
                """,
                (cutoff, ip_digest, subject_digest),
            ).fetchall()
        ip_times = [
            float(row["failed_at"]) for row in rows if row["ip_digest"] == ip_digest
        ]
        subject_times = [
            float(row["failed_at"])
            for row in rows
            if row["subject_digest"] == subject_digest
        ]
        relevant: list[float] = []
        if len(ip_times) >= ip_limit:
            relevant.append(ip_times[-ip_limit])
        if len(subject_times) >= subject_limit:
            relevant.append(subject_times[-subject_limit])
        if not relevant:
            return None
        return max(1, math.ceil(min(relevant) + window_seconds - now))

    def record_login_failure(
        self,
        *,
        ip_digest: str,
        subject_digest: str,
        failed_at: float,
        now_text: str,
    ) -> None:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """
                    INSERT INTO review_login_failures(
                        ip_digest, subject_digest, failed_at
                    ) VALUES (?, ?, ?)
                    """,
                    (ip_digest, subject_digest, failed_at),
                )
                self._audit(
                    "login_failed",
                    created_at=now_text,
                    client_digest=ip_digest,
                    detail={"subject_digest": subject_digest},
                )
                self._connection.execute("COMMIT")
            except (sqlite3.Error, OSError):
                self._rollback()
                raise

    def clear_login_failures(self, *, ip_digest: str, subject_digest: str) -> None:
        with self._lock:
            self._connection.execute(
                """
                DELETE FROM review_login_failures
                WHERE ip_digest = ? OR subject_digest = ?
                """,
                (ip_digest, subject_digest),
            )

    def recent_activity(self, *, limit: int = 25) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT event_type, username, task_id, gate_name,
                       detail_json, created_at
                FROM review_audit_events
                WHERE event_type IN (
                    'task_imported', 'publication_decision',
                    'author_email_decision'
                )
                ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "event_type": str(row["event_type"]),
                "username": str(row["username"]) if row["username"] else None,
                "task_id": str(row["task_id"]) if row["task_id"] else None,
                "gate": str(row["gate_name"]) if row["gate_name"] else None,
                "detail": json.loads(str(row["detail_json"])),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

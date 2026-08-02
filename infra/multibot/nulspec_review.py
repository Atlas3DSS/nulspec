#!/usr/bin/env python3
"""Private human-review API and operational CLI for NULSPEC releases."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping
from urllib.parse import quote, urlparse

from flask import Flask, Response, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from nulspec_review_store import (
    EMAIL_APPROVAL_SCHEMA,
    EMAIL_DISPOSITION_SCHEMA,
    MAX_NOTES_CHARS,
    PUBLICATION_DISPOSITION_SCHEMA,
    SHA256_RE,
    TASK_ID_RE,
    TASK_SCHEMA,
    USERNAME_RE,
    ReviewDecisionConflict,
    ReviewerAccount,
    ReviewPacketError,
    ReviewStore,
    ReviewStoreError,
    canonical_json,
    sha256_json,
    sha256_text,
    utc_text,
    validate_task_packet,
)


logger = logging.getLogger(__name__)

ACCOUNTS_SCHEMA = "nulspec-reviewer-accounts-v1"
DEFAULT_DATABASE = Path("/var/lib/multibot/nulspec-review.sqlite3")
DEFAULT_ALLOWED_ORIGINS = frozenset({"https://nulspec.com"})
SESSION_COOKIE = "__Host-nulspec-review-session"
DEV_SESSION_COOKIE = "nulspec-review-session-dev"
MAX_REQUEST_BYTES = 16 * 1024
MAX_USERNAME_BYTES = 128
MAX_PASSWORD_CHARS = 1024
MIN_PASSWORD_CHARS = 14
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_IP_LIMIT = 8
LOGIN_SUBJECT_LIMIT = 20


class ReviewConfigurationError(RuntimeError):
    """Review service configuration is missing or unsafe."""


class ReviewAuthenticationError(RuntimeError):
    """The supplied credentials or session are not valid."""


class ReviewRateLimited(RuntimeError):
    def __init__(self, retry_after: int):
        super().__init__("review login is rate limited")
        self.retry_after = retry_after


class ReviewActionError(ValueError):
    """A requested gate transition is invalid."""


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(value: str, *, label: str) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise ReviewConfigurationError(f"{label} is empty")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise ReviewConfigurationError(f"{label} is not valid base64url") from exc


def _password_method(password_hash: str) -> str:
    method = password_hash.split("$", 1)[0]
    parts = method.split(":")
    if len(parts) != 4 or parts[0] != "scrypt":
        raise ReviewConfigurationError("reviewer passwords must use Werkzeug scrypt")
    try:
        n, r, p = (int(item) for item in parts[1:])
    except ValueError as exc:
        raise ReviewConfigurationError(
            "reviewer scrypt parameters are invalid"
        ) from exc
    if n < 16_384 or r < 8 or p < 1:
        raise ReviewConfigurationError("reviewer scrypt parameters are too weak")
    return method


def decode_accounts(encoded: str) -> dict[str, ReviewerAccount]:
    try:
        raw = json.loads(_b64decode(encoded, label="reviewer accounts"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReviewConfigurationError("reviewer accounts are not valid JSON") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "accounts"}:
        raise ReviewConfigurationError("reviewer accounts have an invalid envelope")
    if raw["schema_version"] != ACCOUNTS_SCHEMA:
        raise ReviewConfigurationError("reviewer accounts use an unsupported schema")
    rows = raw["accounts"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 25:
        raise ReviewConfigurationError("configure between 1 and 25 reviewer accounts")
    accounts: dict[str, ReviewerAccount] = {}
    password_methods: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
            "username",
            "display_name",
            "password_hash",
            "roles",
        }:
            raise ReviewConfigurationError(f"reviewer account {index} is malformed")
        username = row["username"]
        display_name = row["display_name"]
        password_hash = row["password_hash"]
        roles = row["roles"]
        if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
            raise ReviewConfigurationError(
                f"reviewer account {index} has an unsafe username"
            )
        if username in accounts:
            raise ReviewConfigurationError("reviewer usernames must be unique")
        if (
            not isinstance(display_name, str)
            or not display_name.strip()
            or len(display_name) > 120
            or "\x00" in display_name
        ):
            raise ReviewConfigurationError(
                f"reviewer account {index} has an invalid display name"
            )
        if not isinstance(password_hash, str):
            raise ReviewConfigurationError(
                f"reviewer account {index} has an invalid password hash"
            )
        password_methods.add(_password_method(password_hash))
        if (
            not isinstance(roles, list)
            or roles != ["reviewer"]
            or not all(isinstance(role, str) for role in roles)
        ):
            raise ReviewConfigurationError(
                f"reviewer account {index} must have only the reviewer role"
            )
        accounts[username] = ReviewerAccount(
            username=username,
            display_name=display_name.strip(),
            password_hash=password_hash,
            roles=("reviewer",),
        )
    if len(password_methods) != 1:
        raise ReviewConfigurationError(
            "all reviewer password hashes must use identical scrypt parameters"
        )
    return accounts


def encode_accounts(raw: Mapping[str, object]) -> str:
    encoded = _b64encode(canonical_json(raw).encode("utf-8"))
    decode_accounts(encoded)
    return encoded


def accounts_from_environment(
    environment: Mapping[str, str] = os.environ,
) -> dict[str, ReviewerAccount]:
    """Load either the single primary reviewer or a multi-account envelope."""

    encoded = environment.get("NULSPEC_REVIEW_ACCOUNTS_B64", "").strip()
    primary = {
        "username": environment.get("NULSPEC_REVIEW_PRIMARY_USERNAME", "").strip(),
        "display_name": environment.get(
            "NULSPEC_REVIEW_PRIMARY_DISPLAY_NAME", ""
        ).strip(),
        "password_hash": environment.get(
            "NULSPEC_REVIEW_PRIMARY_PASSWORD_HASH", ""
        ).strip(),
    }
    if encoded:
        if any(primary.values()):
            raise ReviewConfigurationError(
                "configure either the primary reviewer or the account envelope, not both"
            )
        return decode_accounts(encoded)
    if not primary["username"]:
        raise ReviewConfigurationError("primary reviewer username is empty")
    if not primary["display_name"]:
        raise ReviewConfigurationError("primary reviewer display name is empty")
    if not primary["password_hash"]:
        raise ReviewConfigurationError("primary reviewer password hash is empty")
    raw = {
        "schema_version": ACCOUNTS_SCHEMA,
        "accounts": [
            {
                **primary,
                "roles": ["reviewer"],
            }
        ],
    }
    return decode_accounts(encode_accounts(raw))


def decode_pepper(encoded: str) -> bytes:
    pepper = _b64decode(encoded, label="review pepper")
    if len(pepper) < 32:
        raise ReviewConfigurationError(
            "review pepper must contain at least 32 random bytes"
        )
    return pepper


class ReviewService:
    """Authenticate configured humans and enforce the two-stage release gate."""

    def __init__(
        self,
        *,
        store: ReviewStore,
        accounts: Mapping[str, ReviewerAccount],
        pepper: bytes,
        allowed_origins: frozenset[str] = DEFAULT_ALLOWED_ORIGINS,
        session_lifetime: timedelta = timedelta(hours=12),
        secure_cookie: bool = True,
        now: Callable[[], datetime] | None = None,
        login_window_seconds: int = LOGIN_WINDOW_SECONDS,
        login_ip_limit: int = LOGIN_IP_LIMIT,
        login_subject_limit: int = LOGIN_SUBJECT_LIMIT,
    ):
        if not accounts:
            raise ReviewConfigurationError("at least one reviewer account is required")
        if len(pepper) < 32:
            raise ReviewConfigurationError("review pepper is too short")
        if not allowed_origins or "*" in allowed_origins:
            raise ReviewConfigurationError("review origins must be explicit")
        for origin in allowed_origins:
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.params
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or origin.endswith("/")
            ):
                raise ReviewConfigurationError(
                    "review origins must be bare HTTP origins"
                )
            if secure_cookie and parsed.scheme != "https":
                raise ReviewConfigurationError(
                    "secure review cookies require HTTPS origins"
                )
        if session_lifetime < timedelta(minutes=15) or session_lifetime > timedelta(
            days=1
        ):
            raise ReviewConfigurationError(
                "review session lifetime must be 15 minutes to 24 hours"
            )
        if not secure_cookie and not all(
            origin.startswith(("http://127.0.0.1:", "http://localhost:"))
            for origin in allowed_origins
        ):
            raise ReviewConfigurationError(
                "insecure review cookies are local-development only"
            )
        self.store = store
        self.accounts = dict(accounts)
        self.pepper = pepper
        self.allowed_origins = allowed_origins
        self.session_lifetime = session_lifetime
        self.secure_cookie = secure_cookie
        self.cookie_name = SESSION_COOKIE if secure_cookie else DEV_SESSION_COOKIE
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.login_window_seconds = login_window_seconds
        self.login_ip_limit = login_ip_limit
        self.login_subject_limit = login_subject_limit
        dummy_method = _password_method(
            next(iter(self.accounts.values())).password_hash
        )
        self._dummy_hash = generate_password_hash(
            "nulspec-unknown-reviewer-dummy-secret", method=dummy_method
        )
        self._password_slots = threading.BoundedSemaphore(2)

    @classmethod
    def from_environment(cls) -> ReviewService:
        if os.environ.get("NULSPEC_REVIEW_ENABLED") != "1":
            raise ReviewConfigurationError("NULSPEC_REVIEW_ENABLED is not 1")
        accounts = accounts_from_environment()
        pepper = decode_pepper(os.environ.get("NULSPEC_REVIEW_PEPPER_B64", ""))
        database = Path(os.environ.get("NULSPEC_REVIEW_DB_PATH", str(DEFAULT_DATABASE)))
        raw_origins = os.environ.get(
            "NULSPEC_REVIEW_ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS)
        )
        origins = frozenset(
            item.strip() for item in raw_origins.split(",") if item.strip()
        )
        try:
            session_hours = float(os.environ.get("NULSPEC_REVIEW_SESSION_HOURS", "12"))
        except ValueError as exc:
            raise ReviewConfigurationError(
                "review session hours must be numeric"
            ) from exc
        secure_cookie = os.environ.get("NULSPEC_REVIEW_COOKIE_SECURE", "1") == "1"
        return cls(
            store=ReviewStore(database),
            accounts=accounts,
            pepper=pepper,
            allowed_origins=origins,
            session_lifetime=timedelta(hours=session_hours),
            secure_cookie=secure_cookie,
        )

    def origin_allowed(self, origin: str) -> bool:
        return origin in self.allowed_origins

    def _digest(self, namespace: bytes, value: str) -> str:
        return hmac.new(
            self.pepper,
            namespace + b":" + value.encode("utf-8", errors="replace"),
            hashlib.sha256,
        ).hexdigest()

    def client_digest(self, client_ip: str) -> str:
        return self._digest(b"client", client_ip[:256])

    def _subject_digest(self, username: str) -> str:
        return self._digest(b"login-subject", username[:128])

    @staticmethod
    def _token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def _csrf_token(self, session_token: str) -> str:
        return _b64encode(
            hmac.new(
                self.pepper,
                b"csrf:" + session_token.encode("ascii"),
                hashlib.sha256,
            ).digest()
        )

    def login(
        self, username: object, password: object, *, client_ip: str
    ) -> dict[str, Any]:
        normalized = username.strip().lower() if isinstance(username, str) else ""
        password_text = password if isinstance(password, str) else ""
        if len(normalized.encode("utf-8", errors="replace")) > MAX_USERNAME_BYTES:
            normalized = normalized[:MAX_USERNAME_BYTES]
        if len(password_text) > MAX_PASSWORD_CHARS:
            password_text = password_text[:MAX_PASSWORD_CHARS]
        client_digest = self.client_digest(client_ip)
        subject_digest = self._subject_digest(normalized)
        current = self.now()
        now_epoch = current.timestamp()
        retry_after = self.store.login_retry_after(
            ip_digest=client_digest,
            subject_digest=subject_digest,
            now=now_epoch,
            window_seconds=self.login_window_seconds,
            ip_limit=self.login_ip_limit,
            subject_limit=self.login_subject_limit,
        )
        if retry_after is not None:
            raise ReviewRateLimited(retry_after)
        if not self._password_slots.acquire(blocking=False):
            raise ReviewRateLimited(2)
        try:
            account = self.accounts.get(normalized)
            candidate_hash = account.password_hash if account else self._dummy_hash
            valid_password = check_password_hash(candidate_hash, password_text)
        finally:
            self._password_slots.release()
        valid = (
            account is not None
            and USERNAME_RE.fullmatch(normalized) is not None
            and valid_password
        )
        if not valid:
            self.store.record_login_failure(
                ip_digest=client_digest,
                subject_digest=subject_digest,
                failed_at=now_epoch,
                now_text=utc_text(current),
            )
            raise ReviewAuthenticationError("invalid credentials")
        self.store.clear_login_failures(
            ip_digest=client_digest, subject_digest=subject_digest
        )
        token = secrets.token_urlsafe(32)
        token_digest = self._token_digest(token)
        expires_at = now_epoch + self.session_lifetime.total_seconds()
        self.store.create_session(
            token_sha256=token_digest,
            username=account.username,
            now=now_epoch,
            expires_at=expires_at,
            client_digest=client_digest,
            now_text=utc_text(current),
        )
        return {
            "token": token,
            "csrf_token": self._csrf_token(token),
            "account": account,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "max_age": int(self.session_lifetime.total_seconds()),
        }

    def authenticate(self, token: str | None) -> dict[str, Any]:
        if (
            not isinstance(token, str)
            or not 20 <= len(token) <= 256
            or re.fullmatch(r"[A-Za-z0-9_-]+", token) is None
        ):
            raise ReviewAuthenticationError("invalid session")
        current = self.now()
        session = self.store.get_session(
            self._token_digest(token), now=current.timestamp()
        )
        if session is None:
            raise ReviewAuthenticationError("invalid session")
        account = self.accounts.get(session.username)
        if account is None:
            raise ReviewAuthenticationError("invalid session")
        return {
            "token": token,
            "token_sha256": self._token_digest(token),
            "csrf_token": self._csrf_token(token),
            "account": account,
            "expires_at": datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    def require_csrf(self, auth: Mapping[str, Any], supplied: str | None) -> None:
        expected = str(auth["csrf_token"])
        if not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied):
            raise ReviewAuthenticationError("invalid CSRF token")

    def logout(self, auth: Mapping[str, Any], *, client_ip: str) -> None:
        account: ReviewerAccount = auth["account"]
        self.store.revoke_session(
            str(auth["token_sha256"]),
            username=account.username,
            now_text=utc_text(self.now()),
            client_digest=self.client_digest(client_ip),
        )

    @staticmethod
    def _decision_for(task: Mapping[str, Any], gate: str) -> dict[str, Any] | None:
        return next((item for item in task["decisions"] if item["gate"] == gate), None)

    def task_view(self, task: Mapping[str, Any]) -> dict[str, Any]:
        packet = task["packet"]
        publication = self._decision_for(task, "publication")
        email = self._decision_for(task, "author_email")
        superseded = task["superseded_by"] is not None
        if publication is None:
            publication_status = "awaiting_human"
        elif publication["decision"] == "APPROVE_RELEASE":
            publication_status = "approved"
        else:
            publication_status = "kept_blocked"

        recipients = packet["author_email_gate"]["recipients"]
        if publication_status != "approved":
            email_status = "blocked_by_publication"
        elif not recipients:
            email_status = "blocked_missing_recipients"
        elif email is None:
            email_status = "awaiting_human"
        elif email["decision"] == "APPROVE_SEND":
            email_status = "approved_for_operator_dispatch"
        else:
            email_status = "returned_for_revision"

        complete = (
            superseded
            or publication_status == "kept_blocked"
            or (
                publication_status == "approved"
                and email_status
                in {"approved_for_operator_dispatch", "returned_for_revision"}
            )
        )
        return {
            "task_id": task["task_id"],
            "supersedes_task_id": task["supersedes_task_id"],
            "superseded_by": task["superseded_by"],
            "packet_sha256": task["packet_sha256"],
            "imported_at": task["imported_at"],
            "priority": task["priority"],
            "queued_reason": packet["queued_reason"],
            "submitted_at_utc": packet["submitted_at_utc"],
            "study": packet["study"],
            "source": packet["source"],
            "brief": packet["brief"],
            "evidence": packet["evidence"],
            "review_events": packet["review_events"],
            "review_cost_total_usd": round(
                sum(float(item["cost_usd"]) for item in packet["review_events"]),
                8,
            ),
            "publication_gate": {
                **packet["publication_gate"],
                "status": publication_status,
                "action_allowed": publication is None and not superseded,
                "decision": publication,
            },
            "author_email_gate": {
                **packet["author_email_gate"],
                "status": email_status,
                "action_allowed": email_status == "awaiting_human" and not superseded,
                "decision": email,
            },
            "complete": complete,
            "decisions": task["decisions"],
        }

    def inbox(self) -> dict[str, Any]:
        tasks = [self.task_view(task) for task in self.store.list_tasks()]
        summary = {
            "papers_waiting": sum(
                item["superseded_by"] is None
                and item["publication_gate"]["status"] == "awaiting_human"
                for item in tasks
            ),
            "emails_waiting": sum(
                item["superseded_by"] is None
                and item["author_email_gate"]["status"] == "awaiting_human"
                for item in tasks
            ),
            "emails_blocked": sum(
                item["superseded_by"] is None
                and item["author_email_gate"]["status"]
                in {"blocked_by_publication", "blocked_missing_recipients"}
                for item in tasks
            ),
            "completed_tasks": sum(bool(item["complete"]) for item in tasks),
            "total_tasks": len(tasks),
        }
        return {
            "schema_version": "nulspec-human-review-inbox-v1",
            "summary": summary,
            "tasks": tasks,
            "recent_activity": self.store.recent_activity(),
        }

    def _reviewer_projection(self, account: ReviewerAccount) -> dict[str, str]:
        return {
            "display_name": account.display_name,
            "account_sha256": self._digest(b"reviewer-account", account.username),
        }

    def decide(
        self,
        *,
        auth: Mapping[str, Any],
        task_id: str,
        gate: object,
        decision: object,
        notes: object,
        binding_sha256: object,
        confirmed: object,
        client_ip: str,
    ) -> dict[str, Any]:
        if not TASK_ID_RE.fullmatch(task_id):
            raise ReviewActionError("invalid task")
        if gate not in {"publication", "author_email"}:
            raise ReviewActionError("invalid gate")
        allowed = {
            "publication": {"APPROVE_RELEASE", "KEEP_BLOCKED"},
            "author_email": {"APPROVE_SEND", "RETURN_FOR_REVISION"},
        }
        if decision not in allowed[gate]:
            raise ReviewActionError("invalid decision")
        if (
            not isinstance(notes, str)
            or len(notes.strip()) < 20
            or len(notes) > MAX_NOTES_CHARS
            or "\x00" in notes
        ):
            raise ReviewActionError("notes must contain 20 to 4000 characters")
        if not isinstance(binding_sha256, str) or not SHA256_RE.fullmatch(
            binding_sha256
        ):
            raise ReviewActionError("invalid packet binding")
        if confirmed is not True:
            raise ReviewActionError("explicit confirmation is required")
        task = self.store.get_task(task_id)
        if task is None:
            raise ReviewActionError("review task not found")
        if task["superseded_by"] is not None:
            raise ReviewActionError("task was superseded; review the newer packet")
        if task["packet_sha256"] != binding_sha256:
            raise ReviewActionError("task changed; reload before deciding")
        if self._decision_for(task, gate) is not None:
            raise ReviewDecisionConflict(f"{gate} already has a decision")

        packet = task["packet"]
        current = self.now()
        decided_at = utc_text(current)
        decision_id = (
            "NHR-" + current.strftime("%Y%m%d") + "-" + secrets.token_hex(4).upper()
        )
        account: ReviewerAccount = auth["account"]
        reviewer = self._reviewer_projection(account)
        binding = {
            "task_packet_sha256": task["packet_sha256"],
            "source_revision": packet["source"]["source_revision"],
            "review_packet_sha256": packet["source"]["review_packet_sha256"],
            "final_peer_review_sha256": packet["source"]["final_peer_review_sha256"],
            "supplemental_review_consensus_sha256": packet["source"][
                "supplemental_review_consensus_sha256"
            ],
        }
        if gate == "publication":
            record: dict[str, Any] = {
                "schema_version": PUBLICATION_DISPOSITION_SCHEMA,
                "decision_id": decision_id,
                "task_id": task_id,
                "study_id": packet["study"]["study_id"],
                "decision": decision,
                "human_approved": decision == "APPROVE_RELEASE",
                "decided_at_utc": decided_at,
                "reviewer": reviewer,
                "notes": notes.strip(),
                "binding": binding,
                "scientific_result_mutable": False,
                "author_email_dispatch_authorized": False,
            }
        else:
            publication = self._decision_for(task, "publication")
            if publication is None or publication["decision"] != "APPROVE_RELEASE":
                raise ReviewActionError(
                    "author email remains blocked until publication is approved"
                )
            recipients = packet["author_email_gate"]["recipients"]
            if not recipients:
                raise ReviewActionError("author email has no bound recipients")
            recipient_sha = sha256_json(recipients)
            if decision == "APPROVE_SEND":
                record = {
                    "schema_version": EMAIL_APPROVAL_SCHEMA,
                    "decision": "APPROVE_SEND",
                    "human_approved": True,
                    "exact_draft_only": True,
                    "approved_at_utc": decided_at,
                    "author_email_sha256": packet["author_email_gate"]["draft_sha256"],
                    "final_peer_review_sha256": packet["source"][
                        "final_peer_review_sha256"
                    ],
                    "fable_action_closure_sha256": packet["source"][
                        "fable_action_closure_sha256"
                    ],
                    "supplemental_review_consensus_sha256": packet["source"][
                        "supplemental_review_consensus_sha256"
                    ],
                    "publication_disposition_sha256": publication["record_sha256"],
                    "recipient_list_sha256": recipient_sha,
                    "decision_id": decision_id,
                    "task_id": task_id,
                    "study_id": packet["study"]["study_id"],
                    "reviewer": reviewer,
                    "notes": notes.strip(),
                    "operator_dispatch_still_required": True,
                }
            else:
                record = {
                    "schema_version": EMAIL_DISPOSITION_SCHEMA,
                    "decision": "RETURN_FOR_REVISION",
                    "human_approved": False,
                    "decided_at_utc": decided_at,
                    "author_email_sha256": packet["author_email_gate"]["draft_sha256"],
                    "publication_disposition_sha256": publication["record_sha256"],
                    "recipient_list_sha256": recipient_sha,
                    "decision_id": decision_id,
                    "task_id": task_id,
                    "study_id": packet["study"]["study_id"],
                    "reviewer": reviewer,
                    "notes": notes.strip(),
                }
        updated = self.store.record_decision(
            decision_id=decision_id,
            task_id=task_id,
            gate=gate,
            decision=str(decision),
            reviewer_username=account.username,
            reviewer_display_name=account.display_name,
            notes=notes.strip(),
            binding_sha256=binding_sha256,
            record=record,
            now=current,
            client_digest=self.client_digest(client_ip),
        )
        return self.task_view(updated)


class DisabledReviewService:
    cookie_name = SESSION_COOKIE

    def __init__(self, reason: str):
        self.reason = reason


def _json_response(payload: Mapping[str, object], status: int = 200) -> Response:
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'"
    )
    return response


def _client_ip() -> str:
    forwarded = request.headers.get("X-Nulspec-Client-IP", "").strip()
    if forwarded and "," not in forwarded and len(forwarded) <= 256:
        return forwarded
    return request.remote_addr or "unknown"


def register_nulspec_review_routes(
    app: Flask,
    *,
    service: ReviewService | DisabledReviewService | None = None,
) -> None:
    """Register a login-only, same-origin human-review API."""
    if service is None:
        try:
            service = ReviewService.from_environment()
        except (
            OSError,
            ReviewConfigurationError,
            ReviewStoreError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            logger.warning("NULSPEC human-review dashboard disabled: %s", exc)
            service = DisabledReviewService(str(exc))
    app.extensions["nulspec_review_service"] = service

    def enabled() -> ReviewService | None:
        return service if isinstance(service, ReviewService) else None

    def require_origin(active: ReviewService) -> Response | None:
        if not active.origin_allowed(request.headers.get("Origin", "")):
            return _json_response({"ok": False, "error": "forbidden_origin"}, 403)
        return None

    def parse_json() -> tuple[dict[str, Any] | None, Response | None]:
        if request.content_length and request.content_length > MAX_REQUEST_BYTES:
            return None, _json_response(
                {"ok": False, "error": "payload_too_large"}, 413
            )
        if not request.is_json:
            return None, _json_response({"ok": False, "error": "json_required"}, 415)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return None, _json_response({"ok": False, "error": "invalid_json"}, 400)
        return payload, None

    def authenticate(
        active: ReviewService,
    ) -> tuple[dict[str, Any] | None, Response | None]:
        try:
            return active.authenticate(request.cookies.get(active.cookie_name)), None
        except ReviewAuthenticationError:
            return None, _json_response(
                {"ok": False, "error": "authentication_required"}, 401
            )

    @app.post("/api/review/login")
    def nulspec_review_login() -> Response:
        active = enabled()
        if active is None:
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        origin_error = require_origin(active)
        if origin_error is not None:
            return origin_error
        payload, error = parse_json()
        if error is not None:
            return error
        assert payload is not None
        if set(payload) != {"username", "password"}:
            return _json_response({"ok": False, "error": "invalid_credentials"}, 401)
        try:
            result = active.login(
                payload.get("username"), payload.get("password"), client_ip=_client_ip()
            )
        except ReviewRateLimited as exc:
            response = _json_response({"ok": False, "error": "rate_limited"}, 429)
            response.headers["Retry-After"] = str(exc.retry_after)
            return response
        except (ReviewAuthenticationError, ReviewStoreError, sqlite3.Error):
            return _json_response({"ok": False, "error": "invalid_credentials"}, 401)
        account: ReviewerAccount = result["account"]
        response = _json_response(
            {
                "ok": True,
                "reviewer": {
                    "username": account.username,
                    "display_name": account.display_name,
                },
                "csrf_token": result["csrf_token"],
                "expires_at": result["expires_at"],
            }
        )
        response.set_cookie(
            active.cookie_name,
            result["token"],
            max_age=result["max_age"],
            secure=active.secure_cookie,
            httponly=True,
            samesite="Strict",
            path="/",
        )
        return response

    @app.get("/api/review/session")
    def nulspec_review_session() -> Response:
        active = enabled()
        if active is None:
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        auth, error = authenticate(active)
        if error is not None:
            return error
        assert auth is not None
        account: ReviewerAccount = auth["account"]
        return _json_response(
            {
                "ok": True,
                "reviewer": {
                    "username": account.username,
                    "display_name": account.display_name,
                },
                "csrf_token": auth["csrf_token"],
                "expires_at": auth["expires_at"],
            }
        )

    @app.post("/api/review/logout")
    def nulspec_review_logout() -> Response:
        active = enabled()
        if active is None:
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        origin_error = require_origin(active)
        if origin_error is not None:
            return origin_error
        auth, error = authenticate(active)
        if error is not None:
            return error
        assert auth is not None
        try:
            active.require_csrf(auth, request.headers.get("X-Nulspec-CSRF"))
            active.logout(auth, client_ip=_client_ip())
        except (ReviewAuthenticationError, ReviewStoreError, sqlite3.Error):
            return _json_response({"ok": False, "error": "invalid_request"}, 403)
        response = _json_response({"ok": True})
        response.delete_cookie(
            active.cookie_name,
            secure=active.secure_cookie,
            httponly=True,
            samesite="Strict",
            path="/",
        )
        return response

    @app.get("/api/review/tasks")
    def nulspec_review_tasks() -> Response:
        active = enabled()
        if active is None:
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        _, error = authenticate(active)
        if error is not None:
            return error
        try:
            inbox = active.inbox()
        except (ReviewStoreError, sqlite3.Error, json.JSONDecodeError):
            logger.exception("NULSPEC review inbox could not be read")
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        return _json_response({"ok": True, **inbox})

    @app.post("/api/review/tasks/<task_id>/decisions")
    def nulspec_review_decision(task_id: str) -> Response:
        active = enabled()
        if active is None:
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        origin_error = require_origin(active)
        if origin_error is not None:
            return origin_error
        auth, error = authenticate(active)
        if error is not None:
            return error
        assert auth is not None
        try:
            active.require_csrf(auth, request.headers.get("X-Nulspec-CSRF"))
        except ReviewAuthenticationError:
            return _json_response({"ok": False, "error": "invalid_csrf"}, 403)
        payload, payload_error = parse_json()
        if payload_error is not None:
            return payload_error
        assert payload is not None
        if set(payload) != {
            "gate",
            "decision",
            "notes",
            "binding_sha256",
            "confirmed",
        }:
            return _json_response({"ok": False, "error": "unexpected_fields"}, 400)
        try:
            task = active.decide(
                auth=auth,
                task_id=task_id,
                gate=payload.get("gate"),
                decision=payload.get("decision"),
                notes=payload.get("notes"),
                binding_sha256=payload.get("binding_sha256"),
                confirmed=payload.get("confirmed"),
                client_ip=_client_ip(),
            )
        except ReviewDecisionConflict:
            return _json_response({"ok": False, "error": "already_decided"}, 409)
        except ReviewActionError as exc:
            return _json_response(
                {"ok": False, "error": "invalid_decision", "message": str(exc)},
                422,
            )
        except (ReviewStoreError, sqlite3.Error):
            logger.exception("NULSPEC review decision could not be preserved")
            return _json_response({"ok": False, "error": "review_unavailable"}, 503)
        return _json_response({"ok": True, "task": task}, 201)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_file_sha(path: Path) -> str:
    return sha256_json(json.loads(path.read_text()))


def _github_blob_url(repository_url: str, revision: str, path: str) -> str:
    return (
        repository_url.rstrip("/") + "/blob/" + revision + "/" + quote(path, safe="/")
    )


def _load_recipients(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    value = json.loads(path.read_text())
    if not isinstance(value, list):
        raise ReviewPacketError("recipient file must contain a JSON array")
    return value


def build_study_task(args: argparse.Namespace) -> dict[str, Any]:
    """Project a standard NULSPEC study folder into the private inbox schema."""
    study_root = args.study_root.resolve()
    required = {
        "handoff": study_root / "WEBSITE_HANDOFF.json",
        "brief": study_root / "ONE_PAGE.md",
        "report": study_root / "REPORT.md",
        "protocol": study_root / "PROTOCOL.md",
        "tests": study_root / "TESTS.md",
        "final_review_md": study_root / "FABLE_FINAL_REVIEW.md",
        "final_review": study_root / "results/fable_final_peer_review.json",
        "email": study_root / "AUTHOR_EMAIL.md",
        "ledger_md": study_root / "EXTERNAL_REVIEW_LEDGER.md",
        "ledger": study_root / "results/external_review_ledger.json",
    }
    missing = [label for label, path in required.items() if not path.is_file()]
    if missing:
        raise ReviewPacketError(f"study is missing required review files: {missing}")
    handoff = json.loads(required["handoff"].read_text())
    final_review = json.loads(required["final_review"].read_text())
    ledger = json.loads(required["ledger"].read_text())
    supplemental_path = study_root / "results/supplemental_review_consensus.json"
    supplemental = (
        json.loads(supplemental_path.read_text())
        if supplemental_path.is_file()
        else None
    )
    closure_path = study_root / "results/fable_action_closure.json"
    source_revision = args.source_revision
    repository_url = args.repository_url.rstrip("/")
    repo_path = args.study_repo_path.strip("/")

    evidence_specs = [
        (
            "one-page",
            "One-page result",
            "brief",
            required["brief"],
            "Decision-oriented result summary.",
        ),
        (
            "full-report",
            "Full replication report",
            "report",
            required["report"],
            "Complete methods, outcomes, limits, and interpretation.",
        ),
        (
            "protocol",
            "Frozen replication protocol",
            "protocol",
            required["protocol"],
            "Registered scope and decision rules.",
        ),
        (
            "verification",
            "Verification log",
            "artifact",
            required["tests"],
            "Commands, checks, and known test outcomes.",
        ),
        (
            "fable-review",
            "One-shot Fable review",
            "review",
            required["final_review_md"],
            "Final-review outcome and technical refusal context.",
        ),
        (
            "review-ledger",
            "External review ledger",
            "ledger",
            required["ledger_md"],
            "Reviewer attempts, validity, costs, and trace retention.",
        ),
    ]
    if supplemental_path.is_file():
        evidence_specs.append(
            (
                "supplemental-consensus",
                "GLM/Kimi supplemental consensus",
                "review",
                supplemental_path,
                "Fail-closed two-reviewer fallback disposition.",
            )
        )
    evidence = []
    for item_id, label, kind, path, summary in evidence_specs:
        relative = f"{repo_path}/{path.relative_to(study_root).as_posix()}"
        evidence.append(
            {
                "id": item_id,
                "label": label,
                "kind": kind,
                "url": _github_blob_url(repository_url, source_revision, relative),
                "sha256": _sha256_file(path),
                "summary": summary,
            }
        )

    events = []
    for raw in ledger.get("events", []):
        trace_artifacts = (raw.get("trace") or {}).get("artifacts") or {}
        trace = trace_artifacts.get("raw_response") or trace_artifacts.get("attempt")
        if not isinstance(trace, dict) or not SHA256_RE.fullmatch(
            str(trace.get("sha256", ""))
        ):
            raise ReviewPacketError(
                f"review event {raw.get('event_id')} lacks a trace digest"
            )
        failure = raw.get("failure")
        if isinstance(failure, dict):
            summary = str(
                failure.get("provider_message_sanitized")
                or failure.get("category")
                or raw.get("publication_consequence")
                or "Provider returned no valid structured review."
            )
        else:
            summary = str(
                failure
                or raw.get("publication_consequence")
                or raw.get("human_label")
                or "Review event completed."
            )
        events.append(
            {
                "event_id": str(raw["event_id"]),
                "reviewer": str(
                    raw.get("reviewer") or raw.get("reviewer_family") or "Unknown"
                ),
                "provider": str(raw.get("provider") or "Unknown"),
                "model": str(
                    raw.get("canonical_model")
                    or raw.get("model")
                    or raw.get("requested_model")
                    or "Unknown"
                ),
                "outcome": str(
                    raw.get("declared_verdict") or raw.get("event_type") or "unknown"
                ),
                "validation": str(raw.get("validation_status") or "not_applicable"),
                "summary": summary[:2_000],
                "cost_usd": float(raw.get("charged_cost_usd") or 0),
                "trace_sha256": str(trace["sha256"]),
                "consensus_eligible": bool(raw.get("consensus_eligible")),
            }
        )

    study = handoff["study"]
    classification = handoff["classification"]
    consensus_reason = (
        supplemental.get("decision_reason")
        if isinstance(supplemental, dict)
        else final_review["decision"].get("hard_fail_reason")
    )
    email_body = required["email"].read_text()
    subject_match = re.search(r"^\*\*Subject:\*\*\s*(.+)$", email_body, re.MULTILINE)
    if subject_match is None:
        raise ReviewPacketError("AUTHOR_EMAIL.md does not contain a subject line")
    submitted_at = (
        supplemental.get("decided_at_utc")
        if isinstance(supplemental, dict)
        else final_review["completed_at_utc"]
    )
    packet = {
        "schema_version": TASK_SCHEMA,
        "task_id": args.task_id,
        "supersedes_task_id": args.supersedes_task_id,
        "priority": args.priority,
        "queued_reason": str(consensus_reason),
        "submitted_at_utc": submitted_at,
        "study": {
            "study_id": str(study["id"]),
            "paper_title": str(study["title"]),
            "paper_url": str(study["arxiv_url"]),
            "arxiv_id": str(study["arxiv_id"]),
            "replication_assessment": str(classification["replication_outcome"])
            .replace("_", " ")
            .title(),
            "method_assessment": str(classification["underlying_method_claim"])
            .replace("_", " ")
            .title(),
        },
        "source": {
            "source_revision": source_revision,
            "repository_url": repository_url,
            "pull_request_url": args.pull_request_url,
            "review_packet_sha256": str(final_review["packet"]["sha256"]),
            "final_peer_review_sha256": _canonical_json_file_sha(
                required["final_review"]
            ),
            "supplemental_review_consensus_sha256": _sha256_file(supplemental_path)
            if supplemental_path.is_file()
            else None,
            "fable_action_closure_sha256": _canonical_json_file_sha(closure_path)
            if closure_path.is_file()
            else None,
        },
        "brief": required["brief"].read_text(),
        "evidence": evidence,
        "review_events": events,
        "publication_gate": {
            "reason": str(consensus_reason),
            "question": "After reviewing the bound evidence, should this release proceed or remain blocked?",
        },
        "author_email_gate": {
            "subject": subject_match.group(1).strip(),
            "body": email_body,
            "draft_sha256": sha256_text(email_body),
            "recipients": _load_recipients(args.recipients),
        },
    }
    return validate_task_packet(packet)


def _write_private_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("hash-password", help="prompt for and hash one password")

    encode_parser = subparsers.add_parser(
        "encode-accounts",
        help="encode a protected account JSON file for EnvironmentFile",
    )
    encode_parser.add_argument("--input", type=Path, required=True)

    pepper_parser = subparsers.add_parser(
        "generate-pepper", help="generate a review-service pepper"
    )
    pepper_parser.add_argument("--bytes", type=int, default=32)

    validate_parser = subparsers.add_parser(
        "validate-packet", help="validate one inbox packet"
    )
    validate_parser.add_argument("--packet", type=Path, required=True)

    import_parser = subparsers.add_parser(
        "import-task", help="import one immutable inbox packet"
    )
    import_parser.add_argument("--packet", type=Path, required=True)
    import_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    export_parser = subparsers.add_parser(
        "export-decisions", help="export hash-bound human decisions"
    )
    export_parser.add_argument("--task-id", required=True)
    export_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    export_parser.add_argument("--output", type=Path)

    build_parser = subparsers.add_parser(
        "build-study-task",
        help="build a private task from a standard NULSPEC study folder",
    )
    build_parser.add_argument("--study-root", type=Path, required=True)
    build_parser.add_argument("--task-id", required=True)
    build_parser.add_argument(
        "--supersedes-task-id",
        help="prior active task ID when this packet is a revision",
    )
    build_parser.add_argument(
        "--priority", choices=("normal", "high", "urgent"), default="high"
    )
    build_parser.add_argument("--source-revision", required=True)
    build_parser.add_argument("--repository-url", required=True)
    build_parser.add_argument("--pull-request-url")
    build_parser.add_argument("--study-repo-path", required=True)
    build_parser.add_argument("--recipients", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)

    subparsers.add_parser(
        "check-config", help="validate enabled environment configuration"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "hash-password":
        first = getpass.getpass("Password: ")
        second = getpass.getpass("Confirm password: ")
        if first != second:
            raise SystemExit("passwords do not match")
        if len(first) < MIN_PASSWORD_CHARS or len(first) > MAX_PASSWORD_CHARS:
            raise SystemExit(
                f"password must contain {MIN_PASSWORD_CHARS} to {MAX_PASSWORD_CHARS} characters"
            )
        print(generate_password_hash(first, method="scrypt"))
        return 0
    if args.command == "encode-accounts":
        raw = json.loads(args.input.read_text())
        print("NULSPEC_REVIEW_ACCOUNTS_B64=" + encode_accounts(raw))
        return 0
    if args.command == "generate-pepper":
        if not 32 <= args.bytes <= 128:
            raise SystemExit("pepper size must be 32 to 128 bytes")
        print(
            "NULSPEC_REVIEW_PEPPER_B64=" + _b64encode(secrets.token_bytes(args.bytes))
        )
        return 0
    if args.command == "validate-packet":
        packet = validate_task_packet(json.loads(args.packet.read_text()))
        print(f"VALID task={packet['task_id']} sha256={sha256_json(packet)}")
        return 0
    if args.command == "import-task":
        store = ReviewStore(args.database)
        try:
            created = store.import_task(
                json.loads(args.packet.read_text()), now=datetime.now(timezone.utc)
            )
        finally:
            store.close()
        print("IMPORTED" if created else "ALREADY_PRESENT")
        return 0
    if args.command == "export-decisions":
        store = ReviewStore(args.database)
        try:
            task = store.get_task(args.task_id)
        finally:
            store.close()
        if task is None:
            raise SystemExit("review task not found")
        output = {
            "schema_version": "nulspec-human-review-decision-export-v1",
            "task_id": task["task_id"],
            "task_packet_sha256": task["packet_sha256"],
            "decisions": [item["record"] for item in task["decisions"]],
            "decision_record_sha256s": [
                item["record_sha256"] for item in task["decisions"]
            ],
        }
        if args.output:
            _write_private_json(args.output, output)
        else:
            print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "build-study-task":
        packet = build_study_task(args)
        _write_private_json(args.output, packet)
        print(f"BUILT task={packet['task_id']} sha256={sha256_json(packet)}")
        return 0
    if args.command == "check-config":
        service = ReviewService.from_environment()
        print(
            f"VALID accounts={len(service.accounts)} database={service.store.path} "
            f"origins={len(service.allowed_origins)}"
        )
        service.store.close()
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReviewConfigurationError, ReviewPacketError, ReviewStoreError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

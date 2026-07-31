"""Validated NULSPEC paper nominations relayed to a private Discord channel."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import logging
import math
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request
import requests

from nulspec_mail_store import MailStoreError, NominationStore

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 4096
DISCORD_API_ROOT = "https://discord.com/api/v10"
DEFAULT_ALLOWED_ORIGINS = frozenset(
    {
        "https://nulspec.com",
        "https://nulspec-reproducibility-lab.orwelian84.chatgpt.site",
    }
)

EMAIL_RE = re.compile(
    r"^[A-Z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
    r"[A-Z]{2,63}$",
    re.IGNORECASE,
)
MODERN_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$", re.IGNORECASE)
LEGACY_ARXIV_ID_RE = re.compile(
    r"^[a-z][a-z0-9.-]*/\d{7}(?:v\d+)?$",
    re.IGNORECASE,
)
STUDY_ID_RE = re.compile(r"^[0-9]{3,}$")
EXTENSION_OPTION_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEFAULT_RELEASE_MANIFEST = Path("/srv/nulspec/current/release.json")
DEFAULT_MAIL_DATABASE = Path("/var/lib/multibot/nulspec-mail.sqlite3")


class NominationValidationError(ValueError):
    """A nomination field is malformed."""


class ExtensionVoteValidationError(ValueError):
    """An extension-vote field or publication contract is malformed."""


class RateLimitExceeded(RuntimeError):
    """A nomination rate limit was exceeded."""

    def __init__(self, retry_after: int):
        super().__init__("nomination rate limit exceeded")
        self.retry_after = max(1, retry_after)


class RelayUnavailable(RuntimeError):
    """Discord delivery is unavailable."""


@dataclass(frozen=True)
class ValidatedNomination:
    email: str
    arxiv_id: str
    paper_url: str


@dataclass(frozen=True)
class SubmissionResult:
    reference: str
    duplicate: bool


@dataclass(frozen=True)
class ValidatedExtensionVote:
    study_id: str
    study_title: str
    paper_title: str
    paper_url: str
    option_id: str
    option_label: str
    option_role: str
    option_summary: str


class ReleaseManifestRegistry:
    """Resolve vote choices from the currently deployed, hash-bound release."""

    def __init__(self, path: Path = DEFAULT_RELEASE_MANIFEST):
        self.path = path

    def lookup(self, study_id: object, option_id: object) -> ValidatedExtensionVote:
        if not isinstance(study_id, str) or not STUDY_ID_RE.fullmatch(study_id):
            raise ExtensionVoteValidationError("study id is invalid")
        if not isinstance(option_id, str) or not EXTENSION_OPTION_ID_RE.fullmatch(
            option_id
        ):
            raise ExtensionVoteValidationError("extension option id is invalid")

        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise RelayUnavailable("release manifest is unavailable") from exc
        if len(raw) > 1_000_000:
            raise RelayUnavailable("release manifest is unexpectedly large")
        try:
            manifest = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RelayUnavailable("release manifest is invalid") from exc

        publications = manifest.get("publications")
        if not isinstance(publications, list):
            raise RelayUnavailable("release manifest has no publications")
        publication = next(
            (
                item
                for item in publications
                if isinstance(item, dict) and item.get("study_id") == study_id
            ),
            None,
        )
        if publication is None:
            raise ExtensionVoteValidationError("study is not published")

        paper = publication.get("paper")
        extension = publication.get("extension_vote")
        if not (
            isinstance(paper, dict)
            and isinstance(extension, dict)
            and extension.get("requested") is True
            and extension.get("selection_mode") == "single_choice"
            and isinstance(extension.get("options"), list)
        ):
            raise RelayUnavailable("published extension contract is invalid")
        option = next(
            (
                item
                for item in extension["options"]
                if isinstance(item, dict) and item.get("id") == option_id
            ),
            None,
        )
        if option is None:
            raise ExtensionVoteValidationError("extension option is not published")

        values = {
            "study_title": publication.get("study_title"),
            "paper_title": paper.get("title"),
            "paper_url": paper.get("url"),
            "option_label": option.get("label"),
            "option_role": option.get("role"),
            "option_summary": option.get("summary"),
        }
        limits = {
            "study_title": 220,
            "paper_title": 220,
            "paper_url": 300,
            "option_label": 120,
            "option_role": 120,
            "option_summary": 700,
        }
        if any(
            not isinstance(value, str)
            or not value.strip()
            or len(value) > limits[key]
            for key, value in values.items()
        ):
            raise RelayUnavailable("published extension metadata is invalid")
        if not values["paper_url"].startswith("https://arxiv.org/abs/"):
            raise RelayUnavailable("published paper URL is invalid")

        return ValidatedExtensionVote(
            study_id=study_id,
            study_title=values["study_title"],
            paper_title=values["paper_title"],
            paper_url=values["paper_url"],
            option_id=option_id,
            option_label=values["option_label"],
            option_role=values["option_role"],
            option_summary=values["option_summary"],
        )


def normalize_email(value: object) -> str:
    """Return a conservative normalized public email address."""
    if not isinstance(value, str):
        raise NominationValidationError("email must be text")

    email = value.strip().lower()
    if not 3 <= len(email) <= 254:
        raise NominationValidationError("email length is invalid")

    try:
        email.encode("ascii")
    except UnicodeEncodeError as exc:
        raise NominationValidationError("email must use ASCII characters") from exc

    local_part = email.partition("@")[0]
    if len(local_part) > 64 or not EMAIL_RE.fullmatch(email):
        raise NominationValidationError("email is invalid")

    return email


def normalize_arxiv_url(value: object) -> tuple[str, str]:
    """Validate an arxiv.org abstract/PDF URL and return its canonical form."""
    if not isinstance(value, str):
        raise NominationValidationError("paper must be text")

    raw_url = value.strip()
    if not 1 <= len(raw_url) <= 300:
        raise NominationValidationError("paper URL length is invalid")

    try:
        parsed = urlsplit(raw_url)
    except ValueError as exc:
        raise NominationValidationError("paper URL is invalid") from exc

    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname not in {"arxiv.org", "www.arxiv.org"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise NominationValidationError(
            "paper must be a clean HTTPS arxiv.org URL"
        )

    path = parsed.path.rstrip("/")
    if path.startswith("/abs/"):
        arxiv_id = path.removeprefix("/abs/")
    elif path.startswith("/pdf/"):
        arxiv_id = path.removeprefix("/pdf/")
        if arxiv_id.lower().endswith(".pdf"):
            arxiv_id = arxiv_id[:-4]
    else:
        raise NominationValidationError(
            "paper must use an arxiv.org abs or pdf URL"
        )

    arxiv_id = arxiv_id.strip().lower()
    if not (
        MODERN_ARXIV_ID_RE.fullmatch(arxiv_id)
        or LEGACY_ARXIV_ID_RE.fullmatch(arxiv_id)
    ):
        raise NominationValidationError("arXiv identifier is invalid")

    return arxiv_id, f"https://arxiv.org/abs/{arxiv_id}"


def validate_nomination(email: object, paper: object) -> ValidatedNomination:
    """Validate and normalize the two public nomination fields."""
    normalized_email = normalize_email(email)
    arxiv_id, paper_url = normalize_arxiv_url(paper)
    return ValidatedNomination(
        email=normalized_email,
        arxiv_id=arxiv_id,
        paper_url=paper_url,
    )


class SlidingWindowLimiter:
    """Small in-memory limiter for the loopback-only nomination endpoint."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._global_events: deque[float] = deque()
        self._ip_events: dict[str, deque[float]] = defaultdict(deque)
        self._email_events: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _prune(bucket: deque[float], cutoff: float) -> None:
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    @staticmethod
    def _retry_after(bucket: deque[float], window: int, now: float) -> int:
        return max(1, math.ceil(window - (now - bucket[0])))

    def check_and_record(self, client_ip: str, email: str) -> None:
        """Apply global, per-IP, and per-email limits atomically."""
        now = self._clock()
        email_key = hashlib.sha256(email.encode()).hexdigest()

        with self._lock:
            global_window = 3600
            ip_window = 3600
            email_window = 86400
            global_bucket = self._global_events
            ip_bucket = self._ip_events[client_ip]
            email_bucket = self._email_events[email_key]

            self._prune(global_bucket, now - global_window)
            self._prune(ip_bucket, now - ip_window)
            self._prune(email_bucket, now - email_window)

            if len(global_bucket) >= 30:
                raise RateLimitExceeded(
                    self._retry_after(global_bucket, global_window, now)
                )
            if len(ip_bucket) >= 3:
                raise RateLimitExceeded(
                    self._retry_after(ip_bucket, ip_window, now)
                )
            if len(email_bucket) >= 5:
                raise RateLimitExceeded(
                    self._retry_after(email_bucket, email_window, now)
                )

            global_bucket.append(now)
            ip_bucket.append(now)
            email_bucket.append(now)


class NominationRelay:
    """Rate-limit, deduplicate, and deliver nominations through Bob."""

    def __init__(
        self,
        *,
        channel_id: int,
        bot_token: str,
        allowed_origins: frozenset[str] = DEFAULT_ALLOWED_ORIGINS,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] | None = None,
        store: NominationStore | None = None,
    ):
        if channel_id <= 0 or not bot_token:
            raise RelayUnavailable("nomination relay is not configured")

        self.channel_id = channel_id
        self.bot_token = bot_token
        self.allowed_origins = allowed_origins
        self.session = session or requests.Session()
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._limiter = SlidingWindowLimiter(clock)
        self._delivery_lock = threading.Lock()
        self.store = store or NominationStore(":memory:")

    @classmethod
    def from_environment(cls) -> "NominationRelay":
        channel_id = int(os.environ.get("NULSPEC_NOMINATION_CHANNEL_ID", "0"))
        bot_token = os.environ.get("BOB_BOT_TOKEN", "")
        configured_origins = os.environ.get(
            "NULSPEC_NOMINATION_ALLOWED_ORIGINS", ""
        )
        allowed_origins = frozenset(
            origin.strip()
            for origin in configured_origins.split(",")
            if origin.strip()
        )
        return cls(
            channel_id=channel_id,
            bot_token=bot_token,
            allowed_origins=allowed_origins or DEFAULT_ALLOWED_ORIGINS,
            store=NominationStore(
                os.environ.get("NULSPEC_MAIL_DB_PATH", str(DEFAULT_MAIL_DATABASE))
            ),
        )

    def submit(
        self,
        nomination: ValidatedNomination,
        *,
        client_ip: str,
    ) -> SubmissionResult:
        """Persist and deliver one nomination, returning durable duplicates."""
        self._limiter.check_and_record(client_ip, nomination.email)

        with self._delivery_lock:
            submitted_at = self._now().astimezone(timezone.utc)
            reference = (
                f"NLS-{submitted_at:%Y%m%d}-{secrets.token_hex(3).upper()}"
            )
            try:
                claim = self.store.claim_nomination(
                    reference=reference,
                    email=nomination.email,
                    arxiv_id=nomination.arxiv_id,
                    paper_url=nomination.paper_url,
                    submitted_at=submitted_at,
                )
            except (MailStoreError, OSError, sqlite3.Error, ValueError) as exc:
                raise RelayUnavailable("nomination could not be preserved") from exc
            if claim.discord_message_id is not None:
                return SubmissionResult(reference=claim.reference, duplicate=True)

            message_id = self._deliver(
                nomination,
                claim.reference,
                submitted_at,
            )
            try:
                self.store.mark_discord_delivered(claim.reference, message_id)
            except (MailStoreError, OSError, sqlite3.Error, ValueError) as exc:
                raise RelayUnavailable(
                    "nomination delivery could not be committed"
                ) from exc
            logger.info(
                "Relayed NULSPEC nomination %s to Discord message %s.",
                claim.reference,
                message_id,
            )
            return SubmissionResult(reference=claim.reference, duplicate=False)

    def _deliver(
        self,
        nomination: ValidatedNomination,
        reference: str,
        submitted_at: datetime,
    ) -> str:
        endpoint = f"{DISCORD_API_ROOT}/channels/{self.channel_id}/messages"
        nonce = str(
            int.from_bytes(
                hashlib.sha256(reference.encode("ascii")).digest()[:8],
                "big",
            )
        )
        payload = {
            "allowed_mentions": {"parse": []},
            "nonce": nonce,
            "enforce_nonce": True,
            "embeds": [
                {
                    "color": 0x5CE8FF,
                    "title": "New replication nomination",
                    "url": nomination.paper_url,
                    "description": (
                        "A visitor asked NULSPEC to consider this paper for "
                        "independent replication."
                    ),
                    "fields": [
                        {
                            "name": "Paper",
                            "value": (
                                f"[arXiv:{nomination.arxiv_id}]"
                                f"({nomination.paper_url})"
                            ),
                            "inline": False,
                        },
                        {
                            "name": "Contact email",
                            "value": nomination.email,
                            "inline": False,
                        },
                        {
                            "name": "Reference",
                            "value": reference,
                            "inline": True,
                        },
                    ],
                    "footer": {
                        "text": (
                            "NULSPEC intake · a result notice will be sent "
                            "if this paper is published"
                        )
                    },
                    "timestamp": submitted_at.isoformat(),
                }
            ],
        }
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "NULSPEC-Nomination-Relay/1.0",
        }

        for attempt in range(3):
            try:
                response = self.session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=(3.05, 10),
                )
            except requests.RequestException as exc:
                if attempt < 2:
                    time.sleep(0.4 * (2**attempt))
                    continue
                raise RelayUnavailable("Discord delivery failed") from exc

            if response.status_code in {200, 201}:
                try:
                    message_id = str(response.json()["id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise RelayUnavailable(
                        "Discord returned an invalid response"
                    ) from exc
                return message_id

            if response.status_code == 429 and attempt < 2:
                try:
                    retry_after = float(response.json().get("retry_after", 1))
                except (TypeError, ValueError):
                    retry_after = 1
                time.sleep(min(3, max(0.1, retry_after)))
                continue

            if 500 <= response.status_code < 600 and attempt < 2:
                time.sleep(0.4 * (2**attempt))
                continue

            logger.error(
                "Discord nomination relay returned HTTP %s for %s.",
                response.status_code,
                reference,
            )
            raise RelayUnavailable("Discord delivery was rejected")

        raise RelayUnavailable("Discord delivery failed")


class ExtensionVoteLimiter:
    """Bound anonymous vote traffic without retaining raw network addresses."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._global_events: deque[float] = deque()
        self._network_events: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, client_ip: str) -> None:
        now = self._clock()
        network_key = hashlib.sha256(client_ip.encode()).hexdigest()
        with self._lock:
            global_window = 3600
            network_window = 3600
            SlidingWindowLimiter._prune(
                self._global_events, now - global_window
            )
            network_bucket = self._network_events[network_key]
            SlidingWindowLimiter._prune(network_bucket, now - network_window)
            if len(self._global_events) >= 120:
                raise RateLimitExceeded(
                    SlidingWindowLimiter._retry_after(
                        self._global_events, global_window, now
                    )
                )
            if len(network_bucket) >= 5:
                raise RateLimitExceeded(
                    SlidingWindowLimiter._retry_after(
                        network_bucket, network_window, now
                    )
                )
            self._global_events.append(now)
            network_bucket.append(now)


class ExtensionVoteRelay:
    """Validate current choices and relay anonymous extension votes through Bob."""

    def __init__(
        self,
        *,
        channel_id: int,
        bot_token: str,
        allowed_origins: frozenset[str] = DEFAULT_ALLOWED_ORIGINS,
        registry: ReleaseManifestRegistry | None = None,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] | None = None,
    ):
        if channel_id <= 0 or not bot_token:
            raise RelayUnavailable("extension vote relay is not configured")
        self.channel_id = channel_id
        self.bot_token = bot_token
        self.allowed_origins = allowed_origins
        self.registry = registry or ReleaseManifestRegistry()
        self.session = session or requests.Session()
        self._clock = clock
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._limiter = ExtensionVoteLimiter(clock)
        self._delivery_lock = threading.Lock()
        self._recent: dict[str, tuple[float, str]] = {}

    @classmethod
    def from_environment(cls) -> "ExtensionVoteRelay":
        channel_id = int(os.environ.get("NULSPEC_NOMINATION_CHANNEL_ID", "0"))
        bot_token = os.environ.get("BOB_BOT_TOKEN", "")
        configured_origins = os.environ.get(
            "NULSPEC_NOMINATION_ALLOWED_ORIGINS", ""
        )
        manifest_path = Path(
            os.environ.get(
                "NULSPEC_RELEASE_MANIFEST", str(DEFAULT_RELEASE_MANIFEST)
            )
        )
        allowed_origins = frozenset(
            origin.strip()
            for origin in configured_origins.split(",")
            if origin.strip()
        )
        return cls(
            channel_id=channel_id,
            bot_token=bot_token,
            allowed_origins=allowed_origins or DEFAULT_ALLOWED_ORIGINS,
            registry=ReleaseManifestRegistry(manifest_path),
        )

    @staticmethod
    def _fingerprint(client_ip: str, study_id: str) -> str:
        return hashlib.sha256(f"{client_ip}\0{study_id}".encode()).hexdigest()

    def _prune_recent(self, now: float) -> None:
        cutoff = now - 86400
        self._recent = {
            key: value for key, value in self._recent.items() if value[0] > cutoff
        }

    def submit(
        self,
        study_id: object,
        option_id: object,
        *,
        client_ip: str,
    ) -> SubmissionResult:
        vote = self.registry.lookup(study_id, option_id)
        fingerprint = self._fingerprint(client_ip, vote.study_id)
        with self._delivery_lock:
            monotonic_now = self._clock()
            self._prune_recent(monotonic_now)
            if fingerprint in self._recent:
                return SubmissionResult(
                    reference=self._recent[fingerprint][1], duplicate=True
                )
            self._limiter.check_and_record(client_ip)
            submitted_at = self._now().astimezone(timezone.utc)
            reference = f"NLE-{submitted_at:%Y%m%d}-{secrets.token_hex(3).upper()}"
            message_id = self._deliver(vote, reference, submitted_at)
            self._recent[fingerprint] = (monotonic_now, reference)
            logger.info(
                "Relayed NULSPEC extension vote %s to Discord message %s.",
                reference,
                message_id,
            )
            return SubmissionResult(reference=reference, duplicate=False)

    def _deliver(
        self,
        vote: ValidatedExtensionVote,
        reference: str,
        submitted_at: datetime,
    ) -> str:
        endpoint = f"{DISCORD_API_ROOT}/channels/{self.channel_id}/messages"
        payload = {
            "allowed_mentions": {"parse": []},
            "embeds": [
                {
                    "color": 0x5CE8FF,
                    "title": f"Vote to extend NULSPEC Study {vote.study_id}",
                    "url": vote.paper_url,
                    "description": (
                        "A visitor voted for a follow-up to the frozen primary result."
                    ),
                    "fields": [
                        {
                            "name": "Paper",
                            "value": f"[{vote.paper_title}]({vote.paper_url})",
                            "inline": False,
                        },
                        {
                            "name": "Selected extension",
                            "value": f"**{vote.option_label}**\n{vote.option_summary}",
                            "inline": False,
                        },
                        {
                            "name": "Role",
                            "value": vote.option_role.replace("_", " "),
                            "inline": True,
                        },
                        {
                            "name": "Reference",
                            "value": reference,
                            "inline": True,
                        },
                    ],
                    "footer": {
                        "text": (
                            "NULSPEC extension vote · anonymous · primary verdict frozen"
                        )
                    },
                    "timestamp": submitted_at.isoformat(),
                }
            ],
        }
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "NULSPEC-Extension-Vote-Relay/1.0",
        }
        for attempt in range(3):
            try:
                response = self.session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=(3.05, 10),
                )
            except requests.RequestException as exc:
                if attempt < 2:
                    time.sleep(0.4 * (2**attempt))
                    continue
                raise RelayUnavailable("Discord delivery failed") from exc
            if response.status_code in {200, 201}:
                try:
                    return str(response.json()["id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise RelayUnavailable(
                        "Discord returned an invalid response"
                    ) from exc
            if response.status_code == 429 and attempt < 2:
                try:
                    retry_after = float(response.json().get("retry_after", 1))
                except (TypeError, ValueError):
                    retry_after = 1
                time.sleep(min(3, max(0.1, retry_after)))
                continue
            if 500 <= response.status_code < 600 and attempt < 2:
                time.sleep(0.4 * (2**attempt))
                continue
            logger.error(
                "Discord extension vote relay returned HTTP %s for %s.",
                response.status_code,
                reference,
            )
            raise RelayUnavailable("Discord delivery was rejected")
        raise RelayUnavailable("Discord delivery failed")


class DisabledNominationRelay:
    """Fail closed without preventing the existing bots from starting."""

    allowed_origins = DEFAULT_ALLOWED_ORIGINS

    def submit(
        self,
        nomination: ValidatedNomination,
        *,
        client_ip: str,
    ) -> SubmissionResult:
        del nomination, client_ip
        raise RelayUnavailable("nomination relay is disabled")


class DisabledExtensionVoteRelay:
    """Fail closed without preventing the existing bots from starting."""

    allowed_origins = DEFAULT_ALLOWED_ORIGINS

    def submit(
        self,
        study_id: object,
        option_id: object,
        *,
        client_ip: str,
    ) -> SubmissionResult:
        del study_id, option_id, client_ip
        raise RelayUnavailable("extension vote relay is disabled")


def _client_ip() -> str:
    peer = request.remote_addr or "unknown"
    if peer not in {"127.0.0.1", "::1"}:
        return peer

    forwarded = request.headers.get("X-Nulspec-Client-IP", "").strip()
    try:
        return str(ipaddress.ip_address(forwarded))
    except ValueError:
        return peer


def _json_response(
    payload: dict[str, object],
    status: int,
    *,
    origin: str | None = None,
) -> Response:
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response


def register_nulspec_nomination_routes(
    app: Flask,
    *,
    relay: NominationRelay | DisabledNominationRelay | None = None,
) -> None:
    """Register the nomination endpoint on the existing loopback Flask app."""
    if relay is None:
        try:
            relay = NominationRelay.from_environment()
        except (
            MailStoreError,
            OSError,
            RelayUnavailable,
            sqlite3.Error,
            TypeError,
            ValueError,
        ) as exc:
            logger.warning("NULSPEC nomination relay disabled: %s", exc)
            relay = DisabledNominationRelay()

    app.extensions["nulspec_nomination_relay"] = relay

    @app.route("/api/nominations", methods=["POST", "OPTIONS"])
    def nulspec_nominations() -> Response:
        origin = request.headers.get("Origin", "")
        if origin not in relay.allowed_origins:
            return _json_response(
                {"ok": False, "error": "forbidden_origin"},
                403,
            )

        if request.method == "OPTIONS":
            response = _json_response({"ok": True}, 204, origin=origin)
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "600"
            return response

        if request.content_length and request.content_length > MAX_BODY_BYTES:
            return _json_response(
                {"ok": False, "error": "payload_too_large"},
                413,
                origin=origin,
            )

        if not request.is_json:
            return _json_response(
                {"ok": False, "error": "json_required"},
                415,
                origin=origin,
            )

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _json_response(
                {"ok": False, "error": "invalid_json"},
                400,
                origin=origin,
            )

        allowed_keys = {"email", "paper", "company"}
        if set(payload) - allowed_keys:
            return _json_response(
                {"ok": False, "error": "unexpected_fields"},
                400,
                origin=origin,
            )

        company = payload.get("company", "")
        if not isinstance(company, str):
            return _json_response(
                {"ok": False, "error": "invalid_nomination"},
                400,
                origin=origin,
            )
        if company.strip():
            return _json_response(
                {"ok": True, "reference": "NLS-RECEIVED"},
                202,
                origin=origin,
            )

        try:
            nomination = validate_nomination(
                payload.get("email"),
                payload.get("paper"),
            )
            result = relay.submit(nomination, client_ip=_client_ip())
        except NominationValidationError:
            return _json_response(
                {"ok": False, "error": "invalid_nomination"},
                422,
                origin=origin,
            )
        except RateLimitExceeded as exc:
            response = _json_response(
                {"ok": False, "error": "rate_limited"},
                429,
                origin=origin,
            )
            response.headers["Retry-After"] = str(exc.retry_after)
            return response
        except RelayUnavailable:
            logger.exception("NULSPEC nomination relay is unavailable.")
            return _json_response(
                {"ok": False, "error": "relay_unavailable"},
                503,
                origin=origin,
            )

        return _json_response(
            {
                "ok": True,
                "reference": result.reference,
                "duplicate": result.duplicate,
            },
            202,
            origin=origin,
        )


def register_nulspec_extension_vote_routes(
    app: Flask,
    *,
    relay: ExtensionVoteRelay | DisabledExtensionVoteRelay | None = None,
) -> None:
    """Register the hash-bound extension-vote endpoint."""
    if relay is None:
        try:
            relay = ExtensionVoteRelay.from_environment()
        except (RelayUnavailable, TypeError, ValueError) as exc:
            logger.warning("NULSPEC extension vote relay disabled: %s", exc)
            relay = DisabledExtensionVoteRelay()

    app.extensions["nulspec_extension_vote_relay"] = relay

    @app.route("/api/extension-votes", methods=["POST", "OPTIONS"])
    def nulspec_extension_votes() -> Response:
        origin = request.headers.get("Origin", "")
        if origin not in relay.allowed_origins:
            return _json_response(
                {"ok": False, "error": "forbidden_origin"}, 403
            )
        if request.method == "OPTIONS":
            response = _json_response({"ok": True}, 204, origin=origin)
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "600"
            return response
        if request.content_length and request.content_length > MAX_BODY_BYTES:
            return _json_response(
                {"ok": False, "error": "payload_too_large"}, 413, origin=origin
            )
        if not request.is_json:
            return _json_response(
                {"ok": False, "error": "json_required"}, 415, origin=origin
            )
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _json_response(
                {"ok": False, "error": "invalid_json"}, 400, origin=origin
            )
        if set(payload) - {"study_id", "option_id", "company"}:
            return _json_response(
                {"ok": False, "error": "unexpected_fields"}, 400, origin=origin
            )
        company = payload.get("company", "")
        if not isinstance(company, str):
            return _json_response(
                {"ok": False, "error": "invalid_extension_vote"},
                400,
                origin=origin,
            )
        if company.strip():
            return _json_response(
                {"ok": True, "reference": "NLE-RECEIVED"}, 202, origin=origin
            )
        try:
            result = relay.submit(
                payload.get("study_id"),
                payload.get("option_id"),
                client_ip=_client_ip(),
            )
        except ExtensionVoteValidationError:
            return _json_response(
                {"ok": False, "error": "invalid_extension_vote"},
                422,
                origin=origin,
            )
        except RateLimitExceeded as exc:
            response = _json_response(
                {"ok": False, "error": "rate_limited"}, 429, origin=origin
            )
            response.headers["Retry-After"] = str(exc.retry_after)
            return response
        except RelayUnavailable:
            logger.exception("NULSPEC extension vote relay is unavailable.")
            return _json_response(
                {"ok": False, "error": "relay_unavailable"}, 503, origin=origin
            )
        return _json_response(
            {
                "ok": True,
                "reference": result.reference,
                "duplicate": result.duplicate,
            },
            202,
            origin=origin,
        )

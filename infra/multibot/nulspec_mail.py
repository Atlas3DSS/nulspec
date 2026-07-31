#!/usr/bin/env python3
"""Send completed NULSPEC results and relay researcher replies to Discord."""

from __future__ import annotations

import argparse
import hashlib
import imaplib
import json
import logging
import os
import re
import smtplib
import sqlite3
import ssl
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import format_datetime, formataddr, parseaddr, parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import requests
from nulspec_mail_store import (
    REFERENCE_RE,
    MailStoreError,
    NominationStore,
    PendingNotification,
)

logger = logging.getLogger(__name__)

DISCORD_API_ROOT = "https://discord.com/api/v10"
DEFAULT_DATABASE = Path("/var/lib/multibot/nulspec-mail.sqlite3")
DEFAULT_RELEASE_MANIFEST = Path("/srv/nulspec/current/release.json")
DEFAULT_MAILBOX = "research@nulspec.com"
DEFAULT_CHANNEL_ID = 1532567350472343653
DEFAULT_SMTP_HOST = "smtp.purelymail.com"
DEFAULT_IMAP_HOST = "imap.purelymail.com"
MAX_MANIFEST_BYTES = 1_000_000
MAX_INBOUND_BYTES = 10 * 1024 * 1024
CLASSIFICATIONS = {
    "REPRODUCED",
    "PARTIALLY_REPRODUCED",
    "NOT_REPRODUCED",
    "INCONCLUSIVE",
}
ARXIV_ID_RE = re.compile(
    r"^(?:[0-9]{4}\.[0-9]{4,5}|[a-z][a-z0-9.-]*/[0-9]{7})(?:v[0-9]+)?$",
    re.IGNORECASE,
)
ARXIV_EMBED_RE = re.compile(
    r"https://arxiv\.org/abs/"
    r"((?:[0-9]{4}\.[0-9]{4,5}|[a-z][a-z0-9.-]*/[0-9]{7})"
    r"(?:v[0-9]+)?)(?=[)\s]|$)",
    re.IGNORECASE,
)
REFERENCE_SEARCH_RE = re.compile(r"NLS-[0-9]{8}-[A-F0-9]{6}")


class MailConfigurationError(ValueError):
    """Required worker configuration is missing or unsafe."""


class PublicationNoticeError(ValueError):
    """A deployed publication cannot safely become an email notice."""


class MailDeliveryError(RuntimeError):
    """A remote SMTP, IMAP, or Discord operation failed."""


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MailConfigurationError(f"{name} is required")
    return value


def _environment_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise MailConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise MailConfigurationError(f"{name} is outside its allowed range")
    return value


@dataclass(frozen=True)
class MailSettings:
    database_path: Path
    release_manifest: Path
    mailbox: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    discord_channel_id: int
    discord_bot_token: str
    poll_seconds: int

    @classmethod
    def from_environment(cls) -> MailSettings:
        mailbox = os.environ.get("NULSPEC_MAILBOX", DEFAULT_MAILBOX).strip().lower()
        if mailbox != DEFAULT_MAILBOX:
            raise MailConfigurationError(f"NULSPEC_MAILBOX must be {DEFAULT_MAILBOX}")
        smtp_host = os.environ.get("NULSPEC_MAIL_SMTP_HOST", DEFAULT_SMTP_HOST).strip()
        imap_host = os.environ.get("NULSPEC_MAIL_IMAP_HOST", DEFAULT_IMAP_HOST).strip()
        if smtp_host != DEFAULT_SMTP_HOST:
            raise MailConfigurationError(f"SMTP host must be {DEFAULT_SMTP_HOST}")
        if imap_host != DEFAULT_IMAP_HOST:
            raise MailConfigurationError(f"IMAP host must be {DEFAULT_IMAP_HOST}")
        database_path = Path(
            os.environ.get("NULSPEC_MAIL_DB_PATH", str(DEFAULT_DATABASE))
        )
        release_manifest = Path(
            os.environ.get(
                "NULSPEC_MAIL_RELEASE_MANIFEST",
                str(DEFAULT_RELEASE_MANIFEST),
            )
        )
        if not database_path.is_absolute() or not release_manifest.is_absolute():
            raise MailConfigurationError(
                "mail state and release paths must be absolute"
            )
        smtp_port = _environment_int("NULSPEC_MAIL_SMTP_PORT", 465, 1, 65535)
        imap_port = _environment_int("NULSPEC_MAIL_IMAP_PORT", 993, 1, 65535)
        if smtp_port != 465 or imap_port != 993:
            raise MailConfigurationError(
                "mail transport must use TLS ports 465 and 993"
            )
        smtp_username = (
            os.environ.get("NULSPEC_MAIL_SMTP_USERNAME", mailbox).strip().lower()
        )
        imap_username = (
            os.environ.get("NULSPEC_MAIL_IMAP_USERNAME", mailbox).strip().lower()
        )
        if smtp_username != mailbox or imap_username != mailbox:
            raise MailConfigurationError(
                "mail usernames must match the research mailbox"
            )
        channel_id = _environment_int(
            "NULSPEC_MAIL_CHANNEL_ID",
            DEFAULT_CHANNEL_ID,
            1,
            (2**63) - 1,
        )
        if channel_id != DEFAULT_CHANNEL_ID:
            raise MailConfigurationError(
                "Discord relay channel is not the pinned channel"
            )
        return cls(
            database_path=database_path,
            release_manifest=release_manifest,
            mailbox=mailbox,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=_required_environment("NULSPEC_MAIL_SMTP_PASSWORD"),
            imap_host=imap_host,
            imap_port=imap_port,
            imap_username=imap_username,
            imap_password=_required_environment("NULSPEC_MAIL_IMAP_PASSWORD"),
            discord_channel_id=channel_id,
            discord_bot_token=_required_environment("BOB_BOT_TOKEN"),
            poll_seconds=_environment_int("NULSPEC_MAIL_POLL_SECONDS", 60, 30, 3600),
        )


def _bounded_text(value: object, *, name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise PublicationNoticeError(f"{name} must be text")
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > limit:
        raise PublicationNoticeError(f"{name} is empty or oversized")
    return normalized


def load_publication_notices(path: Path) -> list[dict[str, object]]:
    """Load bounded, public-only completion content from the live manifest."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PublicationNoticeError("release manifest is unavailable") from exc
    if len(raw) > MAX_MANIFEST_BYTES:
        raise PublicationNoticeError("release manifest is unexpectedly large")
    try:
        manifest = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PublicationNoticeError("release manifest is invalid") from exc
    if not isinstance(manifest, dict):
        raise PublicationNoticeError("release manifest contract is invalid")
    publications = manifest.get("publications")
    if manifest.get("schema_version") != 1 or not isinstance(publications, list):
        raise PublicationNoticeError("release manifest contract is invalid")

    notices: list[dict[str, object]] = []
    seen_studies: set[str] = set()
    for publication in publications:
        if not isinstance(publication, dict):
            raise PublicationNoticeError("publication must be an object")
        study_id = str(publication.get("study_id", ""))
        if not study_id.isdigit() or study_id in seen_studies:
            raise PublicationNoticeError("study ID is invalid or duplicated")
        seen_studies.add(study_id)
        paper = publication.get("paper")
        result = publication.get("result_notification")
        classification = publication.get("classification")
        if not isinstance(paper, dict) or not isinstance(result, dict):
            raise PublicationNoticeError("publication notice metadata is missing")
        if classification not in CLASSIFICATIONS:
            raise PublicationNoticeError("publication classification is invalid")

        arxiv_id = _bounded_text(
            paper.get("arxiv_id"), name="arXiv ID", limit=80
        ).lower()
        if not ARXIV_ID_RE.fullmatch(arxiv_id):
            raise PublicationNoticeError("publication arXiv ID is invalid")
        paper_url = f"https://arxiv.org/abs/{arxiv_id}"
        if paper.get("url") != paper_url:
            raise PublicationNoticeError("publication paper URL is not canonical")
        study_url = f"https://nulspec.com/studies/{study_id}/"
        if result.get("study_url") != study_url:
            raise PublicationNoticeError("publication study URL is invalid")
        full_report_url = _bounded_text(
            result.get("full_report_url"), name="full report URL", limit=500
        )
        parsed_report = urlsplit(full_report_url)
        if (
            not full_report_url.startswith(f"{study_url}artifacts/")
            or parsed_report.scheme != "https"
            or parsed_report.hostname != "nulspec.com"
            or parsed_report.query
            or parsed_report.fragment
            or ".." in Path(parsed_report.path).parts
        ):
            raise PublicationNoticeError("publication report URL is invalid")
        findings = result.get("key_findings")
        if not isinstance(findings, list) or not 1 <= len(findings) <= 10:
            raise PublicationNoticeError("publication findings are invalid")

        notices.append(
            {
                "study_id": study_id,
                "study_title": _bounded_text(
                    publication.get("study_title"),
                    name="study title",
                    limit=240,
                ),
                "paper_title": _bounded_text(
                    paper.get("title"), name="paper title", limit=240
                ),
                "arxiv_id": arxiv_id,
                "paper_url": paper_url,
                "classification": classification,
                "study_url": study_url,
                "full_report_url": full_report_url,
                "headline": _bounded_text(
                    result.get("headline"), name="headline", limit=240
                ),
                "summary": _bounded_text(
                    result.get("summary"), name="summary", limit=1_200
                ),
                "key_findings": [
                    _bounded_text(item, name="key finding", limit=700)
                    for item in findings
                ],
            }
        )
    return notices


def _classification_label(value: object) -> str:
    return str(value).replace("_", " ").title()


def build_completion_message(
    pending: PendingNotification,
    *,
    mailbox: str,
    now: datetime,
) -> EmailMessage:
    """Create the stable plain-text and HTML completion message."""
    notice = pending.notice
    findings = [str(item) for item in notice["key_findings"]]
    paper_title = str(notice["paper_title"])
    classification = _classification_label(notice["classification"])
    subject_title = (
        paper_title if len(paper_title) <= 120 else paper_title[:117] + "..."
    )

    message = EmailMessage(policy=policy.default)
    message["From"] = formataddr(("NULSPEC Research", mailbox))
    message["To"] = pending.contact_email
    message["Reply-To"] = mailbox
    message["Date"] = format_datetime(now.astimezone(timezone.utc))
    message["Message-ID"] = pending.message_id
    message["Subject"] = f"[NULSPEC] Replication complete: {subject_title}"
    message["Auto-Submitted"] = "auto-generated"
    message["X-Auto-Response-Suppress"] = "All"
    message["X-NULSPEC-Reference"] = pending.reference

    plain_findings = "\n".join(f"- {finding}" for finding in findings)
    plain = (
        f"You nominated this paper for independent replication on "
        f"{pending.submitted_at} (reference {pending.reference}).\n\n"
        f"{paper_title}\n"
        f"{notice['paper_url']}\n\n"
        f"NULSPEC verdict: {classification}\n"
        f"{notice['headline']}\n\n"
        f"{notice['summary']}\n\n"
        f"Key findings\n{plain_findings}\n\n"
        f"Read the study: {notice['study_url']}\n"
        f"Full report: {notice['full_report_url']}\n\n"
        "You received this one-time result because this address nominated the "
        "paper. NULSPEC does not use nomination addresses for marketing. You "
        "may reply to this email; replies are routed to the private NULSPEC "
        "staff channel.\n"
    )
    message.set_content(plain)

    html_findings = "".join(f"<li>{escape(item)}</li>" for item in findings)
    html = (
        "<!doctype html><html><body>"
        f"<p>You nominated this paper for independent replication on "
        f"{escape(pending.submitted_at)} (reference "
        f"<strong>{escape(pending.reference)}</strong>).</p>"
        f"<p><strong>{escape(paper_title)}</strong><br>"
        f'<a href="{escape(str(notice["paper_url"]), quote=True)}">'
        "View on arXiv</a></p>"
        f"<p><strong>NULSPEC verdict: {escape(classification)}</strong><br>"
        f"{escape(str(notice['headline']))}</p>"
        f"<p>{escape(str(notice['summary']))}</p>"
        f"<p><strong>Key findings</strong></p><ul>{html_findings}</ul>"
        f'<p><a href="{escape(str(notice["study_url"]), quote=True)}">'
        "Read the study</a> &middot; "
        f'<a href="{escape(str(notice["full_report_url"]), quote=True)}">'
        "Full report</a></p>"
        "<p><small>You received this one-time result because this address "
        "nominated the paper. NULSPEC does not use nomination addresses for "
        "marketing. You may reply; replies go to the private NULSPEC staff "
        "channel.</small></p>"
        "</body></html>"
    )
    message.add_alternative(html, subtype="html")
    return message


class SMTPDelivery:
    """Deliver one stable completion message over authenticated TLS SMTP."""

    def __init__(self, settings: MailSettings):
        self.settings = settings
        self.context = ssl.create_default_context()

    def send(self, pending: PendingNotification, *, now: datetime) -> None:
        message = build_completion_message(
            pending,
            mailbox=self.settings.mailbox,
            now=now,
        )
        try:
            with smtplib.SMTP_SSL(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=20,
                context=self.context,
            ) as client:
                client.login(
                    self.settings.smtp_username,
                    self.settings.smtp_password,
                )
                client.send_message(
                    message,
                    from_addr=self.settings.mailbox,
                    to_addrs=[pending.contact_email],
                )
        except (OSError, smtplib.SMTPException) as exc:
            raise MailDeliveryError("SMTP result delivery failed") from exc


def _strip_controls(value: str, *, keep_newlines: bool) -> str:
    allowed = {"\n", "\t"} if keep_newlines else set()
    return "".join(
        character
        for character in value
        if character in allowed or not unicodedata.category(character).startswith("C")
    )


def _safe_header(value: object, *, limit: int) -> str:
    cleaned = _strip_controls(str(value or ""), keep_newlines=False)
    normalized = " ".join(cleaned.split())
    return normalized[:limit]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag in {"br", "p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def _normalize_body(value: str, *, limit: int = 3_500) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _strip_controls(value, keep_newlines=True)
    lines = [" ".join(line.split()) for line in value.split("\n")]
    collapsed: list[str] = []
    for line in lines:
        if line or (collapsed and collapsed[-1]):
            collapsed.append(line)
    text = "\n".join(collapsed).strip()
    if len(text) > limit:
        return text[: limit - 24].rstrip() + "\n\n[message truncated]"
    return text


def _message_body(message: Message) -> str:
    plain: str | None = None
    html: str | None = None
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            continue
        try:
            content = part.get_content()
        except (LookupError, UnicodeError):
            payload = part.get_payload(decode=True) or b""
            content = payload.decode("utf-8", errors="replace")
        if not isinstance(content, str):
            continue
        if content_type == "text/plain" and plain is None:
            plain = content
        elif content_type == "text/html" and html is None:
            html = content
    if plain is not None:
        return _normalize_body(plain)
    if html is not None:
        parser = _HTMLTextExtractor()
        parser.feed(html)
        return _normalize_body(parser.text())
    return ""


@dataclass(frozen=True)
class IncomingMail:
    sender: str
    subject: str
    body: str
    attachments: tuple[str, ...]
    message_id: str | None
    reference: str | None
    received_at: datetime


def parse_incoming_message(
    raw: bytes,
    *,
    store: NominationStore,
    now: datetime,
) -> IncomingMail:
    """Convert an arbitrary MIME message into a bounded Discord-safe summary."""
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
    except (ValueError, TypeError) as exc:
        raise MailDeliveryError("inbound message could not be parsed") from exc

    display_name, address = parseaddr(str(message.get("From", "")))
    display_name = _safe_header(display_name, limit=160)
    address = _safe_header(address, limit=254)
    sender = f"{display_name} <{address}>" if display_name and address else address
    sender = sender or "Unknown sender"
    subject = _safe_header(message.get("Subject", "(no subject)"), limit=500)
    message_id_value = _safe_header(message.get("Message-ID"), limit=250)
    message_id = message_id_value or None

    reference_header = _safe_header(message.get("X-NULSPEC-Reference"), limit=80)
    reference = reference_header if REFERENCE_RE.fullmatch(reference_header) else None
    if reference is None:
        match = REFERENCE_SEARCH_RE.search(subject)
        if match:
            reference = match.group(0)
    if reference is None:
        for header_name in ("In-Reply-To", "References"):
            thread_header = _safe_header(message.get(header_name), limit=2_000)
            candidates = re.findall(r"<[^<>\s]{1,240}>", thread_header)
            for candidate in reversed(candidates):
                reference = store.reference_for_message_id(candidate)
                if reference is not None:
                    break
            if reference is not None:
                break

    attachments: list[str] = []
    for part in message.iter_attachments():
        filename = _safe_header(part.get_filename(), limit=180)
        media_type = _safe_header(part.get_content_type(), limit=100)
        attachments.append(filename or media_type or "unnamed attachment")
        if len(attachments) == 10:
            break

    received_at = now.astimezone(timezone.utc)
    date_header = message.get("Date")
    if date_header:
        try:
            parsed_date = parsedate_to_datetime(str(date_header))
            if (
                parsed_date.tzinfo is not None
                and 2000 <= parsed_date.year <= now.year + 1
            ):
                received_at = parsed_date.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass

    return IncomingMail(
        sender=sender,
        subject=subject or "(no subject)",
        body=_message_body(message),
        attachments=tuple(attachments),
        message_id=message_id,
        reference=reference,
        received_at=received_at,
    )


class DiscordReplyRelay:
    """Post a bounded inbox message to the private research channel."""

    def __init__(
        self,
        *,
        channel_id: int,
        bot_token: str,
        session: requests.Session | None = None,
    ):
        self.channel_id = channel_id
        self.bot_token = bot_token
        self.session = session or requests.Session()

    def deliver(
        self,
        message: IncomingMail,
        *,
        mailbox: str,
        uidvalidity: int,
        uid: int,
    ) -> str:
        endpoint = f"{DISCORD_API_ROOT}/channels/{self.channel_id}/messages"
        delivery_notice = (
            "mailer-daemon" in message.sender.lower()
            or message.subject.lower().startswith(
                ("undeliverable", "delivery status", "returned mail")
            )
        )

        def literal_field(value: str) -> str:
            escaped = re.sub(r"([\\`*_{}\[\]()<>#+\-.!|~>])", r"\\\1", value)
            return escaped[:1024] or "(empty)"

        literal_body = message.body.replace("```", "``\u200b`")
        description = (
            f"```\n{literal_body}\n```" if literal_body else "(No readable text body.)"
        )
        fields: list[dict[str, object]] = [
            {
                "name": "From",
                "value": literal_field(message.sender),
                "inline": False,
            },
            {
                "name": "Subject",
                "value": literal_field(message.subject),
                "inline": False,
            },
        ]
        if message.reference:
            fields.append(
                {
                    "name": "Nomination reference",
                    "value": message.reference,
                    "inline": True,
                }
            )
        if message.attachments:
            fields.append(
                {
                    "name": "Attachments (not forwarded)",
                    "value": literal_field(
                        "\n".join(f"• {name}" for name in message.attachments)
                    ),
                    "inline": False,
                }
            )
        nonce_source = f"{mailbox}\0{uidvalidity}\0{uid}".encode()
        nonce = str(int.from_bytes(hashlib.sha256(nonce_source).digest()[:8], "big"))
        payload = {
            "allowed_mentions": {"parse": []},
            "nonce": nonce,
            "enforce_nonce": True,
            "embeds": [
                {
                    "color": 0x5CE8FF,
                    "title": (
                        "NULSPEC delivery notice"
                        if delivery_notice
                        else "Researcher reply to NULSPEC"
                    ),
                    "description": description,
                    "fields": fields,
                    "footer": {
                        "text": (
                            "NULSPEC research inbox · reply through webmail "
                            "if a response is appropriate"
                        )
                    },
                    "timestamp": message.received_at.isoformat(),
                }
            ],
        }
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "NULSPEC-Mail-Relay/1.0",
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
                raise MailDeliveryError("Discord reply relay failed") from exc
            if response.status_code in {200, 201}:
                try:
                    return str(response.json()["id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise MailDeliveryError(
                        "Discord returned an invalid reply relay response"
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
            raise MailDeliveryError("Discord rejected the reply relay")
        raise MailDeliveryError("Discord reply relay failed")


def _imap_number(response: tuple[str, list[bytes | None]], name: str) -> int:
    status, values = response
    if status != name or not values or values[0] is None:
        raise MailDeliveryError(f"IMAP did not provide {name}")
    try:
        return int(bytes(values[0]).split()[-1])
    except (TypeError, ValueError, IndexError) as exc:
        raise MailDeliveryError(f"IMAP {name} is invalid") from exc


def _fetch_message_bytes(data: list[object]) -> bytes:
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    raise MailDeliveryError("IMAP message body is absent")


class IMAPReplyPoller:
    """Read new inbox UIDs without changing their seen/unseen state."""

    def __init__(
        self,
        settings: MailSettings,
        *,
        store: NominationStore,
        relay: DiscordReplyRelay,
        now: Callable[[], datetime] | None = None,
    ):
        self.settings = settings
        self.store = store
        self.relay = relay
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.context = ssl.create_default_context()

    def poll_once(self) -> int:
        connection: imaplib.IMAP4_SSL | None = None
        delivered = 0
        try:
            connection = imaplib.IMAP4_SSL(
                self.settings.imap_host,
                self.settings.imap_port,
                ssl_context=self.context,
                timeout=20,
            )
            connection.login(
                self.settings.imap_username,
                self.settings.imap_password,
            )
            status, _ = connection.select("INBOX", readonly=True)
            if status != "OK":
                raise MailDeliveryError("IMAP inbox could not be selected")
            uidvalidity = _imap_number(
                connection.response("UIDVALIDITY"), "UIDVALIDITY"
            )
            uidnext = _imap_number(connection.response("UIDNEXT"), "UIDNEXT")
            cursor, initialized = self.store.mailbox_cursor(
                mailbox=self.settings.mailbox,
                uidvalidity=uidvalidity,
                initial_high_water_uid=max(0, uidnext - 1),
                now=self.now(),
            )
            if initialized:
                logger.info(
                    "Initialized NULSPEC inbox cursor at UID %s; existing mail was skipped.",
                    cursor,
                )
                return 0

            status, search_data = connection.uid(
                "search", None, "UID", f"{cursor + 1}:*"
            )
            if status != "OK":
                raise MailDeliveryError("IMAP UID search failed")
            raw_uids = search_data[0].split() if search_data and search_data[0] else []
            for raw_uid in raw_uids[:25]:
                uid = int(raw_uid)
                if uid <= cursor:
                    continue
                if self.store.inbound_delivered(
                    mailbox=self.settings.mailbox,
                    uidvalidity=uidvalidity,
                    uid=uid,
                ):
                    continue
                status, fetch_data = connection.uid("fetch", str(uid), "(BODY.PEEK[])")
                if status != "OK":
                    raise MailDeliveryError("IMAP message fetch failed")
                raw_message = _fetch_message_bytes(fetch_data)
                if len(raw_message) > MAX_INBOUND_BYTES:
                    raise MailDeliveryError("inbound message exceeds 10 MiB")
                parsed = parse_incoming_message(
                    raw_message,
                    store=self.store,
                    now=self.now(),
                )
                self.store.begin_inbound(
                    mailbox=self.settings.mailbox,
                    uidvalidity=uidvalidity,
                    uid=uid,
                    message_id=parsed.message_id,
                    received_at=parsed.received_at,
                )
                discord_message_id = self.relay.deliver(
                    parsed,
                    mailbox=self.settings.mailbox,
                    uidvalidity=uidvalidity,
                    uid=uid,
                )
                self.store.complete_inbound(
                    mailbox=self.settings.mailbox,
                    uidvalidity=uidvalidity,
                    uid=uid,
                    discord_message_id=discord_message_id,
                    now=self.now(),
                )
                cursor = uid
                delivered += 1
            return delivered
        except (
            imaplib.IMAP4.error,
            MailStoreError,
            OSError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            raise MailDeliveryError("IMAP reply polling failed") from exc
        finally:
            if connection is not None:
                try:
                    connection.logout()
                except (imaplib.IMAP4.error, OSError):
                    pass


class DiscordNominationBackfill:
    """Import historical nomination embeds without printing their addresses."""

    def __init__(
        self,
        *,
        store: NominationStore,
        channel_id: int,
        bot_token: str,
        session: requests.Session | None = None,
    ):
        self.store = store
        self.channel_id = channel_id
        self.bot_token = bot_token
        self.session = session or requests.Session()
        self.headers = {
            "Authorization": f"Bot {bot_token}",
            "User-Agent": "NULSPEC-Mail-Backfill/1.0",
        }

    def _get_json(self, endpoint: str, **params: object) -> object:
        try:
            response = self.session.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=(3.05, 15),
            )
        except requests.RequestException as exc:
            raise MailDeliveryError("Discord backfill request failed") from exc
        if response.status_code != 200:
            raise MailDeliveryError("Discord rejected the nomination backfill")
        try:
            return response.json()
        except ValueError as exc:
            raise MailDeliveryError("Discord returned invalid backfill data") from exc

    @staticmethod
    def _parse_embed(message: Mapping[str, object]) -> dict[str, object] | None:
        embeds = message.get("embeds")
        if (
            not isinstance(embeds, list)
            or not embeds
            or not isinstance(embeds[0], dict)
        ):
            return None
        embed = embeds[0]
        if embed.get("title") != "New replication nomination":
            return None
        fields = embed.get("fields")
        if not isinstance(fields, list):
            return None
        values = {
            str(field.get("name")): field.get("value")
            for field in fields
            if isinstance(field, dict)
        }
        email = str(values.get("Contact email", "")).strip().lower()
        paper_value = str(values.get("Paper", ""))
        reference = str(values.get("Reference", ""))
        paper_match = ARXIV_EMBED_RE.search(paper_value)
        message_id = str(message.get("id", ""))
        if (
            not REFERENCE_RE.fullmatch(reference)
            or not paper_match
            or not message_id.isdigit()
            or not 3 <= len(email) <= 254
            or "@" not in email
            or any(character in email for character in "\r\n\x00")
        ):
            return None
        arxiv_id = paper_match.group(1).lower()
        if not ARXIV_ID_RE.fullmatch(arxiv_id):
            return None
        try:
            submitted_at = datetime.fromisoformat(
                str(message.get("timestamp", "")).replace("Z", "+00:00")
            )
        except ValueError:
            return None
        if submitted_at.tzinfo is None:
            return None
        return {
            "reference": reference,
            "email": email,
            "arxiv_id": arxiv_id,
            "paper_url": f"https://arxiv.org/abs/{arxiv_id}",
            "submitted_at": submitted_at,
            "discord_message_id": message_id,
        }

    def run(self, *, max_messages: int = 1_000) -> tuple[int, int, int]:
        user = self._get_json(f"{DISCORD_API_ROOT}/users/@me")
        if not isinstance(user, dict) or not str(user.get("id", "")).isdigit():
            raise MailDeliveryError("Discord bot identity is invalid")
        bot_id = str(user["id"])
        endpoint = f"{DISCORD_API_ROOT}/channels/{self.channel_id}/messages"
        imported = existing = skipped = 0
        before: str | None = None
        inspected = 0
        while inspected < max_messages:
            params: dict[str, object] = {"limit": min(100, max_messages - inspected)}
            if before:
                params["before"] = before
            page = self._get_json(endpoint, **params)
            if not isinstance(page, list):
                raise MailDeliveryError("Discord message history is invalid")
            if not page:
                break
            inspected += len(page)
            for message in page:
                if not isinstance(message, dict):
                    skipped += 1
                    continue
                author = message.get("author")
                if not isinstance(author, dict) or str(author.get("id")) != bot_id:
                    skipped += 1
                    continue
                parsed = self._parse_embed(message)
                if parsed is None:
                    skipped += 1
                    continue
                created = self.store.import_delivered_nomination(**parsed)
                imported += int(created)
                existing += int(not created)
            before = str(page[-1].get("id", "")) if isinstance(page[-1], dict) else None
            if len(page) < int(params["limit"]) or not before:
                break
        return imported, existing, skipped


class MailWorker:
    """Join live publication state, SMTP outbox delivery, and IMAP replies."""

    def __init__(self, settings: MailSettings):
        self.settings = settings
        self.store = NominationStore(settings.database_path)
        self.smtp = SMTPDelivery(settings)
        relay = DiscordReplyRelay(
            channel_id=settings.discord_channel_id,
            bot_token=settings.discord_bot_token,
        )
        self.imap = IMAPReplyPoller(settings, store=self.store, relay=relay)

    def run_once(self) -> tuple[int, int, int]:
        now = datetime.now(timezone.utc)
        notices = load_publication_notices(self.settings.release_manifest)
        queued = self.store.queue_publication_notices(notices, now=now)
        sent = 0
        for _ in range(25):
            pending = self.store.lease_notification(now=time.time())
            if pending is None:
                break
            try:
                delivered_at = datetime.now(timezone.utc)
                self.smtp.send(pending, now=delivered_at)
                self.store.complete_notification(
                    pending.outbox_id,
                    sent_at=delivered_at,
                )
                sent += 1
                logger.info(
                    "Sent NULSPEC completion notice for %s (study %s).",
                    pending.reference,
                    pending.study_id,
                )
            except (
                MailDeliveryError,
                MailStoreError,
                OSError,
                sqlite3.Error,
            ) as exc:
                delay = min(3600, 60 * (2 ** min(6, pending.attempts - 1)))
                self.store.retry_notification(
                    pending.outbox_id,
                    next_attempt_at=time.time() + delay,
                    error=type(exc).__name__,
                )
                logger.warning(
                    "Completion notice for %s will retry in %s seconds.",
                    pending.reference,
                    delay,
                )
        replies = self.imap.poll_once()
        return queued, sent, replies

    def run_forever(self) -> None:
        recovered = self.store.recover_interrupted_notifications(now=time.time())
        if recovered:
            logger.warning(
                "Recovered %s interrupted mail delivery attempt(s).", recovered
            )
        while True:
            try:
                queued, sent, replies = self.run_once()
                if queued or sent or replies:
                    logger.info(
                        "NULSPEC mail cycle: queued=%s sent=%s replies=%s.",
                        queued,
                        sent,
                        replies,
                    )
            except (
                MailDeliveryError,
                MailStoreError,
                PublicationNoticeError,
                OSError,
                sqlite3.Error,
            ):
                logger.exception("NULSPEC mail cycle failed; it will retry.")
            time.sleep(self.settings.poll_seconds)


def _backfill_from_environment() -> tuple[int, int, int]:
    database = Path(os.environ.get("NULSPEC_MAIL_DB_PATH", str(DEFAULT_DATABASE)))
    channel_id = _environment_int(
        "NULSPEC_MAIL_CHANNEL_ID", DEFAULT_CHANNEL_ID, 1, (2**63) - 1
    )
    bot_token = _required_environment("BOB_BOT_TOKEN")
    store = NominationStore(database)
    return DiscordNominationBackfill(
        store=store,
        channel_id=channel_id,
        bot_token=bot_token,
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("worker", "check-config", "backfill-discord"),
        nargs="?",
        default="worker",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "backfill-discord":
            imported, existing, skipped = _backfill_from_environment()
            print(
                "NULSPEC_MAIL_BACKFILL_READY "
                f"imported={imported} existing={existing} skipped={skipped}"
            )
            return 0
        settings = MailSettings.from_environment()
        notices = load_publication_notices(settings.release_manifest)
        if args.command == "check-config":
            print(
                "NULSPEC_MAIL_CONFIG_READY "
                f"publications={len(notices)} mailbox={settings.mailbox}"
            )
            return 0
        MailWorker(settings).run_forever()
    except (
        MailConfigurationError,
        MailDeliveryError,
        MailStoreError,
        PublicationNoticeError,
        OSError,
        sqlite3.Error,
    ) as exc:
        logger.error("NULSPEC mail startup failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

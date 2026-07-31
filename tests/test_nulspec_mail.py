from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infra" / "multibot"))

import nulspec_mail  # noqa: E402
from nulspec_mail import (  # noqa: E402
    DiscordNominationBackfill,
    DiscordReplyRelay,
    IMAPReplyPoller,
    MailConfigurationError,
    MailSettings,
    PublicationNoticeError,
    build_completion_message,
    load_publication_notices,
    parse_incoming_message,
)
from nulspec_mail_store import NominationStore  # noqa: E402

from ops.nulspec_install_release import DeployError, validate_release  # noqa: E402
from scripts.build_release_manifest import build_manifest  # noqa: E402

NOW = datetime(2026, 7, 31, 12, 30, tzinfo=timezone.utc)


def result_notice() -> dict[str, object]:
    return {
        "study_id": "260725091",
        "study_title": "Independent reproduction of robust RL",
        "paper_title": "Towards Robust Reinforcement Learning",
        "arxiv_id": "2607.25091",
        "paper_url": "https://arxiv.org/abs/2607.25091",
        "classification": "PARTIALLY_REPRODUCED",
        "study_url": "https://nulspec.com/studies/260725091/",
        "full_report_url": (
            "https://nulspec.com/studies/260725091/artifacts/full-matrix-report.md"
        ),
        "headline": "Released numbers reproduced; stronger claims unconfirmed",
        "summary": "The numerical table was close, but the broad claim was not.",
        "key_findings": [
            "Most released deltas fell inside the conditional intervals.",
            "Training-to-training variance remains unresolved.",
        ],
    }


def add_delivered_nomination(store: NominationStore) -> str:
    reference = "NLS-20260731-ABC123"
    claim = store.claim_nomination(
        reference=reference,
        email="researcher@example.com",
        arxiv_id="2607.25091v2",
        paper_url="https://arxiv.org/abs/2607.25091v2",
        submitted_at=NOW,
    )
    assert claim.created is True
    store.mark_discord_delivered(reference, "1533000000000000001")
    return reference


def test_nomination_deduplication_survives_restart_and_arxiv_versions(
    tmp_path: Path,
) -> None:
    database = tmp_path / "mail.sqlite3"
    first_store = NominationStore(database)
    reference = add_delivered_nomination(first_store)
    first_store.close()

    second_store = NominationStore(database)
    duplicate = second_store.claim_nomination(
        reference="NLS-20260801-DEF456",
        email="RESEARCHER@example.com",
        arxiv_id="2607.25091v4",
        paper_url="https://arxiv.org/abs/2607.25091v4",
        submitted_at=NOW,
    )

    assert duplicate.created is False
    assert duplicate.reference == reference
    assert duplicate.discord_message_id == "1533000000000000001"
    assert database.stat().st_mode & 0o777 == 0o600


def test_outbox_matches_base_paper_and_redacts_contact_after_delivery(
    tmp_path: Path,
) -> None:
    database = tmp_path / "mail.sqlite3"
    store = NominationStore(database)
    reference = add_delivered_nomination(store)

    assert store.queue_publication_notices([result_notice()], now=NOW) == 1
    pending = store.lease_notification(now=0)
    assert pending is not None
    assert pending.reference == reference
    assert pending.contact_email == "researcher@example.com"
    assert pending.message_id == (
        "<completion.nls-20260731-abc123.260725091@nulspec.com>"
    )

    store.complete_notification(pending.outbox_id, sent_at=NOW)
    assert store.lease_notification(now=10_000) is None
    assert store.queue_publication_notices([result_notice()], now=NOW) == 0

    with sqlite3.connect(database) as connection:
        email, digest, notified_at = connection.execute(
            """
            SELECT contact_email, contact_sha256, notified_at
            FROM nominations WHERE reference = ?
            """,
            (reference,),
        ).fetchone()
    assert email is None
    assert len(digest) == 64
    assert notified_at.endswith("Z")


def test_completion_message_is_one_time_transactional_mail(tmp_path: Path) -> None:
    store = NominationStore(tmp_path / "mail.sqlite3")
    add_delivered_nomination(store)
    store.queue_publication_notices([result_notice()], now=NOW)
    pending = store.lease_notification(now=0)
    assert pending is not None

    message = build_completion_message(
        pending,
        mailbox="research@nulspec.com",
        now=NOW,
    )
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()

    assert message["Message-ID"] == pending.message_id
    assert message["Reply-To"] == "research@nulspec.com"
    assert message["X-NULSPEC-Reference"] == pending.reference
    assert message["Auto-Submitted"] == "auto-generated"
    assert "NULSPEC verdict: Partially Reproduced" in plain
    assert "does not use nomination addresses for marketing" in plain
    assert "https://nulspec.com/studies/260725091/" in plain
    assert "<ul>" in html
    assert "tracking" not in message.as_string().lower()


def test_release_manifest_notice_loader_is_strict(tmp_path: Path) -> None:
    notice = result_notice()
    manifest = {
        "schema_version": 1,
        "publications": [
            {
                "study_id": notice["study_id"],
                "study_title": notice["study_title"],
                "classification": notice["classification"],
                "paper": {
                    "title": notice["paper_title"],
                    "arxiv_id": notice["arxiv_id"],
                    "url": notice["paper_url"],
                },
                "result_notification": {
                    key: notice[key]
                    for key in (
                        "study_url",
                        "full_report_url",
                        "headline",
                        "summary",
                        "key_findings",
                    )
                },
            }
        ],
    }
    path = tmp_path / "release.json"
    path.write_text(json.dumps(manifest))

    assert load_publication_notices(path) == [notice]

    manifest["publications"][0]["result_notification"]["full_report_url"] = (
        "https://attacker.example/report"
    )
    path.write_text(json.dumps(manifest))
    with pytest.raises(PublicationNoticeError, match="report URL"):
        load_publication_notices(path)

    path.write_text("[]")
    with pytest.raises(PublicationNoticeError, match="contract"):
        load_publication_notices(path)


def test_mail_settings_pin_credentials_to_expected_hosts_and_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NULSPEC_MAIL_SMTP_PASSWORD", "smtp-secret")
    monkeypatch.setenv("NULSPEC_MAIL_IMAP_PASSWORD", "imap-secret")
    monkeypatch.setenv("BOB_BOT_TOKEN", "discord-secret")

    settings = MailSettings.from_environment()
    assert settings.smtp_host == "smtp.purelymail.com"
    assert settings.imap_host == "imap.purelymail.com"
    assert settings.discord_channel_id == 1532567350472343653

    monkeypatch.setenv("NULSPEC_MAIL_SMTP_HOST", "attacker.example")
    with pytest.raises(MailConfigurationError, match="SMTP host"):
        MailSettings.from_environment()


def test_static_release_manifest_contains_reviewed_result_notice(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text("home")
    publication_path = ROOT / "site-data/publications/study-260725091.json"
    publication = json.loads(publication_path.read_text())
    study_id = publication["study"]["id"]
    study_directory = tmp_path / "studies" / study_id
    study_directory.mkdir(parents=True)
    (study_directory / "index.html").write_text("study")
    for artifact in publication["artifacts"]:
        target = tmp_path / artifact["public_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact["role"])

    manifest = build_manifest(tmp_path, "a" * 40)
    record = manifest["publications"][0]
    result = record["result_notification"]

    assert result["headline"] == publication["verdict"]["headline"]
    assert result["summary"] == publication["verdict"]["summary"]
    assert result["key_findings"] == publication["verdict"]["key_findings"]
    assert result["study_url"] == ("https://nulspec.com/studies/260725091/")

    release_path = tmp_path / "release.json"
    release_path.write_text(json.dumps(manifest))
    assert validate_release(tmp_path)["git_commit"] == "a" * 40

    manifest["publications"][0]["result_notification"]["full_report_url"] = (
        "https://nulspec.com/studies/260725091/artifacts/../../private"
    )
    release_path.write_text(json.dumps(manifest))
    with pytest.raises(DeployError, match="invalid result notice"):
        validate_release(tmp_path)


class FakeResponse:
    status_code = 200

    def json(self) -> dict[str, str]:
        return {"id": "1533000000000000042"}


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse()


def test_researcher_reply_is_prettified_and_cannot_ping_discord(
    tmp_path: Path,
) -> None:
    store = NominationStore(tmp_path / "mail.sqlite3")
    reference = add_delivered_nomination(store)
    store.queue_publication_notices([result_notice()], now=NOW)
    pending = store.lease_notification(now=0)
    assert pending is not None

    reply = EmailMessage()
    reply["From"] = "Ada Researcher <ada@example.edu>"
    reply["To"] = "research@nulspec.com"
    reply["Subject"] = "Re: replication findings"
    reply["In-Reply-To"] = pending.message_id
    reply["Message-ID"] = "<reply-1@example.edu>"
    reply["Date"] = "Fri, 31 Jul 2026 13:00:00 +0000"
    reply.set_content("Thank you. @everyone This is useful.\n\nCould we discuss it?")
    reply.add_attachment(
        b"not downloaded by the relay",
        maintype="application",
        subtype="pdf",
        filename="notes.pdf",
    )

    parsed = parse_incoming_message(reply.as_bytes(), store=store, now=NOW)
    assert parsed.reference == reference
    assert parsed.sender == "Ada Researcher <ada@example.edu>"
    assert "@everyone" in parsed.body
    assert parsed.attachments == ("notes.pdf",)

    session = FakeSession()
    relay = DiscordReplyRelay(
        channel_id=1532567350472343653,
        bot_token="test-token",
        session=session,
    )
    message_id = relay.deliver(
        parsed,
        mailbox="research@nulspec.com",
        uidvalidity=42,
        uid=7,
    )

    assert message_id == "1533000000000000042"
    payload = session.calls[0]["json"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["enforce_nonce"] is True
    embed = payload["embeds"][0]
    assert embed["description"].startswith("```\nThank you.")
    assert reference in json.dumps(embed)
    assert "notes" in json.dumps(embed)


def test_reference_can_be_found_inside_an_unthreaded_subject(tmp_path: Path) -> None:
    store = NominationStore(tmp_path / "mail.sqlite3")
    reply = EmailMessage()
    reply["From"] = "person@example.org"
    reply["Subject"] = "Question about NLS-20260731-ABC123 please"
    reply.set_content("Hello")

    parsed = parse_incoming_message(reply.as_bytes(), store=store, now=NOW)
    assert parsed.reference == "NLS-20260731-ABC123"


def test_historical_embed_parser_accepts_only_generated_shape() -> None:
    message = {
        "id": "1533000000000000001",
        "timestamp": "2026-07-31T12:30:00Z",
        "embeds": [
            {
                "title": "New replication nomination",
                "fields": [
                    {
                        "name": "Paper",
                        "value": (
                            "[arXiv:2607.25091](https://arxiv.org/abs/2607.25091)"
                        ),
                    },
                    {"name": "Contact email", "value": "researcher@example.com"},
                    {"name": "Reference", "value": "NLS-20260731-ABC123"},
                ],
            }
        ],
    }

    parsed = DiscordNominationBackfill._parse_embed(message)
    assert parsed is not None
    assert parsed["arxiv_id"] == "2607.25091"

    message["embeds"][0]["title"] = "Untrusted message"
    assert DiscordNominationBackfill._parse_embed(message) is None


def test_mailbox_cursor_skips_existing_mail_then_advances(tmp_path: Path) -> None:
    store = NominationStore(tmp_path / "mail.sqlite3")
    cursor, initialized = store.mailbox_cursor(
        mailbox="research@nulspec.com",
        uidvalidity=99,
        initial_high_water_uid=12,
        now=NOW,
    )
    assert (cursor, initialized) == (12, True)

    store.begin_inbound(
        mailbox="research@nulspec.com",
        uidvalidity=99,
        uid=13,
        message_id="<reply@example.org>",
        received_at=NOW,
    )
    store.complete_inbound(
        mailbox="research@nulspec.com",
        uidvalidity=99,
        uid=13,
        discord_message_id="1533000000000000002",
        now=NOW,
    )
    cursor, initialized = store.mailbox_cursor(
        mailbox="research@nulspec.com",
        uidvalidity=99,
        initial_high_water_uid=99,
        now=NOW,
    )
    assert (cursor, initialized) == (13, False)


class FakeIMAPServer:
    messages: ClassVar[dict[int, bytes]] = {}
    uidvalidity = 77

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def login(self, username: str, password: str) -> tuple[str, list[bytes]]:
        assert username == "research@nulspec.com"
        assert password == "imap-secret"
        return "OK", [b"logged in"]

    def select(self, mailbox: str, readonly: bool) -> tuple[str, list[bytes]]:
        assert mailbox == "INBOX"
        assert readonly is True
        return "OK", [str(len(self.messages)).encode()]

    def response(self, name: str) -> tuple[str, list[bytes]]:
        if name == "UIDVALIDITY":
            return name, [str(self.uidvalidity).encode()]
        if name == "UIDNEXT":
            next_uid = max(self.messages, default=6) + 1
            return name, [str(next_uid).encode()]
        raise AssertionError(name)

    def uid(self, command: str, *args: object) -> tuple[str, list[object]]:
        if command == "search":
            start = int(str(args[-1]).partition(":")[0])
            matches = b" ".join(
                str(uid).encode() for uid in sorted(self.messages) if uid >= start
            )
            return "OK", [matches]
        if command == "fetch":
            uid = int(str(args[0]))
            raw = self.messages[uid]
            return "OK", [(b"BODY[]", raw), b")"]
        raise AssertionError(command)

    def logout(self) -> tuple[str, list[bytes]]:
        return "BYE", [b"logged out"]


class FakeReplyRelay:
    def __init__(self) -> None:
        self.messages = []

    def deliver(self, message, **kwargs: object) -> str:
        self.messages.append((message, kwargs))
        return "1533000000000000099"


def test_imap_poller_skips_old_mail_then_relays_new_uid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeIMAPServer.messages = {7: b"existing provider welcome message"}
    monkeypatch.setattr(nulspec_mail.imaplib, "IMAP4_SSL", FakeIMAPServer)
    settings = MailSettings(
        database_path=tmp_path / "mail.sqlite3",
        release_manifest=tmp_path / "release.json",
        mailbox="research@nulspec.com",
        smtp_host="smtp.purelymail.com",
        smtp_port=465,
        smtp_username="research@nulspec.com",
        smtp_password="smtp-secret",
        imap_host="imap.purelymail.com",
        imap_port=993,
        imap_username="research@nulspec.com",
        imap_password="imap-secret",
        discord_channel_id=1532567350472343653,
        discord_bot_token="test-token",
        poll_seconds=60,
    )
    store = NominationStore(settings.database_path)
    relay = FakeReplyRelay()
    poller = IMAPReplyPoller(settings, store=store, relay=relay, now=lambda: NOW)

    assert poller.poll_once() == 0
    assert relay.messages == []

    reply = EmailMessage()
    reply["From"] = "researcher@example.org"
    reply["Subject"] = "A new response"
    reply.set_content("This arrived after cursor initialization.")
    FakeIMAPServer.messages[8] = reply.as_bytes()

    assert poller.poll_once() == 1
    assert relay.messages[0][0].subject == "A new response"
    assert relay.messages[0][1]["uid"] == 8
    assert poller.poll_once() == 0

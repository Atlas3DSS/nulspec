from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infra" / "multibot"))

from nulspec_nominations import (  # noqa: E402
    DEFAULT_ALLOWED_ORIGINS,
    NominationRelay,
    NominationValidationError,
    RateLimitExceeded,
    SubmissionResult,
    normalize_arxiv_url,
    normalize_email,
    register_nulspec_nomination_routes,
    validate_nomination,
)


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {"id": "discord-message-1"}

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls: list[dict] = []

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse()


class FakeRelay:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

    def __init__(self):
        self.submissions = []

    def submit(self, nomination, *, client_ip: str) -> SubmissionResult:
        self.submissions.append((nomination, client_ip))
        return SubmissionResult(reference="NLS-20260731-ABC123", duplicate=False)


def test_email_normalization_is_conservative() -> None:
    assert normalize_email(" Researcher@Example.COM ") == "researcher@example.com"

    for invalid in (
        "missing-at.example.com",
        ".leading@example.com",
        "double..dot@example.com",
        "person@localhost",
        "☃@example.com",
    ):
        with pytest.raises(NominationValidationError):
            normalize_email(invalid)


def test_arxiv_links_are_canonicalized() -> None:
    assert normalize_arxiv_url("https://arxiv.org/abs/2607.25091v2") == (
        "2607.25091v2",
        "https://arxiv.org/abs/2607.25091v2",
    )
    assert normalize_arxiv_url("https://www.arxiv.org/pdf/hep-th/9901001.pdf") == (
        "hep-th/9901001",
        "https://arxiv.org/abs/hep-th/9901001",
    )


@pytest.mark.parametrize(
    "url",
    (
        "http://arxiv.org/abs/2607.25091",
        "https://example.com/abs/2607.25091",
        "https://arxiv.org/search/?query=agents",
        "https://arxiv.org/abs/not-an-id",
        "https://arxiv.org/abs/2607.25091?download=1",
        "https://arxiv.org/abs/2607.25091#page=2",
    ),
)
def test_noncanonical_or_non_arxiv_links_are_rejected(url: str) -> None:
    with pytest.raises(NominationValidationError):
        normalize_arxiv_url(url)


def test_relay_posts_one_safe_embed_and_deduplicates() -> None:
    session = FakeSession()
    clock_value = [100.0]
    relay = NominationRelay(
        channel_id=1532567350472343653,
        bot_token="test-token",
        session=session,
        clock=lambda: clock_value[0],
        now=lambda: datetime(2026, 7, 31, 2, 30, tzinfo=timezone.utc),
    )
    nomination = validate_nomination(
        "researcher@example.com",
        "https://arxiv.org/abs/2607.25091",
    )

    first = relay.submit(nomination, client_ip="203.0.113.10")
    second = relay.submit(nomination, client_ip="203.0.113.10")

    assert first.duplicate is False
    assert second == SubmissionResult(reference=first.reference, duplicate=True)
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"].endswith("/channels/1532567350472343653/messages")
    assert call["json"]["allowed_mentions"] == {"parse": []}
    embed = call["json"]["embeds"][0]
    assert embed["url"] == "https://arxiv.org/abs/2607.25091"
    assert embed["fields"][1]["value"] == "researcher@example.com"


def test_relay_limits_fourth_submission_from_one_ip() -> None:
    session = FakeSession()
    relay = NominationRelay(
        channel_id=1532567350472343653,
        bot_token="test-token",
        session=session,
        clock=lambda: 100.0,
        now=lambda: datetime(2026, 7, 31, 2, 30, tzinfo=timezone.utc),
    )

    for suffix in range(3):
        relay.submit(
            validate_nomination(
                f"researcher{suffix}@example.com",
                f"https://arxiv.org/abs/2607.2509{suffix}",
            ),
            client_ip="203.0.113.20",
        )

    with pytest.raises(RateLimitExceeded):
        relay.submit(
            validate_nomination(
                "researcher3@example.com",
                "https://arxiv.org/abs/2607.25093",
            ),
            client_ip="203.0.113.20",
        )


def test_flask_route_accepts_only_the_two_fields_and_honeypot() -> None:
    relay = FakeRelay()
    app = Flask(__name__)
    register_nulspec_nomination_routes(app, relay=relay)
    client = app.test_client()
    headers = {
        "Origin": "https://nulspec.com",
        "X-Nulspec-Client-IP": "203.0.113.30",
    }

    response = client.post(
        "/api/nominations",
        json={
            "email": "researcher@example.com",
            "paper": "https://arxiv.org/abs/2607.25091",
            "company": "",
        },
        headers=headers,
    )

    assert response.status_code == 202
    assert response.get_json() == {
        "duplicate": False,
        "ok": True,
        "reference": "NLS-20260731-ABC123",
    }
    assert relay.submissions[0][1] == "203.0.113.30"

    trapped = client.post(
        "/api/nominations",
        json={
            "email": "bot@example.com",
            "paper": "https://arxiv.org/abs/2607.25091",
            "company": "filled by bot",
        },
        headers=headers,
    )
    assert trapped.status_code == 202
    assert len(relay.submissions) == 1


def test_flask_route_enforces_origin_shape_and_preflight() -> None:
    relay = FakeRelay()
    app = Flask(__name__)
    register_nulspec_nomination_routes(app, relay=relay)
    client = app.test_client()

    forbidden = client.post(
        "/api/nominations",
        json={
            "email": "researcher@example.com",
            "paper": "https://arxiv.org/abs/2607.25091",
        },
        headers={"Origin": "https://attacker.example"},
    )
    assert forbidden.status_code == 403

    invalid = client.post(
        "/api/nominations",
        json={
            "email": "researcher@example.com",
            "paper": "https://example.com/paper",
            "extra": "not allowed",
        },
        headers={"Origin": "https://nulspec.com"},
    )
    assert invalid.status_code == 400

    preflight = client.options(
        "/api/nominations",
        headers={"Origin": "https://nulspec.com"},
    )
    assert preflight.status_code == 204
    assert preflight.headers["Access-Control-Allow-Origin"] == "https://nulspec.com"
    assert preflight.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"

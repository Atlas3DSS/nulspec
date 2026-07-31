from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infra" / "multibot"))

from nulspec_nominations import (  # noqa: E402
    DEFAULT_ALLOWED_ORIGINS,
    ExtensionVoteRelay,
    ExtensionVoteValidationError,
    NominationRelay,
    NominationValidationError,
    RateLimitExceeded,
    ReleaseManifestRegistry,
    SubmissionResult,
    normalize_arxiv_url,
    normalize_email,
    register_nulspec_extension_vote_routes,
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


class FakeExtensionRelay:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

    def __init__(self):
        self.submissions = []

    def submit(self, study_id, option_id, *, client_ip: str) -> SubmissionResult:
        self.submissions.append((study_id, option_id, client_ip))
        return SubmissionResult(reference="NLE-20260731-DEF456", duplicate=False)


def write_release_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "publications": [
                    {
                        "study_id": "260725091",
                        "study_title": "Independent reproduction of robust RL",
                        "paper": {
                            "title": "Towards Robust Reinforcement Learning",
                            "arxiv_id": "2607.25091",
                            "url": "https://arxiv.org/abs/2607.25091",
                        },
                        "extension_vote": {
                            "requested": True,
                            "selection_mode": "single_choice",
                            "options": [
                                {
                                    "id": "targeted-variance-map",
                                    "label": "Measure run-to-run variance",
                                    "role": "ROBUSTNESS_REPLICATION",
                                    "priority": 1,
                                    "summary": "Repeat selected arms across fresh seeds.",
                                },
                                {
                                    "id": "clean-room-audit",
                                    "label": "Run a clean-room reproduction",
                                    "role": "REPRODUCIBILITY_STRENGTHENING",
                                    "priority": 2,
                                    "summary": "Use only the tagged public materials.",
                                },
                            ],
                        },
                    }
                ],
            }
        )
    )
    return path


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


def test_extension_registry_resolves_only_current_published_options(
    tmp_path: Path,
) -> None:
    registry = ReleaseManifestRegistry(write_release_manifest(tmp_path / "release.json"))
    vote = registry.lookup("260725091", "targeted-variance-map")

    assert vote.paper_url == "https://arxiv.org/abs/2607.25091"
    assert vote.option_label == "Measure run-to-run variance"
    with pytest.raises(ExtensionVoteValidationError):
        registry.lookup("260725091", "not-published")
    with pytest.raises(ExtensionVoteValidationError):
        registry.lookup("../private", "targeted-variance-map")


def test_extension_vote_posts_safe_embed_and_deduplicates_by_network(
    tmp_path: Path,
) -> None:
    session = FakeSession()
    relay = ExtensionVoteRelay(
        channel_id=1532567350472343653,
        bot_token="test-token",
        registry=ReleaseManifestRegistry(write_release_manifest(tmp_path / "release.json")),
        session=session,
        clock=lambda: 100.0,
        now=lambda: datetime(2026, 7, 31, 2, 30, tzinfo=timezone.utc),
    )

    first = relay.submit(
        "260725091", "targeted-variance-map", client_ip="203.0.113.40"
    )
    second = relay.submit(
        "260725091", "clean-room-audit", client_ip="203.0.113.40"
    )

    assert first.duplicate is False
    assert second == SubmissionResult(reference=first.reference, duplicate=True)
    assert len(session.calls) == 1
    embed = session.calls[0]["json"]["embeds"][0]
    assert embed["title"] == "Vote to extend NULSPEC Study 260725091"
    assert "Measure run-to-run variance" in embed["fields"][1]["value"]
    assert "203.0.113.40" not in json.dumps(session.calls[0]["json"])
    assert session.calls[0]["json"]["allowed_mentions"] == {"parse": []}


def test_extension_vote_route_is_strict_and_cors_bound() -> None:
    relay = FakeExtensionRelay()
    app = Flask(__name__)
    register_nulspec_extension_vote_routes(app, relay=relay)
    client = app.test_client()
    headers = {
        "Origin": "https://nulspec.com",
        "X-Nulspec-Client-IP": "203.0.113.50",
    }

    response = client.post(
        "/api/extension-votes",
        json={
            "study_id": "260725091",
            "option_id": "targeted-variance-map",
            "company": "",
        },
        headers=headers,
    )
    assert response.status_code == 202
    assert response.get_json() == {
        "duplicate": False,
        "ok": True,
        "reference": "NLE-20260731-DEF456",
    }
    assert relay.submissions == [
        ("260725091", "targeted-variance-map", "203.0.113.50")
    ]

    unexpected = client.post(
        "/api/extension-votes",
        json={"study_id": "260725091", "option_id": "x", "email": "nope"},
        headers=headers,
    )
    assert unexpected.status_code == 400
    forbidden = client.post(
        "/api/extension-votes",
        json={"study_id": "260725091", "option_id": "targeted-variance-map"},
        headers={"Origin": "https://attacker.example"},
    )
    assert forbidden.status_code == 403
    preflight = client.options(
        "/api/extension-votes", headers={"Origin": "https://nulspec.com"}
    )
    assert preflight.status_code == 204
    assert preflight.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"

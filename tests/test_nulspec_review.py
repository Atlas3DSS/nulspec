from __future__ import annotations

import base64
from argparse import Namespace
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infra" / "multibot"))

from nulspec_review import (  # noqa: E402
    ACCOUNTS_SCHEMA,
    DisabledReviewService,
    RELEASE_REVIEW_SCHEMA,
    ReviewConfigurationError,
    ReviewService,
    accounts_from_environment,
    build_study_task,
    decode_accounts,
    encode_accounts,
    register_nulspec_review_routes,
)
from nulspec_review_store import (  # noqa: E402
    EMAIL_APPROVAL_SCHEMA,
    LEGACY_TASK_SCHEMA,
    PUBLICATION_DISPOSITION_SCHEMA,
    TASK_SCHEMA,
    ReviewPacketError,
    ReviewerAccount,
    ReviewStore,
    ReviewStoreError,
    sha256_json,
    sha256_text,
    validate_task_packet,
)


NOW = datetime(2026, 8, 1, 19, 30, tzinfo=timezone.utc)
PASSWORD = "correct horse battery staple"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="scrypt:16384:8:1")
ORIGIN = "http://127.0.0.1:4321"
CLIENT_HEADERS = {
    "Origin": ORIGIN,
    "X-Nulspec-Client-IP": "203.0.113.41",
}


class Clock:
    def __init__(self, value: datetime = NOW):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def reviewer_account() -> ReviewerAccount:
    return ReviewerAccount(
        username="reviewer.one",
        display_name="Reviewer One",
        password_hash=PASSWORD_HASH,
        roles=("reviewer",),
    )


def task_packet(
    *, task_id: str = "study-260723346-r1", recipients: bool = True
) -> dict:
    email_body = (
        "# Draft author email — not sent\n\n"
        "**Subject:** Independent replication attempt\n\n"
        "Hello authors,\n\nThis exact draft requires human approval.\n"
    )
    return {
        "schema_version": TASK_SCHEMA,
        "task_id": task_id,
        "supersedes_task_id": None,
        "priority": "high",
        "queued_reason": (
            "The independent GLM and Kimi release reviews require a human "
            "publication disposition."
        ),
        "submitted_at_utc": "2026-08-01T18:16:18Z",
        "study": {
            "study_id": "260723346",
            "paper_title": "A computational research paper",
            "paper_url": "https://arxiv.org/abs/2607.23346v1",
            "arxiv_id": "2607.23346v1",
            "replication_assessment": "Not replicated",
            "method_assessment": "Inconclusive",
        },
        "source": {
            "source_revision": "a" * 40,
            "repository_url": "https://github.com/example/research",
            "pull_request_url": "https://github.com/example/research/pull/18",
            "review_packet_sha256": "b" * 64,
            "release_review_consensus_sha256": "c" * 64,
        },
        "brief": (
            "The frozen final-result recipe did not reproduce the reported "
            "result. The underlying method remains unresolved."
        ),
        "evidence": [
            {
                "id": "one-page",
                "label": "One-page result",
                "kind": "brief",
                "url": "https://github.com/example/research/blob/"
                + "a" * 40
                + "/ONE_PAGE.md",
                "sha256": "e" * 64,
                "summary": "Decision-oriented result summary.",
            }
        ],
        "review_events": [
            {
                "event_id": "RELEASE-GLM-20260802-001",
                "reviewer": "GLM",
                "provider": "OpenRouter",
                "model": "z-ai/glm-versioned",
                "outcome": "PASS",
                "validation": "completed_valid",
                "summary": "The release review completed with a valid PASS.",
                "cost_usd": 0.157606,
                "trace_sha256": "f" * 64,
                "consensus_eligible": False,
            }
        ],
        "publication_gate": {
            "reason": "The model gate passed and human publication review remains required.",
            "question": "Should this exact release proceed or remain blocked?",
        },
        "author_email_gate": {
            "subject": "Independent replication attempt",
            "body": email_body,
            "draft_sha256": sha256_text(email_body),
            "recipients": (
                [{"name": "Paper authors", "email": "authors@example.org"}]
                if recipients
                else []
            ),
        },
    }


def write_generic_release_study(root: Path, *, ledger_reviewer: str = "GLM") -> None:
    (root / "results").mkdir(parents=True)
    handoff = {
        "study": {
            "id": "260723346",
            "title": "A computational research paper",
            "arxiv_url": "https://arxiv.org/abs/2607.23346v1",
            "arxiv_id": "2607.23346v1",
        },
        "classification": {
            "replication_outcome": "not_replicated",
            "underlying_method_claim": "inconclusive",
        },
    }
    (root / "WEBSITE_HANDOFF.json").write_text(json.dumps(handoff))
    for name in ("ONE_PAGE.md", "REPORT.md", "PROTOCOL.md", "TESTS.md"):
        (root / name).write_text(f"# {name}\n\nBound release evidence.\n")
    (root / "FINAL_REVIEW.md").write_text(
        "# GLM/Kimi release review\n\nBoth independent reviews passed.\n"
    )
    (root / "AUTHOR_EMAIL.md").write_text(
        "# Draft author email — not sent\n\n"
        "**Subject:** Independent replication attempt\n\n"
        "Hello authors,\n\nThis exact draft requires human approval.\n"
    )
    (root / "EXTERNAL_REVIEW_LEDGER.md").write_text(
        "# External review ledger\n\nImmutable GLM/Kimi attempts.\n"
    )
    release_review = {
        "schema_version": RELEASE_REVIEW_SCHEMA,
        "fable_invoked": False,
        "publication_authorized": False,
        "human_publication_approval_required": True,
        "author_email_human_approval_required": True,
        "review_packet": {"sha256": "a" * 64},
        "decision_reason": "GLM and Kimi returned valid PASS reviews.",
        "completed_at_utc": "2026-08-02T20:00:00Z",
        "model_review_gate": "passed",
        "reviewers": [
            {
                "reviewer_family": "GLM",
                "status": "completed_valid",
                "verdict": "PASS",
            },
            {
                "reviewer_family": "Kimi",
                "status": "completed_valid",
                "verdict": "PASS",
            },
        ],
    }
    (root / "results" / "release_review_consensus.json").write_text(
        json.dumps(release_review)
    )
    ledger = {
        "events": [
            {
                "event_id": "RELEASE-REVIEW-001",
                "reviewer_family": ledger_reviewer,
                "provider": "OpenRouter",
                "canonical_model": "versioned-review-model",
                "declared_verdict": "PASS",
                "validation_status": "completed_valid",
                "charged_cost_usd": 0.1,
                "consensus_eligible": True,
                "trace": {"artifacts": {"raw_response": {"sha256": "b" * 64}}},
            }
        ]
    }
    (root / "results" / "external_review_ledger.json").write_text(json.dumps(ledger))


def build_task_args(study_root: Path) -> Namespace:
    return Namespace(
        study_root=study_root,
        task_id="260723346-release-r3",
        supersedes_task_id=None,
        priority="high",
        source_revision="c" * 40,
        repository_url="https://github.com/example/research",
        pull_request_url="https://github.com/example/research/pull/30",
        study_repo_path="research/replications/2607.23346",
        recipients=None,
    )


def make_service(
    store: ReviewStore,
    *,
    clock: Clock | None = None,
    login_ip_limit: int = 8,
) -> ReviewService:
    account = reviewer_account()
    return ReviewService(
        store=store,
        accounts={account.username: account},
        pepper=b"p" * 32,
        allowed_origins=frozenset({ORIGIN}),
        secure_cookie=False,
        now=clock or Clock(),
        login_ip_limit=login_ip_limit,
        login_subject_limit=20,
    )


def make_client(
    tmp_path: Path,
    *,
    packet: dict | None = None,
    login_ip_limit: int = 8,
) -> tuple:
    store = ReviewStore(tmp_path / "review.sqlite3")
    if packet is not None:
        store.import_task(packet, now=NOW)
    service = make_service(store, login_ip_limit=login_ip_limit)
    app = Flask(__name__)
    app.testing = True
    register_nulspec_review_routes(app, service=service)
    return app.test_client(), service, store


def login(client) -> str:
    response = client.post(
        "/api/review/login",
        json={"username": "reviewer.one", "password": PASSWORD},
        headers=CLIENT_HEADERS,
    )
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_account_envelope_round_trips_and_rejects_plain_passwords() -> None:
    raw = {
        "schema_version": ACCOUNTS_SCHEMA,
        "accounts": [
            {
                "username": "reviewer.one",
                "display_name": "Reviewer One",
                "password_hash": PASSWORD_HASH,
                "roles": ["reviewer"],
            }
        ],
    }
    encoded = encode_accounts(raw)
    accounts = decode_accounts(encoded)
    assert accounts["reviewer.one"].display_name == "Reviewer One"

    raw["accounts"][0]["password_hash"] = PASSWORD
    unsafe = base64.urlsafe_b64encode(json.dumps(raw).encode()).decode().rstrip("=")
    with pytest.raises(ReviewConfigurationError, match="scrypt"):
        decode_accounts(unsafe)


def test_primary_reviewer_environment_provisions_monkey() -> None:
    accounts = accounts_from_environment(
        {
            "NULSPEC_REVIEW_PRIMARY_USERNAME": "monkey",
            "NULSPEC_REVIEW_PRIMARY_DISPLAY_NAME": "monkey",
            "NULSPEC_REVIEW_PRIMARY_PASSWORD_HASH": PASSWORD_HASH,
        }
    )

    assert list(accounts) == ["monkey"]
    assert accounts["monkey"].display_name == "monkey"
    assert accounts["monkey"].password_hash == PASSWORD_HASH


def test_primary_reviewer_environment_fails_closed_until_password_hash_is_set() -> None:
    with pytest.raises(ReviewConfigurationError, match="password hash is empty"):
        accounts_from_environment(
            {
                "NULSPEC_REVIEW_PRIMARY_USERNAME": "monkey",
                "NULSPEC_REVIEW_PRIMARY_DISPLAY_NAME": "monkey",
                "NULSPEC_REVIEW_PRIMARY_PASSWORD_HASH": "",
            }
        )


def test_primary_reviewer_and_account_envelope_are_mutually_exclusive() -> None:
    raw = {
        "schema_version": ACCOUNTS_SCHEMA,
        "accounts": [
            {
                "username": "reviewer.one",
                "display_name": "Reviewer One",
                "password_hash": PASSWORD_HASH,
                "roles": ["reviewer"],
            }
        ],
    }
    with pytest.raises(ReviewConfigurationError, match="not both"):
        accounts_from_environment(
            {
                "NULSPEC_REVIEW_ACCOUNTS_B64": encode_accounts(raw),
                "NULSPEC_REVIEW_PRIMARY_USERNAME": "monkey",
            }
        )


def test_account_hash_parameters_and_origins_are_configuration_wide() -> None:
    raw = {
        "schema_version": ACCOUNTS_SCHEMA,
        "accounts": [
            {
                "username": "reviewer.one",
                "display_name": "Reviewer One",
                "password_hash": PASSWORD_HASH,
                "roles": ["reviewer"],
            },
            {
                "username": "reviewer.two",
                "display_name": "Reviewer Two",
                "password_hash": generate_password_hash(
                    PASSWORD, method="scrypt:32768:8:1"
                ),
                "roles": ["reviewer"],
            },
        ],
    }
    encoded = base64.urlsafe_b64encode(json.dumps(raw).encode()).decode().rstrip("=")
    with pytest.raises(ReviewConfigurationError, match="identical scrypt"):
        decode_accounts(encoded)

    account = reviewer_account()
    store = ReviewStore(":memory:")
    try:
        with pytest.raises(ReviewConfigurationError, match="HTTPS origins"):
            ReviewService(
                store=store,
                accounts={account.username: account},
                pepper=b"p" * 32,
                allowed_origins=frozenset({ORIGIN}),
                secure_cookie=True,
            )
    finally:
        store.close()


def test_packet_validation_binds_exact_email_and_rejects_unsafe_links() -> None:
    packet = task_packet()
    assert validate_task_packet(packet)["task_id"] == "study-260723346-r1"

    changed = json.loads(json.dumps(packet))
    changed["author_email_gate"]["body"] += "changed"
    with pytest.raises(ReviewPacketError, match="draft digest"):
        validate_task_packet(changed)

    unsafe = json.loads(json.dumps(packet))
    unsafe["evidence"][0]["url"] = "javascript:alert(1)"
    with pytest.raises(ReviewPacketError, match="HTTPS"):
        validate_task_packet(unsafe)


def test_legacy_fable_task_remains_readable_but_new_schema_has_no_fable_binding() -> (
    None
):
    current = task_packet()
    assert "fable_action_closure_sha256" not in current["source"]

    legacy = task_packet(task_id="study-260723346-legacy")
    legacy["schema_version"] = LEGACY_TASK_SCHEMA
    legacy["source"] = {
        "source_revision": "a" * 40,
        "repository_url": "https://github.com/example/research",
        "pull_request_url": "https://github.com/example/research/pull/18",
        "review_packet_sha256": "b" * 64,
        "final_peer_review_sha256": "c" * 64,
        "supplemental_review_consensus_sha256": "d" * 64,
        "fable_action_closure_sha256": None,
    }
    assert validate_task_packet(legacy)["schema_version"] == LEGACY_TASK_SCHEMA


def test_study_adapter_builds_generic_glm_kimi_task(tmp_path: Path) -> None:
    write_generic_release_study(tmp_path)

    packet = build_study_task(build_task_args(tmp_path))

    assert packet["schema_version"] == TASK_SCHEMA
    assert packet["source"]["release_review_consensus_sha256"]
    assert "fable_action_closure_sha256" not in packet["source"]
    assert {event["reviewer"] for event in packet["review_events"]} == {"GLM"}
    assert any(item["id"] == "release-review" for item in packet["evidence"])


def test_study_adapter_rejects_per_paper_fable_event(tmp_path: Path) -> None:
    write_generic_release_study(tmp_path, ledger_reviewer="Fable")

    with pytest.raises(ReviewPacketError, match="prohibited Fable event"):
        build_study_task(build_task_args(tmp_path))


def test_task_import_is_idempotent_but_never_rebinds_an_id(tmp_path: Path) -> None:
    database = tmp_path / "review.sqlite3"
    store = ReviewStore(database)
    packet = task_packet()
    assert store.import_task(packet, now=NOW) is True
    assert store.import_task(packet, now=NOW) is False
    changed = json.loads(json.dumps(packet))
    changed["brief"] += " Material change."
    with pytest.raises(ReviewStoreError, match="different immutable packet"):
        store.import_task(changed, now=NOW)
    store.close()

    reopened = ReviewStore(database)
    assert reopened.get_task(packet["task_id"])["packet_sha256"] == sha256_json(packet)
    reopened.close()


def test_revised_packet_explicitly_supersedes_and_disables_old_task(
    tmp_path: Path,
) -> None:
    store = ReviewStore(tmp_path / "review.sqlite3")
    original = task_packet()
    assert store.import_task(original, now=NOW) is True

    revision = task_packet(task_id="study-260723346-r2")
    revision["brief"] += " The private packet now binds a corrected email draft."
    with pytest.raises(ReviewStoreError, match="supersession must be explicit"):
        store.import_task(revision, now=NOW)

    revision["supersedes_task_id"] = original["task_id"]
    assert store.import_task(revision, now=NOW) is True
    old_task = store.get_task(original["task_id"])
    assert old_task is not None
    assert old_task["superseded_by"] == revision["task_id"]

    service = make_service(store)
    old_view = service.task_view(old_task)
    assert old_view["complete"] is True
    assert old_view["publication_gate"]["action_allowed"] is False
    assert old_view["author_email_gate"]["action_allowed"] is False
    with pytest.raises(ReviewStoreError, match="superseded"):
        store.record_decision(
            decision_id="NHR-20260801-00000001",
            task_id=original["task_id"],
            gate="publication",
            decision="KEEP_BLOCKED",
            reviewer_username="reviewer.one",
            reviewer_display_name="Reviewer One",
            notes="This stale task must never accept a disposition.",
            binding_sha256=sha256_json(original),
            record={"test": True},
            now=NOW,
            client_digest="a" * 64,
        )
    assert service.inbox()["summary"] == {
        "completed_tasks": 1,
        "emails_blocked": 1,
        "emails_waiting": 0,
        "papers_waiting": 1,
        "total_tasks": 2,
    }
    store.close()


def test_store_migrates_pre_supersession_database_in_place(tmp_path: Path) -> None:
    database = tmp_path / "legacy-review.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE review_tasks (
            task_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            priority TEXT NOT NULL,
            packet_sha256 TEXT NOT NULL UNIQUE,
            packet_json TEXT NOT NULL,
            imported_at TEXT NOT NULL
        )
        """
    )
    connection.execute("PRAGMA user_version = 1")
    connection.close()

    store = ReviewStore(database)
    columns = {
        row["name"]
        for row in store._connection.execute(  # noqa: SLF001 - migration assertion
            "PRAGMA table_info(review_tasks)"
        ).fetchall()
    }
    version = store._connection.execute(  # noqa: SLF001 - migration assertion
        "PRAGMA user_version"
    ).fetchone()[0]
    assert "supersedes_task_id" in columns
    assert version == 2
    assert store.import_task(task_packet(), now=NOW) is True
    store.close()


def test_login_is_generic_secure_and_has_no_account_creation_surface(
    tmp_path: Path,
) -> None:
    client, _, store = make_client(tmp_path)
    unknown = client.post(
        "/api/review/login",
        json={"username": "missing.user", "password": "wrong password value"},
        headers=CLIENT_HEADERS,
    )
    wrong = client.post(
        "/api/review/login",
        json={"username": "reviewer.one", "password": "wrong password value"},
        headers=CLIENT_HEADERS,
    )
    assert unknown.status_code == wrong.status_code == 401
    assert (
        unknown.get_json()
        == wrong.get_json()
        == {
            "error": "invalid_credentials",
            "ok": False,
        }
    )

    response = client.post(
        "/api/review/login",
        json={"username": "reviewer.one", "password": PASSWORD},
        headers=CLIENT_HEADERS,
    )
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie
    assert "Path=/" in cookie
    assert "Cache-Control" in response.headers
    assert response.headers["Cache-Control"].startswith("no-store")

    session = client.get("/api/review/session")
    assert session.status_code == 200
    assert session.get_json()["reviewer"]["display_name"] == "Reviewer One"
    for path in ("signup", "register", "invite", "reset-password"):
        assert client.post(f"/api/review/{path}").status_code == 404
    store.close()


def test_production_cookie_is_host_only_secure_and_session_token_is_not_stored(
    tmp_path: Path,
) -> None:
    database = tmp_path / "review.sqlite3"
    store = ReviewStore(database)
    account = reviewer_account()
    service = ReviewService(
        store=store,
        accounts={account.username: account},
        pepper=b"s" * 32,
        allowed_origins=frozenset({"https://nulspec.com"}),
        secure_cookie=True,
        now=Clock(),
    )
    app = Flask(__name__)
    app.testing = True
    register_nulspec_review_routes(app, service=service)
    response = app.test_client().post(
        "/api/review/login",
        json={"username": "reviewer.one", "password": PASSWORD},
        headers={
            "Origin": "https://nulspec.com",
            "X-Nulspec-Client-IP": "203.0.113.42",
        },
    )
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert cookie.startswith("__Host-nulspec-review-session=")
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie
    assert "Path=/" in cookie
    assert "Domain=" not in cookie
    token = cookie.split("=", 1)[1].split(";", 1)[0]
    stored = store._connection.execute(  # noqa: SLF001 - storage assertion
        "SELECT token_sha256 FROM review_sessions"
    ).fetchone()["token_sha256"]
    assert token not in stored
    assert stored == sha256_text(token)
    store.close()


def test_login_requires_same_origin_and_rate_limits_before_more_scrypt(
    tmp_path: Path,
) -> None:
    client, _, store = make_client(tmp_path, login_ip_limit=2)
    forbidden = client.post(
        "/api/review/login",
        json={"username": "reviewer.one", "password": PASSWORD},
        headers={"Origin": "https://attacker.example"},
    )
    assert forbidden.status_code == 403
    for _ in range(2):
        response = client.post(
            "/api/review/login",
            json={"username": "reviewer.one", "password": "wrong password value"},
            headers=CLIENT_HEADERS,
        )
        assert response.status_code == 401
    limited = client.post(
        "/api/review/login",
        json={"username": "reviewer.one", "password": PASSWORD},
        headers=CLIENT_HEADERS,
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    store.close()


def test_inbox_is_private_and_explains_both_gates(tmp_path: Path) -> None:
    packet = task_packet()
    client, _, store = make_client(tmp_path, packet=packet)
    assert client.get("/api/review/tasks").status_code == 401
    login(client)
    response = client.get("/api/review/tasks")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"] == {
        "completed_tasks": 0,
        "emails_blocked": 1,
        "emails_waiting": 0,
        "papers_waiting": 1,
        "total_tasks": 1,
    }
    task = payload["tasks"][0]
    assert task["publication_gate"]["status"] == "awaiting_human"
    assert task["author_email_gate"]["status"] == "blocked_by_publication"
    assert task["author_email_gate"]["body"] == packet["author_email_gate"]["body"]
    assert task["review_cost_total_usd"] == 0.157606
    store.close()


def test_publication_then_email_decisions_are_separate_and_hash_bound(
    tmp_path: Path,
) -> None:
    packet = task_packet()
    client, _, store = make_client(tmp_path, packet=packet)
    csrf = login(client)
    binding = sha256_json(packet)
    decision_headers = {**CLIENT_HEADERS, "X-Nulspec-CSRF": csrf}

    premature_email = client.post(
        f"/api/review/tasks/{packet['task_id']}/decisions",
        json={
            "gate": "author_email",
            "decision": "APPROVE_SEND",
            "notes": "I reviewed the exact draft for factual accuracy.",
            "binding_sha256": binding,
            "confirmed": True,
        },
        headers=decision_headers,
    )
    assert premature_email.status_code == 422

    publication = client.post(
        f"/api/review/tasks/{packet['task_id']}/decisions",
        json={
            "gate": "publication",
            "decision": "APPROVE_RELEASE",
            "notes": "Both release reviews passed and the bound evidence is ready for human disposition.",
            "binding_sha256": binding,
            "confirmed": True,
        },
        headers=decision_headers,
    )
    assert publication.status_code == 201
    publication_task = publication.get_json()["task"]
    assert publication_task["publication_gate"]["status"] == "approved"
    assert publication_task["author_email_gate"]["status"] == "awaiting_human"
    publication_record = publication_task["publication_gate"]["decision"]["record"]
    assert publication_record["schema_version"] == PUBLICATION_DISPOSITION_SCHEMA
    assert publication_record["scientific_result_mutable"] is False
    assert publication_record["author_email_dispatch_authorized"] is False

    duplicate = client.post(
        f"/api/review/tasks/{packet['task_id']}/decisions",
        json={
            "gate": "publication",
            "decision": "APPROVE_RELEASE",
            "notes": "This duplicate must not overwrite the immutable decision.",
            "binding_sha256": binding,
            "confirmed": True,
        },
        headers=decision_headers,
    )
    assert duplicate.status_code == 409

    email = client.post(
        f"/api/review/tasks/{packet['task_id']}/decisions",
        json={
            "gate": "author_email",
            "decision": "APPROVE_SEND",
            "notes": "I reviewed the recipient list and exact draft for accuracy and fairness.",
            "binding_sha256": binding,
            "confirmed": True,
        },
        headers=decision_headers,
    )
    assert email.status_code == 201
    email_task = email.get_json()["task"]
    assert email_task["complete"] is True
    assert email_task["author_email_gate"]["status"] == "approved_for_operator_dispatch"
    email_record = email_task["author_email_gate"]["decision"]["record"]
    assert email_record["schema_version"] == EMAIL_APPROVAL_SCHEMA
    assert (
        email_record["author_email_sha256"]
        == packet["author_email_gate"]["draft_sha256"]
    )
    assert email_record["operator_dispatch_still_required"] is True
    assert (
        email_record["release_review_consensus_sha256"]
        == packet["source"]["release_review_consensus_sha256"]
    )
    assert "fable_action_closure_sha256" not in email_record
    assert "recipients" not in email_record

    final_inbox = client.get("/api/review/tasks").get_json()
    assert final_inbox["summary"]["completed_tasks"] == 1
    assert len(final_inbox["recent_activity"]) == 3
    store.close()


def test_decision_requires_csrf_confirmation_notes_and_current_binding(
    tmp_path: Path,
) -> None:
    packet = task_packet()
    client, _, store = make_client(tmp_path, packet=packet)
    csrf = login(client)
    base = {
        "gate": "publication",
        "decision": "KEEP_BLOCKED",
        "notes": "The evidence packet needs a documented correction first.",
        "binding_sha256": sha256_json(packet),
        "confirmed": True,
    }
    route = f"/api/review/tasks/{packet['task_id']}/decisions"
    assert client.post(route, json=base, headers=CLIENT_HEADERS).status_code == 403
    wrong = {**base, "binding_sha256": "0" * 64}
    assert (
        client.post(
            route,
            json=wrong,
            headers={**CLIENT_HEADERS, "X-Nulspec-CSRF": csrf},
        ).status_code
        == 422
    )
    unconfirmed = {**base, "confirmed": False}
    assert (
        client.post(
            route,
            json=unconfirmed,
            headers={**CLIENT_HEADERS, "X-Nulspec-CSRF": csrf},
        ).status_code
        == 422
    )
    store.close()


def test_missing_recipient_list_keeps_email_fail_closed(tmp_path: Path) -> None:
    packet = task_packet(recipients=False)
    client, _, store = make_client(tmp_path, packet=packet)
    csrf = login(client)
    route = f"/api/review/tasks/{packet['task_id']}/decisions"
    headers = {**CLIENT_HEADERS, "X-Nulspec-CSRF": csrf}
    response = client.post(
        route,
        json={
            "gate": "publication",
            "decision": "APPROVE_RELEASE",
            "notes": "The evidence can publish; author recipients are still not bound.",
            "binding_sha256": sha256_json(packet),
            "confirmed": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.get_json()["task"]["author_email_gate"]["status"] == (
        "blocked_missing_recipients"
    )
    store.close()


def test_logout_revokes_server_side_session(tmp_path: Path) -> None:
    client, _, store = make_client(tmp_path)
    csrf = login(client)
    response = client.post(
        "/api/review/logout",
        headers={**CLIENT_HEADERS, "X-Nulspec-CSRF": csrf},
    )
    assert response.status_code == 200
    assert "Max-Age=0" in response.headers["Set-Cookie"]
    assert client.get("/api/review/session").status_code == 401
    store.close()


def test_disabled_routes_fail_closed_without_exposing_configuration() -> None:
    app = Flask(__name__)
    register_nulspec_review_routes(app, service=DisabledReviewService("secret detail"))
    response = app.test_client().get("/api/review/tasks")
    assert response.status_code == 503
    assert response.get_json() == {"error": "review_unavailable", "ok": False}
    assert "secret detail" not in response.get_data(as_text=True)

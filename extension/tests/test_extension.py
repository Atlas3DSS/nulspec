from __future__ import annotations

import json
from pathlib import Path
import threading

from extension.analyze_judgments import summarize
from extension.external_judge import extract_decision, mapped_winner
from extension.matrixctl import arms
from extension.outer_teacher import build_packet
import extension.review_hierarchy as review_hierarchy
from extension.direct_teacher_providers import (
    FIRST_EVENT_TIMEOUT_SECONDS,
    STREAM_IDLE_TIMEOUT_SECONDS,
    TOTAL_RESPONSE_TIMEOUT_SECONDS,
    build_stream_payload,
    route_for,
)
from extension.review_hierarchy import (
    codex_packet,
    high_depth_harness,
    repair_plan_for_attempt,
    sanitize_failure_message,
    trace_evidence_index,
    validate_outer_outer,
    validate_qwen_packet,
)


def test_trace_index_excludes_summary_and_captures_final_event(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text('{"event":"run_started"}\n')
    before_summary = trace_evidence_index(tmp_path)
    (tmp_path / "public-summary.json").write_text("{}\n")
    assert trace_evidence_index(tmp_path) == before_summary
    events.write_text(events.read_text() + '{"event":"run_completed"}\n')
    assert trace_evidence_index(tmp_path) != before_summary


def test_extract_decision_handles_fenced_reasoning() -> None:
    result = extract_decision(
        'analysis first\n```json\n{"winner":"B","reason":"More coherent"}\n```'
    )
    assert result == {"winner": "B", "reason": "More coherent"}


def test_mapping_is_position_invariant() -> None:
    assert mapped_winner("B", "sft_first") == "ppo"
    assert mapped_winner("A", "ppo_first") == "ppo"
    assert mapped_winner("TIE", "ppo_first") == "tie"


def test_summary_excludes_position_inconsistent_pair() -> None:
    records = [
        {
            "pair_id": "good",
            "orientation": "sft_first",
            "winner": "B",
            "mapped_winner": "ppo",
        },
        {
            "pair_id": "good",
            "orientation": "ppo_first",
            "winner": "A",
            "mapped_winner": "ppo",
        },
        {
            "pair_id": "bad",
            "orientation": "sft_first",
            "winner": "A",
            "mapped_winner": "sft",
        },
        {
            "pair_id": "bad",
            "orientation": "ppo_first",
            "winner": "A",
            "mapped_winner": "ppo",
        },
    ]
    result = summarize(records)
    assert result["position_consistent_pairs"] == 1
    assert result["position_inconsistent_pairs"] == 1
    assert result["ppo_win_rate_ties_half"] == 1.0


def test_matrix_has_unique_dependency_ordered_arms() -> None:
    plan = arms()
    assert len(plan) == 18
    ids = [arm["arm_id"] for arm in plan]
    assert len(ids) == len(set(ids))
    for arm in plan:
        if arm["protocol"] == "paper-faithful":
            assert arm["depends_on"] in ids


def test_outer_teacher_packet_excludes_policy_content(tmp_path: Path) -> None:
    path = tmp_path / "judgments.jsonl"
    records = [
        {
            "label": "arm",
            "pair_id": "pair-1",
            "orientation": "sft_first",
            "winner": "A",
            "mapped_winner": "sft",
            "reason": "A is more coherent.",
            "model": "qwen-27b",
            "raw_response": "must not cross boundary",
            "expected_winner": "ppo",
        },
        {
            "label": "arm",
            "pair_id": "pair-1",
            "orientation": "ppo_first",
            "winner": "B",
            "mapped_winner": "sft",
            "reason": "B is more coherent.",
            "model": "qwen-27b",
            "raw_response": "must not cross boundary",
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records))
    packet = build_packet([("arm", path)], 1)
    encoded = json.dumps(packet)
    assert "raw_response" not in encoded
    assert "expected_winner" not in encoded
    assert "must not cross boundary" not in encoded


def qwen_only_packet() -> dict:
    return {
        "protocol": {
            "name": "qwen-reviewer-outer-audit-v1",
            "boundary": (
                "Contains only Qwen reviewer records. No story prompt, "
                "small-policy output, checkpoint, reward, or training state."
            ),
        },
        "pairs": [
            {
                "label": "arm",
                "pair_id": "pair-1",
                "selection_reason": "position_inconsistent",
                "qwen_reviews": [
                    {
                        "label": "arm",
                        "pair_id": "pair-1",
                        "orientation": "sft_first",
                        "winner": "A",
                        "mapped_winner": "sft",
                        "reason": "A is more coherent.",
                        "model": "qwen-27b",
                    },
                    {
                        "label": "arm",
                        "pair_id": "pair-1",
                        "orientation": "ppo_first",
                        "winner": "A",
                        "mapped_winner": "ppo",
                        "reason": "A is more coherent.",
                        "model": "qwen-27b",
                    },
                ],
            }
        ],
    }


def test_review_hierarchy_rejects_policy_content() -> None:
    packet = qwen_only_packet()
    packet["pairs"][0]["qwen_reviews"][0]["raw_response"] = "private output"
    try:
        validate_qwen_packet(packet)
    except RuntimeError as error:
        assert "field boundary" in str(error)
    else:
        raise AssertionError("policy content crossed the Qwen-only boundary")


def test_review_hierarchy_uses_high_reasoning_and_catalog_limits() -> None:
    packet = qwen_only_packet()
    validate_qwen_packet(packet)
    glm_route = route_for("z-ai/glm-5.2", 0)
    glm = high_depth_harness(
        "z-ai/glm-5.2",
        packet,
        glm_route,
    )
    kimi_route = route_for("moonshotai/kimi-k3", 0)
    kimi = high_depth_harness(
        "moonshotai/kimi-k3",
        packet,
        kimi_route,
    )
    assert glm["request_parameters"]["reasoning"] == {"effort": "high"}
    assert glm["request_parameters"]["max_tokens"] == 131_072
    assert kimi["request_parameters"]["reasoning_effort"] == "high"
    assert kimi["request_parameters"]["max_completion_tokens"] > 1_000_000

    glm_payload = build_stream_payload(
        glm_route,
        glm["system_prompt"],
        glm["user_prompt"],
        {"type": "object"},
        glm["request_parameters"]["max_tokens"],
    )
    assert glm_payload["stream"] is True
    assert glm_payload["response_format"]["type"] == "json_schema"
    assert "<output_schema>" in glm_payload["messages"][0]["content"]


def test_teacher_routes_use_hybrid_transport_and_bounded_stream_deadlines() -> None:
    glm = route_for("z-ai/glm-5.2", 0)
    kimi = route_for("moonshotai/kimi-k3", 0)
    assert glm.provider_name == "OpenRouter"
    assert glm.provider_model_id == "z-ai/glm-5.2"
    assert glm.endpoint == "https://openrouter.ai/api/v1/chat/completions"
    assert glm.request_parameters["provider"]["sort"] == "latency"
    assert kimi.provider_name == "Moonshot AI"
    assert kimi.provider_model_id == "kimi-k3"
    assert kimi.endpoint == "https://api.moonshot.ai/v1/chat/completions"
    assert "openrouter" not in kimi.endpoint.lower()
    assert FIRST_EVENT_TIMEOUT_SECONDS == 60
    assert STREAM_IDLE_TIMEOUT_SECONDS == 60
    assert TOTAL_RESPONSE_TIMEOUT_SECONDS == 240


def test_direct_billing_failure_reroutes_without_reducing_model_maximum() -> None:
    failure = "ProviderStreamError: Z.AI returned HTTP 402: insufficient balance"
    attempt = {
        "attempt_id": "run-GLM-A1",
        "requested_model_id": "z-ai/glm-5.2",
        "provider_route_index": 0,
        "http_status": 402,
        "failure": sanitize_failure_message(failure),
        "request_parameters": {"max_tokens": 1_029_863},
    }
    repair = repair_plan_for_attempt(attempt)
    assert repair["repair_of_attempt_id"] == "run-GLM-A1"
    assert repair["kind"] == "reissue_after_billing_failure_with_provider_reroute"
    assert repair["parameter_overrides"] == {"route_index": 1}
    assert "max_tokens" not in repair["parameter_overrides"]


def test_timeout_repair_reroutes_away_from_first_provider_route() -> None:
    attempt = {
        "attempt_id": "run-GLM-A1",
        "requested_model_id": "z-ai/glm-5.2",
        "provider_route_index": 0,
        "failure": "TimeoutError: The read operation timed out",
        "request_parameters": {"max_tokens": 131_072},
    }
    repair = repair_plan_for_attempt(attempt)
    assert repair["kind"] == "reissue_after_stream_timeout_with_provider_reroute"
    assert repair["parameter_overrides"] == {"route_index": 1}


def test_missing_kimi_fallback_key_blocks_instead_of_rotating_primary() -> None:
    attempt = {
        "attempt_id": "run-KIMI-A2",
        "requested_model_id": "moonshotai/kimi-k3",
        "provider_route_index": 1,
        "failure": (
            "ReviewHierarchyError: FIREWORKS_API_KEY is missing for "
            "fireworks-direct-fallback"
        ),
    }
    repair = repair_plan_for_attempt(attempt)
    assert repair["kind"] == "block_after_missing_independent_fallback_key"
    assert repair["terminal_without_reissue"] is True
    assert repair["parameter_overrides"] == {}


def test_invalid_teacher_attempt_is_reissued_as_a_linked_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    repairs: list[dict | None] = []

    def fake_attempt(
        model_id,
        attempt_id,
        provider_keys,
        packet,
        schema,
        trace_root,
        event_log,
        attempt_number,
        repair,
    ):
        repairs.append(repair)
        if attempt_number == 1:
            return {
                "attempt_id": attempt_id,
                "reviewer_family": "Kimi",
                "requested_model_id": model_id,
                "status": "invoked_invalid",
                "http_status": 503,
                "failure": "temporary provider failure",
                "request_parameters": {"max_tokens": 131_072},
                "usage": {},
            }
        return {
            "attempt_id": attempt_id,
            "reviewer_family": "Kimi",
            "requested_model_id": model_id,
            "status": "completed_valid",
            "audit": {"overall_assessment": "warn"},
            "usage": {"cost": 0.01},
        }

    monkeypatch.setattr(review_hierarchy, "run_outer_teacher_attempt", fake_attempt)
    chain = review_hierarchy.run_teacher_with_repairs(
        "moonshotai/kimi-k3",
        "run",
        {"MOONSHOT_API_KEY": "test-key"},
        qwen_only_packet(),
        {},
        tmp_path,
        tmp_path / "events.jsonl",
    )
    assert chain["status"] == "completed_valid"
    assert chain["attempt_count"] == 2
    assert chain["repair_count"] == 1
    assert repairs[0] is None
    assert repairs[1]["repair_of_attempt_id"] == "run-KIMI-A1"


def test_unfunded_kimi_fallback_blocks_chain_after_preserved_setup_failure(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[int] = []

    def fake_attempt(
        model_id,
        attempt_id,
        provider_keys,
        packet,
        schema,
        trace_root,
        event_log,
        attempt_number,
        repair,
    ):
        calls.append(attempt_number)
        if attempt_number == 1:
            return {
                "attempt_id": attempt_id,
                "reviewer_family": "Kimi",
                "requested_model_id": model_id,
                "provider_route_index": 0,
                "status": "invoked_invalid",
                "failure": "ProviderStreamError: stream timeout",
                "usage": {},
            }
        return {
            "attempt_id": attempt_id,
            "reviewer_family": "Kimi",
            "requested_model_id": model_id,
            "provider_route_index": 1,
            "status": "setup_failed",
            "failure": (
                "ReviewHierarchyError: FIREWORKS_API_KEY is missing for "
                "fireworks-direct-fallback"
            ),
            "usage": {},
        }

    monkeypatch.setattr(review_hierarchy, "run_outer_teacher_attempt", fake_attempt)
    chain = review_hierarchy.run_teacher_with_repairs(
        "moonshotai/kimi-k3",
        "run",
        {"MOONSHOT_API_KEY": "test-key"},
        qwen_only_packet(),
        {},
        tmp_path,
        tmp_path / "events.jsonl",
    )
    assert calls == [1, 2]
    assert chain["status"] == "blocked_no_configured_fallback"
    assert chain["attempt_count"] == 2
    assert chain["terminal_block"]["terminal_without_reissue"] is True
    assert (
        tmp_path / "outer-teachers/moonshotai-kimi-k3/repair-blocked-after-02.json"
    ).is_file()


def test_glm_and_kimi_fan_out_before_join(tmp_path: Path, monkeypatch) -> None:
    barrier = threading.Barrier(2)

    def fake_chain(
        model_id,
        run_id,
        provider_keys,
        packet,
        schema,
        trace_root,
        event_log,
    ):
        barrier.wait(timeout=2)
        family = "GLM" if model_id.startswith("z-ai/") else "Kimi"
        return {
            "reviewer_family": family,
            "requested_model_id": model_id,
            "status": "completed_valid",
            "attempts": [],
        }

    monkeypatch.setattr(review_hierarchy, "run_teacher_with_repairs", fake_chain)
    models = ("z-ai/glm-5.2", "moonshotai/kimi-k3")
    chains = review_hierarchy.run_parallel_teachers(
        models,
        "run",
        {
            "ZAI_API_KEY": "test-zai-key",
            "MOONSHOT_API_KEY": "test-moonshot-key",
        },
        qwen_only_packet(),
        {},
        tmp_path,
        tmp_path / "events.jsonl",
    )
    assert [chain["requested_model_id"] for chain in chains] == list(models)


def test_invalid_codex_adjudication_is_reissued_as_linked_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    repairs: list[dict | None] = []

    def fake_codex_attempt(
        packet,
        schema_path,
        directory,
        event_log,
        model,
        attempt_id,
        attempt_number,
        repair,
    ):
        repairs.append(repair)
        result = {
            "attempt_id": attempt_id,
            "attempt_number": attempt_number,
            "started_at_utc": f"start-{attempt_number}",
            "completed_at_utc": f"end-{attempt_number}",
            "elapsed_seconds": 1.0,
            "codex_cli_version": "codex-test",
            "return_code": 0,
            "status": "completed_invalid",
        }
        if attempt_number == 1:
            result["failure"] = "partial pair identity"
        else:
            result["status"] = "completed_valid"
            result["decision"] = {"qwen_process_assessment": "warn"}
            result["contract_warnings"] = []
        return result

    monkeypatch.setattr(
        review_hierarchy, "run_codex_outer_outer_attempt", fake_codex_attempt
    )
    chain = review_hierarchy.run_codex_outer_outer(
        "run",
        {},
        tmp_path / "schema.json",
        tmp_path,
        tmp_path / "events.jsonl",
        None,
    )
    assert chain["status"] == "completed_valid"
    assert chain["attempt_count"] == 2
    assert chain["repair_count"] == 1
    assert repairs[0] is None
    assert repairs[1]["repair_of_attempt_id"] == "run-CODEX-A1"
    assert (tmp_path / "outer-codex/repair-01-to-02.json").is_file()


def teacher_attempt(family: str, assessment: str) -> dict:
    return {
        "attempt_id": f"run-{family}",
        "reviewer_family": family,
        "requested_model_id": family.lower(),
        "status": "completed_valid",
        "invocation_count": 1,
        "model_invocation_count": 1,
        "retry_allowed": False,
        "decision_weight": 1,
        "provider_model_id": f"{family.lower()}-provider-model",
        "response_model": f"{family.lower()}-provider-model",
        "provider_route": {"route_id": f"{family.lower()}-route"},
        "provider_route_sha256": "a" * 64,
        "raw_response_byte_count": 123,
        "raw_response_sha256": "b" * 64,
        "stream_events_byte_count": 100,
        "stream_events_sha256": "c" * 64,
        "usage": {"total_tokens": 42, "cost": 0.01},
        "audit": {
            "scope_confirmation": "qwen_records_only",
            "overall_assessment": assessment,
            "reviewer_reliability": 0.5,
            "findings": [],
            "systemic_patterns": [],
            "summary": "Test audit.",
        },
    }


def test_codex_packet_contains_only_glm_and_kimi_teacher_attempts() -> None:
    attempts = [teacher_attempt("GLM", "fail"), teacher_attempt("Kimi", "warn")]
    packet = codex_packet(qwen_only_packet(), attempts)
    assert [row["reviewer_family"] for row in packet["outer_teacher_attempts"]] == [
        "GLM",
        "Kimi",
    ]
    assert packet["outer_teacher_attempts"][0]["provider_route"] == {
        "route_id": "glm-route"
    }
    assert packet["outer_teacher_attempts"][0]["stream_events_sha256"] == "c" * 64
    assert packet["outer_teacher_attempts"][0]["model_id"] == "glm"
    assert "Fable is not part" in packet["protocol"]["excluded_reviewer"]
    decision = {
        "scope_confirmation": "qwen_records_and_outer_teacher_audits_only",
        "teacher_assessments": [
            {
                "attempt_id": attempt["attempt_id"],
                "model_id": attempt["requested_model_id"],
                "trace_valid": True,
                "assessment": attempt["audit"]["overall_assessment"],
                "reliability": 0.5,
                "notes": "Valid test trace.",
            }
            for attempt in attempts
        ],
        "cross_teacher_agreement": "partial",
        "preserved_disagreements": [],
        "qwen_process_assessment": "fail",
        "qwen_reviewer_reliability": 0.4,
        "findings": [],
        "release_recommendation": "accept_as_process_audit",
        "required_human_actions": [],
        "release_control": {
            "automatic_publication_authorized": False,
            "automatic_training_signal_authorized": False,
            "author_email_dispatch_authorized": False,
        },
        "summary": "The process audit is usable.",
    }
    validate_outer_outer(decision, packet)

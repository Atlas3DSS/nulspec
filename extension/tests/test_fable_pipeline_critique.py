from __future__ import annotations

import pytest

from extension.fable_pipeline_critique import (
    CritiqueError,
    DEFAULT_SOURCE_PATHS,
    build_packet,
    validate_critique,
    validate_claude_cli_schema,
    validate_explicit_reissue,
    validate_pipeline_summary,
    validate_validation_record,
)


def valid_summary() -> dict:
    return {
        "architecture": {
            "teacher_execution": "parallel_fan_out_then_join",
            "fable_in_teacher_loop": False,
        },
        "outer_teacher_chains": [
            {"reviewer_family": "GLM", "status": "completed_valid"},
            {"reviewer_family": "Kimi", "status": "completed_valid"},
        ],
        "outer_teacher_valid_count": 2,
        "outer_adjudicator": {"status": "completed_valid"},
        "release_control": {
            "publication_authorized": False,
            "training_signal_change_authorized": False,
            "author_email_dispatch_authorized": False,
        },
    }


def valid_critique() -> dict:
    return {
        "scope_confirmation": "pipeline_architecture_and_trace_only",
        "overall_assessment": "sound_with_changes",
        "confidence": 0.8,
        "findings": [],
        "authority_confirmation": {
            "is_teacher_vote": False,
            "can_change_qwen_results": False,
            "can_change_training_signals": False,
            "can_authorize_publication": False,
            "can_authorize_email": False,
        },
    }


def test_fable_critique_requires_completed_parallel_pipeline() -> None:
    validate_pipeline_summary(valid_summary())
    sequential = valid_summary()
    sequential["architecture"]["teacher_execution"] = "sequential"
    with pytest.raises(CritiqueError, match="not a parallel"):
        validate_pipeline_summary(sequential)


def test_fable_critique_requires_passing_validation_record() -> None:
    validate_validation_record({"status": "passed", "commands": [{"exit_code": 0}]})
    with pytest.raises(CritiqueError, match="has not passed"):
        validate_validation_record({"status": "failed", "commands": [{"exit_code": 1}]})


def test_fable_critique_validation_is_bound_to_pipeline_trace() -> None:
    summary = valid_summary()
    summary["run_id"] = "pipeline-v1"
    summary["trace_index"] = {
        "evidence_file_count": 42,
        "evidence_aggregate_sha256": "a" * 64,
    }
    validation = {
        "status": "passed",
        "pipeline_run_id": "pipeline-v1",
        "commands": [{"exit_code": 0}],
        "trace_index": summary["trace_index"],
    }
    validate_validation_record(validation, summary)
    validation["trace_index"] = {
        **validation["trace_index"],
        "evidence_aggregate_sha256": "b" * 64,
    }
    with pytest.raises(CritiqueError, match="different evidence_aggregate"):
        validate_validation_record(validation, summary)


def test_fable_schema_preflight_rejects_unsupported_draft_declaration() -> None:
    validate_claude_cli_schema({"type": "object", "$defs": {}})
    with pytest.raises(CritiqueError, match="must omit"):
        validate_claude_cli_schema(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            }
        )


def test_fable_explicit_reissue_requires_bound_pre_model_failure(tmp_path) -> None:
    prior_record = tmp_path / "prior.json"
    prior_record.write_text(
        """{
  "run_id": "fable-v1",
  "status": "completed_invalid",
  "raw_stdout_byte_count": 0
}\n"""
    )
    prior_stderr = tmp_path / "stderr.txt"
    prior_stderr.write_text(
        "Error: --json-schema is not a valid JSON Schema: unsupported draft\n"
    )

    reissue = validate_explicit_reissue(
        "fable-v2", "fable-v1", prior_record, prior_stderr
    )

    assert reissue["explicit_user_reissue_authorized"] is True
    assert reissue["reissue_of_run_id"] == "fable-v1"
    assert reissue["prior_record_sha256"]
    with pytest.raises(CritiqueError, match="new run ID"):
        validate_explicit_reissue("fable-v1", "fable-v1", prior_record, prior_stderr)


def test_fable_packet_labels_explicit_reissue() -> None:
    packet = build_packet(
        valid_summary(),
        {"status": "passed"},
        {},
        explicit_reissue_of="fable-v1",
    )

    assert packet["protocol"]["automatic_retry"] is False
    assert packet["protocol"]["explicit_user_reissue_authorized"] is True
    assert packet["protocol"]["reissue_of_run_id"] == "fable-v1"


def test_fable_packet_source_boundary_includes_transport_and_validator() -> None:
    assert {
        "extension/direct_teacher_providers.py",
        "extension/validate_review_hierarchy.py",
    }.issubset({path.as_posix() for path in DEFAULT_SOURCE_PATHS})


def test_fable_critique_cannot_claim_authority() -> None:
    validate_critique(valid_critique())
    unauthorized = valid_critique()
    unauthorized["authority_confirmation"]["can_authorize_publication"] = True
    with pytest.raises(CritiqueError, match="authority controls"):
        validate_critique(unauthorized)

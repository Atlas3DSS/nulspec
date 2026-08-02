from __future__ import annotations

import json
from pathlib import Path

import pytest

from extension.fable_pipeline_critique import (
    BATCH_SCHEMA,
    CritiqueError,
    DEFAULT_SOURCE_PATHS,
    FABLE_BATCH_SIZE,
    FABLE_SAMPLE_SIZE,
    build_batch_packet,
    claim_batch,
    load_batch_manifest,
    parse_args,
    select_batch_samples,
    validate_relative_input_path,
    validate_critique,
    validate_claude_cli_schema,
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


def write_batch_fixture(root: Path, paper_count: int = FABLE_BATCH_SIZE) -> Path:
    papers = []
    for index in range(paper_count):
        study_id = f"study-{index:02d}"
        summary = valid_summary()
        summary["run_id"] = f"pipeline-{index:02d}"
        summary["trace_index"] = {
            "evidence_file_count": index + 1,
            "evidence_aggregate_sha256": f"{index:064x}",
        }
        validation = {
            "status": "passed",
            "pipeline_run_id": summary["run_id"],
            "commands": [{"exit_code": 0}],
            "trace_index": summary["trace_index"],
        }
        paths = {
            "pipeline_summary": f"inputs/{study_id}-summary.json",
            "validation": f"inputs/{study_id}-validation.json",
            "corrections": f"inputs/{study_id}-corrections.json",
        }
        for field, value in (
            ("pipeline_summary", summary),
            ("validation", validation),
            ("corrections", {"study_id": study_id}),
        ):
            path = root / paths[field]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        papers.append({"study_id": study_id, **paths})
    manifest = root / "batch.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": BATCH_SCHEMA,
                "batch_id": "batch-001",
                "papers": papers,
            }
        )
    )
    return manifest


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

    active_fable = valid_summary()
    active_fable["release_control"]["fable_batch_only"] = False
    with pytest.raises(CritiqueError, match="active per-paper Fable"):
        validate_pipeline_summary(active_fable)


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


def test_fable_cli_requires_batch_and_has_no_single_run_mode(capsys) -> None:
    with pytest.raises(SystemExit):
        parse_args([])
    assert "--batch-manifest" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        parse_args(
            [
                "--batch-manifest",
                "batch.json",
                "--run-id",
                "batch-001",
                "--trace-root",
                "trace",
                "--public-result",
                "result.json",
                "--historical-single-run",
            ]
        )
    assert "unrecognized arguments" in capsys.readouterr().err


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


def test_batch_manifest_requires_ten_complete_unique_papers(tmp_path: Path) -> None:
    manifest = write_batch_fixture(tmp_path)
    batch_id, papers = load_batch_manifest(manifest, tmp_path)

    assert batch_id == "batch-001"
    assert len(papers) == FABLE_BATCH_SIZE

    short_manifest = write_batch_fixture(tmp_path / "short", paper_count=9)
    with pytest.raises(CritiqueError, match="exactly 10 papers"):
        load_batch_manifest(short_manifest, tmp_path / "short")


def test_batch_selection_is_randomized_but_reproducible_and_order_independent(
    tmp_path: Path,
) -> None:
    _, papers = load_batch_manifest(write_batch_fixture(tmp_path), tmp_path)
    seed = "12" * 32

    first = select_batch_samples(papers, seed)
    second = select_batch_samples(list(reversed(papers)), seed)

    assert len(first) == FABLE_SAMPLE_SIZE
    assert [paper["study_id"] for paper in first] == [
        paper["study_id"] for paper in second
    ]


def test_batch_packet_contains_one_three_of_ten_cadence(tmp_path: Path) -> None:
    batch_id, papers = load_batch_manifest(write_batch_fixture(tmp_path), tmp_path)
    seed = "34" * 32
    selected = select_batch_samples(papers, seed)

    packet = build_batch_packet(batch_id, papers, selected, seed)

    cadence = packet["protocol"]["cadence"]
    assert cadence["eligible_completed_papers"] == 10
    assert cadence["random_sample_size"] == 3
    assert cadence["invocations_per_batch"] == 1
    assert len(packet["pipeline_samples"]) == 3
    assert packet["protocol"]["automatic_retry"] is False


def test_batch_registry_rejects_batch_and_paper_reuse(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    study_ids = [f"study-{index:02d}" for index in range(10)]
    kwargs = {
        "batch_id": "batch-001",
        "run_id": "run-001",
        "all_study_ids": study_ids,
        "selected_study_ids": study_ids[:3],
        "selection_seed": "56" * 32,
        "packet_sha256": "a" * 64,
    }
    claim_batch(registry, **kwargs)

    with pytest.raises(CritiqueError, match="already claimed"):
        claim_batch(registry, **kwargs)
    with pytest.raises(CritiqueError, match="already used"):
        claim_batch(
            registry,
            **{
                **kwargs,
                "batch_id": "batch-002",
                "run_id": "run-002",
                "all_study_ids": [study_ids[0], *[f"new-{i}" for i in range(9)]],
                "selected_study_ids": [study_ids[0], "new-0", "new-1"],
            },
        )


def test_batch_paths_cannot_escape_repository() -> None:
    assert validate_relative_input_path("results/summary.json", "summary") == Path(
        "results/summary.json"
    )
    with pytest.raises(CritiqueError, match="inside the repository"):
        validate_relative_input_path("../private.json", "summary")
    with pytest.raises(CritiqueError, match="inside the repository"):
        validate_relative_input_path("/etc/passwd", "summary")

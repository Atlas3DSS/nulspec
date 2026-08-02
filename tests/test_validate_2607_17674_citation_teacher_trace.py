from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts/validate_2607_17674_citation_teacher_trace.py"
SPEC = importlib.util.spec_from_file_location("validate_citation_teacher_trace", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def packet() -> dict:
    return {
        "population_summary": {
            "source_reviews": 41,
            "citation_occurrences": 74,
            "evidence_chunks": 112,
        },
        "sources": [
            {
                "citation_key": "source-a",
                "citation_review": {
                    "occurrence_assessments": [{"occurrence_id": "occurrence-a"}]
                },
                "evidence_chunk_reviews": [{"chunk_id": "chunk-a"}],
            }
        ],
    }


def teacher_record() -> dict:
    return {
        "scope_confirmation": "qwen_citation_records_only",
        "coverage_confirmation": {
            "source_reviews": 41,
            "citation_occurrences": 74,
            "evidence_chunks": 112,
            "inspected_all_records": True,
        },
        "overall_assessment": "pass",
        "qwen_reviewer_quality_score": 8,
        "findings": [],
        "systemic_patterns": [],
        "boundary_limitations": ["Full sources are outside the packet."],
        "summary": "The bounded review passed.",
    }


def binding(path: Path) -> dict:
    return {
        "relative_path": path.name,
        "bytes": path.stat().st_size,
        "sha256": VALIDATOR.sha256_file(path),
    }


def build_teacher_chain(root: Path, packet_sha256: str) -> None:
    attempt = root / "attempt-01"
    parsed_path = attempt / "parsed.json"
    write_json(parsed_path, teacher_record())
    route = VALIDATOR.PROVIDER_ROUTES["z-ai/glm-5.2"][0]
    write_json(
        attempt / "attempt-record.json",
        {
            "logical_teacher": "glm",
            "requested_model": "z-ai/glm-5.2",
            "packet_sha256": packet_sha256,
            "route": route.public_record(),
            "accounting": {
                "accounted_cost_usd": 0.25,
                "accounting_basis": "completed_usage",
            },
            "valid": True,
            "errors": [],
            "artifacts": [binding(parsed_path)],
        },
    )
    write_json(
        root / "accepted.json",
        {
            "logical_teacher": "glm",
            "parsed_relative_path": "attempt-01/parsed.json",
            "parsed_sha256": VALIDATOR.sha256_file(parsed_path),
        },
    )


def test_teacher_chain_requires_bound_terminal_valid_attempt(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, packet())
    packet_sha256 = VALIDATOR.sha256_file(packet_path)
    root = tmp_path / "glm"
    build_teacher_chain(root, packet_sha256)
    schema = VALIDATOR.load_object(VALIDATOR.TEACHER_SCHEMA)
    record, summary = VALIDATOR.validate_teacher_chain(
        root,
        "glm",
        "z-ai/glm-5.2",
        packet(),
        packet_sha256,
        schema,
    )
    assert record["qwen_reviewer_quality_score"] == 8
    assert summary["accounted_cost_usd"] == 0.25


def test_teacher_chain_rejects_unbound_artifact(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, packet())
    packet_sha256 = VALIDATOR.sha256_file(packet_path)
    root = tmp_path / "glm"
    build_teacher_chain(root, packet_sha256)
    (root / "attempt-01" / "unbound.txt").write_text("not in the manifest")
    schema = VALIDATOR.load_object(VALIDATOR.TEACHER_SCHEMA)
    with pytest.raises(VALIDATOR.TraceValidationError, match="unbound"):
        VALIDATOR.validate_teacher_chain(
            root,
            "glm",
            "z-ai/glm-5.2",
            packet(),
            packet_sha256,
            schema,
        )

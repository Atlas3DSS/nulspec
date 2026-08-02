from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts/run_2607_17674_codex_citation_adjudication.py"
SPEC = importlib.util.spec_from_file_location("run_codex_adjudication", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def qwen_packet() -> dict:
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


def test_build_codex_packet_includes_both_complete_attempt_chains(tmp_path: Path) -> None:
    packet_path = tmp_path / "qwen-packet.json"
    write_json(packet_path, qwen_packet())
    packet_hash = RUNNER.sha256_file(packet_path)
    trace = tmp_path / "trace"
    write_json(
        trace / "teacher-completion.json",
        {"teacher_packet_sha256": packet_hash},
    )
    for teacher in ("glm", "kimi"):
        parsed_path = trace / "teachers" / teacher / "attempt-01" / "parsed.json"
        write_json(parsed_path, teacher_record())
        write_json(
            trace / "teachers" / teacher / "attempt-01" / "attempt-record.json",
            {
                "logical_teacher": teacher,
                "valid": True,
                "artifacts": [],
                "transport": {"reasoning_content": "bounded teacher reasoning"},
            },
        )
        write_json(
            trace / "teachers" / teacher / "accepted.json",
            {
                "parsed_relative_path": "attempt-01/parsed.json",
                "parsed_sha256": RUNNER.sha256_file(parsed_path),
            },
        )
    schema = RUNNER.load_object(RUNNER.DEFAULT_TEACHER_SCHEMA)
    packet, records = RUNNER.build_codex_packet(
        qwen_packet(), packet_hash, trace, schema
    )

    assert set(packet["teacher_chains"]) == {"glm", "kimi"}
    assert set(records) == {"glm", "kimi"}
    assert len(packet["teacher_chains"]["glm"]["attempts"]) == 1
    assert (
        packet["teacher_chains"]["kimi"]["attempts"][0]["attempt_record"][
            "transport"
        ]["reasoning_content"]
        == "bounded teacher reasoning"
    )


def test_frozen_codex_bindings_match() -> None:
    config = RUNNER.load_object(RUNNER.DEFAULT_CONFIG)
    RUNNER.verify_bindings(config)

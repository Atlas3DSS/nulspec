from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "citation_teacher_contract.py"
SPEC = importlib.util.spec_from_file_location("citation_teacher_contract", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTRACT
SPEC.loader.exec_module(CONTRACT)


def teacher_schema() -> dict:
    return json.loads(
        (WORKSPACE / "protocols/2607.17674/citation_teacher_audit.schema.json").read_text()
    )


def codex_schema() -> dict:
    return json.loads(
        (
            WORKSPACE
            / "protocols/2607.17674/citation_codex_adjudication.schema.json"
        ).read_text()
    )


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


def valid_teacher_record() -> dict:
    return {
        "scope_confirmation": "qwen_citation_records_only",
        "coverage_confirmation": {
            "source_reviews": 41,
            "citation_occurrences": 74,
            "evidence_chunks": 112,
            "inspected_all_records": True,
        },
        "overall_assessment": "warn",
        "qwen_reviewer_quality_score": 7,
        "findings": [
            {
                "citation_key": "source-a",
                "occurrence_id": "occurrence-a",
                "chunk_id": "chunk-a",
                "severity": "warning",
                "issue_type": "score_calibration",
                "qwen_record_reference": "source-a/final-review",
                "rationale": "The score is high relative to the stated caveat.",
                "recommended_action": "Recalibrate the score while retaining the caveat.",
            }
        ],
        "systemic_patterns": [],
        "boundary_limitations": ["Full source text is outside this packet."],
        "summary": "Conditional review complete.",
    }


def test_teacher_record_accepts_exact_packet_identities() -> None:
    assert CONTRACT.validate_teacher_record(
        valid_teacher_record(), packet(), teacher_schema()
    ) == []


def test_teacher_record_rejects_false_coverage_and_invented_identifier() -> None:
    record = valid_teacher_record()
    record["coverage_confirmation"]["inspected_all_records"] = False
    record["findings"][0]["occurrence_id"] = "invented"
    errors = CONTRACT.validate_teacher_record(record, packet(), teacher_schema())
    assert any("must be true" in error for error in errors)
    assert any("absent from cited source" in error for error in errors)


def test_schema_rejects_boolean_as_integer_and_additional_property() -> None:
    record = valid_teacher_record()
    record["qwen_reviewer_quality_score"] = True
    record["unexpected"] = "leak"
    errors = CONTRACT.validate_teacher_record(record, packet(), teacher_schema())
    assert any("expected type" in error for error in errors)
    assert any("unexpected property" in error for error in errors)


def valid_codex_record() -> dict:
    return {
        "scope_confirmation": "qwen_records_and_teacher_audits_only",
        "teacher_assessments": [
            {
                "teacher": "glm",
                "execution_chain_valid": True,
                "scientific_assessment": "warn",
                "qwen_quality_score": 7,
                "strengths": ["Complete coverage."],
                "limitations": ["Full sources are outside the layer."],
            },
            {
                "teacher": "kimi",
                "execution_chain_valid": True,
                "scientific_assessment": "warn",
                "qwen_quality_score": 7,
                "strengths": ["Complete coverage."],
                "limitations": ["Full sources are outside the layer."],
            },
        ],
        "teacher_disagreement_present": False,
        "teacher_disagreements": [],
        "citation_adjudications": [
            {
                "citation_key": "source-a",
                "occurrence_id": "occurrence-a",
                "status": "qwen_record_accepted",
                "basis": "Both teachers accepted the bounded record.",
            }
        ],
        "final_qwen_reviewer_quality_score": 7,
        "overall_assessment": "warn",
        "boundary_limitations": ["Full sources are outside this layer."],
        "release_controls": {
            "primary_results_changed": False,
            "training_authorized": False,
            "publication_authorized": False,
            "email_authorized": False,
        },
        "summary": "The bounded reviewer audit warrants a warning.",
    }


def test_codex_record_preserves_teacher_decisions_and_release_boundary() -> None:
    teachers = {"glm": valid_teacher_record(), "kimi": valid_teacher_record()}
    assert CONTRACT.validate_codex_record(
        valid_codex_record(), packet(), teachers, codex_schema()
    ) == []


def test_codex_record_cannot_hide_obvious_teacher_disagreement() -> None:
    teachers = {"glm": valid_teacher_record(), "kimi": valid_teacher_record()}
    teachers["kimi"]["qwen_reviewer_quality_score"] = 5
    teachers["kimi"]["overall_assessment"] = "fail"
    record = valid_codex_record()
    record["teacher_assessments"][1]["qwen_quality_score"] = 5
    record["teacher_assessments"][1]["scientific_assessment"] = "fail"
    errors = CONTRACT.validate_codex_record(record, packet(), teachers, codex_schema())
    assert any("collapsed a teacher disagreement" in error for error in errors)

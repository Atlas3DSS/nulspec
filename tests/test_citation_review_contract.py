from __future__ import annotations

import importlib.util
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "citation_review_contract.py"
SPEC = importlib.util.spec_from_file_location("citation_contract", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


def packet() -> dict:
    return {
        "source_identity": {"citation_key": "paper2026"},
        "target_occurrences": [{"occurrence_id": "paper2026:occurrence-001"}],
        "source_chunk": {
            "chunk_id": "paper2026:chunk-0001",
            "text": "Header\nThe method improves accuracy under condition A.\n",
            "page_spans": [
                {
                    "page_number": 1,
                    "chunk_character_start": 0,
                    "chunk_character_end": 55,
                }
            ],
        },
    }


def evidence_record() -> dict:
    return {
        "schema_version": 1,
        "review_type": "citation_evidence_chunk",
        "citation_key": "paper2026",
        "chunk_id": "paper2026:chunk-0001",
        "chunk_summary": "A conditional accuracy result.",
        "source_identity_observations": "Title fragment is consistent.",
        "occurrence_findings": [
            {
                "occurrence_id": "paper2026:occurrence-001",
                "claim_focus": "The method improves accuracy.",
                "evidence_candidates": [
                    {
                        "page_number": 1,
                        "section_or_heading": "Results",
                        "excerpt": "The method improves accuracy under condition A.",
                        "relevance": "Direct but qualified support.",
                        "stance": "qualifies_claim",
                    }
                ],
                "no_relevant_evidence_explanation": "",
            }
        ],
        "coverage_confirmation": True,
        "unreviewable_text_reason": "",
    }


def review_record() -> dict:
    return {
        "schema_version": 1,
        "review_type": "citation_review",
        "citation_key": "paper2026",
        "source_identity": {
            "status": "match",
            "rationale": "The title and result match the cited source.",
        },
        "source_contribution_summary": "Reports a conditional accuracy gain.",
        "occurrence_assessments": [
            {
                "occurrence_id": "paper2026:occurrence-001",
                "claim_summary": "The method improves accuracy.",
                "source_relevant_contribution": "It improves under condition A.",
                "evidence": [
                    {
                        "chunk_id": "paper2026:chunk-0001",
                        "page_number": 1,
                        "section_or_heading": "Results",
                        "excerpt": "The method improves accuracy under condition A.",
                    }
                ],
                "support_class": "partially_supports",
                "citation_appropriateness_score": 7,
                "confidence": 0.9,
                "limitation_or_correction": "Retain condition A.",
            }
        ],
        "overall_notes": "",
        "self_check": {
            "all_occurrences_reviewed": True,
            "all_evidence_grounded": True,
            "uncertainty_notes": "",
        },
    }


def test_valid_evidence_and_review_pass() -> None:
    source_plan = {
        "citation_key": "paper2026",
        "target_occurrences": packet()["target_occurrences"],
    }
    evidence = evidence_record()
    assert CONTRACT.validate_evidence_record(evidence, packet()) == []
    assert CONTRACT.validate_review_record(review_record(), source_plan, [evidence]) == []


def test_hallucinated_evidence_fails_both_stages() -> None:
    evidence = evidence_record()
    evidence["occurrence_findings"][0]["evidence_candidates"][0]["excerpt"] = (
        "This sentence is absent."
    )
    errors = CONTRACT.validate_evidence_record(evidence, packet())
    assert any("not grounded" in error for error in errors)

    final = review_record()
    final["occurrence_assessments"][0]["evidence"][0]["excerpt"] = (
        "This sentence is absent."
    )
    source_plan = {
        "citation_key": "paper2026",
        "target_occurrences": packet()["target_occurrences"],
    }
    errors = CONTRACT.validate_review_record(final, source_plan, [evidence_record()])
    assert any("not copied" in error for error in errors)


def test_wrong_occurrence_identity_fails_closed() -> None:
    evidence = evidence_record()
    evidence["occurrence_findings"][0]["occurrence_id"] = "wrong"
    errors = CONTRACT.validate_evidence_record(evidence, packet())
    assert any("order/identity differs" in error for error in errors)

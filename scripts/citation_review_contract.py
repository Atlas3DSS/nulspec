"""Strict semantic validators for NULSPEC citation-review model outputs."""

from __future__ import annotations

import unicodedata
from typing import Any


EVIDENCE_TOP_LEVEL_FIELDS = {
    "schema_version",
    "review_type",
    "citation_key",
    "chunk_id",
    "chunk_summary",
    "source_identity_observations",
    "occurrence_findings",
    "coverage_confirmation",
    "unreviewable_text_reason",
}
EVIDENCE_FINDING_FIELDS = {
    "occurrence_id",
    "claim_focus",
    "evidence_candidates",
    "no_relevant_evidence_explanation",
}
EVIDENCE_CANDIDATE_FIELDS = {
    "page_number",
    "section_or_heading",
    "excerpt",
    "relevance",
    "stance",
}
EVIDENCE_STANCES = {
    "supports_claim",
    "qualifies_claim",
    "contradicts_claim",
    "background_only",
}
REVIEW_TOP_LEVEL_FIELDS = {
    "schema_version",
    "review_type",
    "citation_key",
    "source_identity",
    "source_contribution_summary",
    "occurrence_assessments",
    "overall_notes",
    "self_check",
}
ASSESSMENT_FIELDS = {
    "occurrence_id",
    "claim_summary",
    "source_relevant_contribution",
    "evidence",
    "support_class",
    "citation_appropriateness_score",
    "confidence",
    "limitation_or_correction",
}
REVIEW_EVIDENCE_FIELDS = {
    "chunk_id",
    "page_number",
    "section_or_heading",
    "excerpt",
}
SUPPORT_CLASSES = {
    "supports",
    "partially_supports",
    "does_not_support",
    "contradicts",
    "not_verifiable",
}


def normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    actual = set(value)
    if actual != expected:
        errors.append(
            f"{label} fields differ: missing={sorted(expected - actual)} "
            f"extra={sorted(actual - expected)}"
        )
        return False
    return True


def page_text(packet: dict[str, Any], page_number: int) -> str:
    source_chunk = packet["source_chunk"]
    text = str(source_chunk["text"])
    pieces = []
    for span in source_chunk["page_spans"]:
        if int(span["page_number"]) == page_number:
            pieces.append(
                text[
                    int(span["chunk_character_start"]) : int(
                        span["chunk_character_end"]
                    )
                ]
            )
    return "".join(pieces)


def validate_evidence_record(
    value: Any, packet: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if not exact_fields(value, EVIDENCE_TOP_LEVEL_FIELDS, "evidence record", errors):
        return errors
    expected_key = str(packet["source_identity"]["citation_key"])
    expected_chunk = str(packet["source_chunk"]["chunk_id"])
    if value["schema_version"] != 1:
        errors.append("evidence schema_version must equal 1")
    if value["review_type"] != "citation_evidence_chunk":
        errors.append("evidence review_type differs")
    if value["citation_key"] != expected_key:
        errors.append("evidence citation_key differs from packet")
    if value["chunk_id"] != expected_chunk:
        errors.append("evidence chunk_id differs from packet")
    if value["coverage_confirmation"] is not True:
        errors.append("coverage_confirmation must be true")
    if not isinstance(value["chunk_summary"], str) or not value["chunk_summary"].strip():
        errors.append("chunk_summary must be nonempty")
    if not isinstance(value["source_identity_observations"], str):
        errors.append("source_identity_observations must be a string")
    if not isinstance(value["unreviewable_text_reason"], str):
        errors.append("unreviewable_text_reason must be a string")

    expected_occurrences = [
        str(item["occurrence_id"]) for item in packet["target_occurrences"]
    ]
    findings = value["occurrence_findings"]
    if not isinstance(findings, list):
        errors.append("occurrence_findings must be an array")
        return errors
    actual_occurrences: list[str] = []
    valid_pages = {
        int(span["page_number"]) for span in packet["source_chunk"]["page_spans"]
    }
    for index, finding in enumerate(findings):
        label = f"occurrence_findings[{index}]"
        if not exact_fields(finding, EVIDENCE_FINDING_FIELDS, label, errors):
            continue
        occurrence_id = finding["occurrence_id"]
        if not isinstance(occurrence_id, str):
            errors.append(f"{label}.occurrence_id must be a string")
        else:
            actual_occurrences.append(occurrence_id)
        if not isinstance(finding["claim_focus"], str) or not finding[
            "claim_focus"
        ].strip():
            errors.append(f"{label}.claim_focus must be nonempty")
        candidates = finding["evidence_candidates"]
        explanation = finding["no_relevant_evidence_explanation"]
        if not isinstance(candidates, list):
            errors.append(f"{label}.evidence_candidates must be an array")
            continue
        if not isinstance(explanation, str):
            errors.append(f"{label}.no_relevant_evidence_explanation must be a string")
        elif not candidates and not explanation.strip():
            errors.append(f"{label} needs an explanation when evidence is empty")
        for candidate_index, candidate in enumerate(candidates):
            candidate_label = f"{label}.evidence_candidates[{candidate_index}]"
            if not exact_fields(
                candidate, EVIDENCE_CANDIDATE_FIELDS, candidate_label, errors
            ):
                continue
            page_number = candidate["page_number"]
            if not isinstance(page_number, int) or isinstance(page_number, bool):
                errors.append(f"{candidate_label}.page_number must be an integer")
                continue
            if page_number not in valid_pages:
                errors.append(f"{candidate_label}.page_number is outside the chunk")
            excerpt = candidate["excerpt"]
            if not isinstance(excerpt, str) or not excerpt.strip():
                errors.append(f"{candidate_label}.excerpt must be nonempty")
            elif normalized_text(excerpt) not in normalized_text(
                page_text(packet, page_number)
            ):
                errors.append(f"{candidate_label}.excerpt is not grounded on its page")
            for field in ("section_or_heading", "relevance"):
                if not isinstance(candidate[field], str):
                    errors.append(f"{candidate_label}.{field} must be a string")
            if candidate["stance"] not in EVIDENCE_STANCES:
                errors.append(f"{candidate_label}.stance is invalid")
    if actual_occurrences != expected_occurrences:
        errors.append(
            "occurrence finding order/identity differs: "
            f"expected={expected_occurrences} actual={actual_occurrences}"
        )
    return errors


def evidence_candidate_index(
    evidence_records: list[dict[str, Any]],
) -> set[tuple[str, int, str, str]]:
    index: set[tuple[str, int, str, str]] = set()
    for record in evidence_records:
        chunk_id = str(record["chunk_id"])
        for finding in record["occurrence_findings"]:
            for candidate in finding["evidence_candidates"]:
                index.add(
                    (
                        chunk_id,
                        int(candidate["page_number"]),
                        str(candidate["section_or_heading"]),
                        normalized_text(str(candidate["excerpt"])),
                    )
                )
    return index


def validate_review_record(
    value: Any,
    source_plan: dict[str, Any],
    evidence_records: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if not exact_fields(value, REVIEW_TOP_LEVEL_FIELDS, "review record", errors):
        return errors
    expected_key = str(source_plan["citation_key"])
    if value["schema_version"] != 1:
        errors.append("review schema_version must equal 1")
    if value["review_type"] != "citation_review":
        errors.append("review_type differs")
    if value["citation_key"] != expected_key:
        errors.append("review citation_key differs from source plan")
    identity = value["source_identity"]
    if exact_fields(identity, {"status", "rationale"}, "source_identity", errors):
        if identity["status"] not in {
            "match",
            "probable_match",
            "ambiguous",
            "mismatch",
        }:
            errors.append("source_identity.status is invalid")
        if not isinstance(identity["rationale"], str) or not identity[
            "rationale"
        ].strip():
            errors.append("source_identity.rationale must be nonempty")
    if not isinstance(value["source_contribution_summary"], str) or not value[
        "source_contribution_summary"
    ].strip():
        errors.append("source_contribution_summary must be nonempty")
    if not isinstance(value["overall_notes"], str):
        errors.append("overall_notes must be a string")

    expected_occurrences = [
        str(item["occurrence_id"]) for item in source_plan["target_occurrences"]
    ]
    assessments = value["occurrence_assessments"]
    if not isinstance(assessments, list):
        errors.append("occurrence_assessments must be an array")
        return errors
    candidates = evidence_candidate_index(evidence_records)
    actual_occurrences: list[str] = []
    for index, assessment in enumerate(assessments):
        label = f"occurrence_assessments[{index}]"
        if not exact_fields(assessment, ASSESSMENT_FIELDS, label, errors):
            continue
        occurrence_id = assessment["occurrence_id"]
        if isinstance(occurrence_id, str):
            actual_occurrences.append(occurrence_id)
        else:
            errors.append(f"{label}.occurrence_id must be a string")
        for field in ("claim_summary", "source_relevant_contribution"):
            if not isinstance(assessment[field], str) or not assessment[field].strip():
                errors.append(f"{label}.{field} must be nonempty")
        if not isinstance(assessment["limitation_or_correction"], str):
            errors.append(f"{label}.limitation_or_correction must be a string")
        support_class = assessment["support_class"]
        if support_class not in SUPPORT_CLASSES:
            errors.append(f"{label}.support_class is invalid")
        score = assessment["citation_appropriateness_score"]
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 10:
            errors.append(f"{label}.citation_appropriateness_score is invalid")
        confidence = assessment["confidence"]
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            errors.append(f"{label}.confidence is invalid")
        evidence = assessment["evidence"]
        if not isinstance(evidence, list):
            errors.append(f"{label}.evidence must be an array")
            continue
        if support_class != "not_verifiable" and not evidence:
            errors.append(f"{label} needs grounded evidence for its support class")
        for evidence_index, item in enumerate(evidence):
            item_label = f"{label}.evidence[{evidence_index}]"
            if not exact_fields(item, REVIEW_EVIDENCE_FIELDS, item_label, errors):
                continue
            try:
                signature = (
                    str(item["chunk_id"]),
                    int(item["page_number"]),
                    str(item["section_or_heading"]),
                    normalized_text(str(item["excerpt"])),
                )
            except (TypeError, ValueError):
                errors.append(f"{item_label} has invalid locator types")
                continue
            if signature not in candidates:
                errors.append(f"{item_label} was not copied from chunk evidence")
    if actual_occurrences != expected_occurrences:
        errors.append(
            "assessment order/identity differs: "
            f"expected={expected_occurrences} actual={actual_occurrences}"
        )
    self_check = value["self_check"]
    if exact_fields(
        self_check,
        {"all_occurrences_reviewed", "all_evidence_grounded", "uncertainty_notes"},
        "self_check",
        errors,
    ):
        if self_check["all_occurrences_reviewed"] is not True:
            errors.append("self_check.all_occurrences_reviewed must be true")
        if self_check["all_evidence_grounded"] is not True:
            errors.append("self_check.all_evidence_grounded must be true")
        if not isinstance(self_check["uncertainty_notes"], str):
            errors.append("self_check.uncertainty_notes must be a string")
    return errors

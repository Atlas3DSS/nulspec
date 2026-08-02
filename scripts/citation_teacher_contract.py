#!/usr/bin/env python3
"""Fail-closed contracts for the 2607.17674 citation teacher hierarchy."""

from __future__ import annotations

from typing import Any


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate the bounded JSON-Schema subset used by the frozen contracts."""

    errors: list[str] = []
    expected = schema.get("type")
    expected_types = [expected] if isinstance(expected, str) else expected
    if isinstance(expected_types, list) and not any(
        isinstance(item, str) and _matches_type(value, item) for item in expected_types
    ):
        return [f"{path}: expected type {expected_types}, got {type(value).__name__}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is outside enum")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key!r}")
        for key, child in properties.items():
            if key in value and isinstance(child, dict):
                errors.extend(validate_schema(value[key], child, f"{path}.{key}"))

    if isinstance(value, list):
        minimum = schema.get("minItems")
        maximum = schema.get("maxItems")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{path}: has {len(value)} items, minimum is {minimum}")
        if isinstance(maximum, int) and len(value) > maximum:
            errors.append(f"{path}: has {len(value)} items, maximum is {maximum}")
        child = schema.get("items")
        if isinstance(child, dict):
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, child, f"{path}[{index}]"))

    if isinstance(value, str):
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{path}: string is shorter than {minimum}")
        if isinstance(maximum, int) and len(value) > maximum:
            errors.append(f"{path}: string is longer than {maximum}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{path}: value is below {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{path}: value is above {maximum}")
    return errors


def packet_identities(packet: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    """Index the citation, occurrence, and chunk identities in a teacher packet."""

    identities: dict[str, dict[str, set[str]]] = {}
    sources = packet.get("sources")
    if not isinstance(sources, list):
        return identities
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("citation_key"), str):
            continue
        key = source["citation_key"]
        occurrence_ids: set[str] = set()
        review = source.get("citation_review")
        if isinstance(review, dict):
            assessments = review.get("occurrence_assessments")
            if isinstance(assessments, list):
                for assessment in assessments:
                    if isinstance(assessment, dict) and isinstance(
                        assessment.get("occurrence_id"), str
                    ):
                        occurrence_ids.add(assessment["occurrence_id"])
        chunk_ids = {
            chunk["chunk_id"]
            for chunk in source.get("evidence_chunk_reviews", [])
            if isinstance(chunk, dict) and isinstance(chunk.get("chunk_id"), str)
        }
        identities[key] = {"occurrences": occurrence_ids, "chunks": chunk_ids}
    return identities


def validate_teacher_record(
    record: dict[str, Any], packet: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    errors = validate_schema(record, schema)
    if errors:
        return errors
    coverage = record["coverage_confirmation"]
    expected = packet.get("population_summary", {})
    for key in ("source_reviews", "citation_occurrences", "evidence_chunks"):
        if coverage[key] != expected.get(key):
            errors.append(f"$.coverage_confirmation.{key}: differs from packet")
    if coverage["inspected_all_records"] is not True:
        errors.append("$.coverage_confirmation.inspected_all_records: must be true")

    identities = packet_identities(packet)
    for index, finding in enumerate(record["findings"]):
        root = f"$.findings[{index}]"
        key = finding["citation_key"]
        if key not in identities:
            errors.append(f"{root}.citation_key: absent from packet")
            continue
        occurrence = finding["occurrence_id"]
        chunk = finding["chunk_id"]
        if occurrence and occurrence not in identities[key]["occurrences"]:
            errors.append(f"{root}.occurrence_id: absent from cited source")
        if chunk and chunk not in identities[key]["chunks"]:
            errors.append(f"{root}.chunk_id: absent from cited source")
    return errors


def validate_codex_record(
    record: dict[str, Any],
    packet: dict[str, Any],
    teacher_records: dict[str, dict[str, Any]],
    schema: dict[str, Any],
) -> list[str]:
    errors = validate_schema(record, schema)
    if errors:
        return errors
    assessments = {item["teacher"]: item for item in record["teacher_assessments"]}
    if set(assessments) != {"glm", "kimi"}:
        errors.append("$.teacher_assessments: must contain glm and kimi exactly once")
    for teacher, source in teacher_records.items():
        assessment = assessments.get(teacher)
        if assessment is None:
            continue
        if assessment["execution_chain_valid"] is not True:
            errors.append(f"$.teacher_assessments[{teacher}]: valid chain marked invalid")
        if assessment["scientific_assessment"] != source["overall_assessment"]:
            errors.append(
                f"$.teacher_assessments[{teacher}].scientific_assessment: "
                "does not preserve the teacher decision"
            )
        if assessment["qwen_quality_score"] != source["qwen_reviewer_quality_score"]:
            errors.append(
                f"$.teacher_assessments[{teacher}].qwen_quality_score: "
                "does not preserve the teacher score"
            )

    glm = teacher_records.get("glm", {})
    kimi = teacher_records.get("kimi", {})
    obvious_disagreement = (
        glm.get("overall_assessment") != kimi.get("overall_assessment")
        or glm.get("qwen_reviewer_quality_score")
        != kimi.get("qwen_reviewer_quality_score")
        or glm.get("findings") != kimi.get("findings")
    )
    if obvious_disagreement and record["teacher_disagreement_present"] is not True:
        errors.append("$.teacher_disagreement_present: collapsed a teacher disagreement")
    if record["teacher_disagreement_present"] and not record["teacher_disagreements"]:
        errors.append("$.teacher_disagreements: disagreement flag requires an entry")

    identities = packet_identities(packet)
    for index, item in enumerate(record["citation_adjudications"]):
        root = f"$.citation_adjudications[{index}]"
        key = item["citation_key"]
        occurrence = item["occurrence_id"]
        if key not in identities:
            errors.append(f"{root}.citation_key: absent from packet")
        elif occurrence and occurrence not in identities[key]["occurrences"]:
            errors.append(f"{root}.occurrence_id: absent from cited source")
    return errors

#!/usr/bin/env python3
"""Project a completed Qwen citation trace into the frozen teacher boundary."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
TEACHER_PROTOCOL = WORKSPACE / "protocols" / "2607.17674" / "CITATION_TEACHER_PROTOCOL.md"
TEACHER_CONFIG = (
    WORKSPACE / "protocols" / "2607.17674" / "citation_teacher_config.v1.0.0.json"
)
TEACHER_SCHEMA = (
    WORKSPACE / "protocols" / "2607.17674" / "citation_teacher_audit.schema.json"
)
CODEX_SCHEMA = (
    WORKSPACE / "protocols" / "2607.17674" / "citation_codex_adjudication.schema.json"
)


class ProjectionError(RuntimeError):
    """Raised when a Qwen trace cannot cross the teacher evidence boundary."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProjectionError(f"expected JSON object: {path}")
    return value


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def accepted_record(stage_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    accepted = load_object(stage_root / "accepted.json")
    parsed_path = stage_root / str(accepted["parsed_relative_path"])
    if sha256_file(parsed_path) != accepted["parsed_sha256"]:
        raise ProjectionError(f"accepted parsed hash differs: {stage_root}")
    parsed = load_object(parsed_path)
    attempt = load_object(stage_root / str(accepted["attempt_id"]) / "attempt-record.json")
    if attempt.get("valid") is not True:
        raise ProjectionError(f"accepted attempt is not valid: {stage_root}")
    return parsed, attempt


def execution_summary(source_root: Path) -> dict[str, Any]:
    stages = sorted(path.parent for path in source_root.glob("evidence/*/accepted.json"))
    stages.append(source_root / "synthesis")
    attempt_records: list[dict[str, Any]] = []
    accepted_attempts: list[str] = []
    for stage in stages:
        accepted = load_object(stage / "accepted.json")
        accepted_attempts.append(str(accepted["attempt_id"]))
        for attempt_path in sorted(stage.glob("attempt-*/attempt-record.json")):
            attempt_records.append(load_object(attempt_path))
    invalid = [record for record in attempt_records if record.get("valid") is not True]
    error_types = Counter()
    for record in invalid:
        for error in record.get("errors", []):
            error_types[str(error).split(":", maxsplit=1)[0]] += 1
    return {
        "logical_calls": len(stages),
        "attempts": len(attempt_records),
        "invalid_attempts": len(invalid),
        "accepted_attempt_ids": accepted_attempts,
        "invalid_error_type_counts": dict(sorted(error_types.items())),
    }


def build_source_record(source_root: Path) -> dict[str, Any]:
    synthesis_packet = load_object(source_root / "synthesis-packet.json")
    final_review = load_object(source_root / "final-review.json")
    key = source_root.name
    if final_review.get("citation_key") != key:
        raise ProjectionError(f"final review identity differs: {key}")
    evidence_records: list[dict[str, Any]] = []
    for stage in sorted(
        (source_root / "evidence").glob("chunk-*"),
        key=lambda path: path.name,
    ):
        record, _ = accepted_record(stage)
        if record.get("citation_key") != key:
            raise ProjectionError(f"evidence review identity differs: {stage}")
        evidence_records.append(record)
    if not evidence_records:
        raise ProjectionError(f"source has no evidence reviews: {key}")
    final_from_stage, _ = accepted_record(source_root / "synthesis")
    if final_from_stage != final_review:
        raise ProjectionError(f"final review copy differs from accepted stage: {key}")
    source_identity = synthesis_packet.get("source_identity")
    if not isinstance(source_identity, dict):
        raise ProjectionError(f"source identity is absent: {key}")
    allowed_identity_fields = {
        "citation_key",
        "title",
        "authors",
        "year",
        "doi",
        "eprint",
        "bibliographic_source_url",
        "selected_source_url",
    }
    if set(source_identity) != allowed_identity_fields:
        raise ProjectionError(f"source identity crossed its field boundary: {key}")
    return {
        "citation_key": key,
        "source_identity": source_identity,
        "evidence_chunk_reviews": evidence_records,
        "citation_review": final_review,
        "execution_summary": execution_summary(source_root),
    }


def population_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    support_classes: Counter[str] = Counter()
    identity_statuses: Counter[str] = Counter()
    score_histogram: Counter[int] = Counter()
    confidence_values: list[float] = []
    evidence_candidates = 0
    empty_chunk_occurrence_findings = 0
    attempts = 0
    invalid_attempts = 0
    occurrence_ids: set[str] = set()
    chunk_ids: set[str] = set()
    for source in sources:
        review = source["citation_review"]
        identity_statuses[str(review["source_identity"]["status"])] += 1
        for assessment in review["occurrence_assessments"]:
            occurrence_id = str(assessment["occurrence_id"])
            if occurrence_id in occurrence_ids:
                raise ProjectionError(f"duplicate occurrence review: {occurrence_id}")
            occurrence_ids.add(occurrence_id)
            support_classes[str(assessment["support_class"])] += 1
            score_histogram[int(assessment["citation_appropriateness_score"])] += 1
            confidence_values.append(float(assessment["confidence"]))
        for chunk in source["evidence_chunk_reviews"]:
            chunk_id = str(chunk["chunk_id"])
            if chunk_id in chunk_ids:
                raise ProjectionError(f"duplicate evidence chunk: {chunk_id}")
            chunk_ids.add(chunk_id)
            for finding in chunk["occurrence_findings"]:
                candidates = finding["evidence_candidates"]
                evidence_candidates += len(candidates)
                empty_chunk_occurrence_findings += not candidates
        attempts += int(source["execution_summary"]["attempts"])
        invalid_attempts += int(source["execution_summary"]["invalid_attempts"])
    if len(sources) != 41 or len(occurrence_ids) != 74 or len(chunk_ids) != 112:
        raise ProjectionError(
            "Qwen population differs from frozen counts: "
            f"sources={len(sources)} occurrences={len(occurrence_ids)} "
            f"chunks={len(chunk_ids)}"
        )
    return {
        "source_reviews": len(sources),
        "citation_occurrences": len(occurrence_ids),
        "evidence_chunks": len(chunk_ids),
        "support_class_counts": dict(sorted(support_classes.items())),
        "source_identity_status_counts": dict(sorted(identity_statuses.items())),
        "citation_score_histogram": {
            str(score): score_histogram[score] for score in range(1, 11)
        },
        "mean_confidence": sum(confidence_values) / len(confidence_values),
        "evidence_candidate_count": evidence_candidates,
        "empty_chunk_occurrence_finding_count": empty_chunk_occurrence_findings,
        "logical_qwen_calls": 112 + 41,
        "qwen_attempts": attempts,
        "qwen_invalid_attempts": invalid_attempts,
    }


def build_packet(trace_root: Path) -> dict[str, Any]:
    completion_path = trace_root / "qwen-audit-completion.json"
    completion = load_object(completion_path)
    if completion.get("source_count") != 41:
        raise ProjectionError("Qwen audit is not complete")
    run_input = load_object(trace_root / "run-input.json")
    source_roots = sorted(
        path for path in (trace_root / "sources").iterdir() if path.is_dir()
    )
    sources = [build_source_record(path) for path in source_roots]
    summary = population_summary(sources)
    return {
        "schema_version": 1,
        "packet_type": "qwen_citation_teacher_packet",
        "paper_id": "2607.17674",
        "teacher_protocol_version": "1.0.0",
        "parent_citation_audit_version": "1.0.1",
        "protocol": {
            "boundary": (
                "Contains only Qwen reviewer records, public source identities, "
                "bounded excerpts, and aggregate execution counts. It excludes "
                "full sources, Qwen prompts/reasoning, credentials, checkpoints, "
                "and private infrastructure state."
            ),
            "score_scope": (
                "Reviewer-quality scores are conditional on this Qwen packet and "
                "automated excerpt grounding; teachers cannot establish that Qwen "
                "found every relevant passage in the unseen full sources."
            ),
            "qwen_model": {
                "logical_family": "Qwen-family 27B local GGUF",
                "gguf_basename": run_input["gguf"]["basename"],
                "gguf_sha256": run_input["gguf"]["sha256"],
                "official_upstream_release": false,
            },
            "source_qwen_completion_sha256": sha256_file(completion_path),
            "teacher_protocol_sha256": sha256_file(TEACHER_PROTOCOL),
            "teacher_config_sha256": sha256_file(TEACHER_CONFIG),
            "teacher_schema_sha256": sha256_file(TEACHER_SCHEMA),
            "codex_schema_sha256": sha256_file(CODEX_SCHEMA),
        },
        "population_summary": summary,
        "sources": sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qwen-trace-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace_root = args.qwen_trace_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    packet = build_packet(trace_root)
    write_new_json(output, packet)
    print(
        json.dumps(
            {
                "output_sha256": sha256_file(output),
                **packet["population_summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

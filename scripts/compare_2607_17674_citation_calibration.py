#!/usr/bin/env python3
"""Compare completed Qwen calibration reviews with frozen outer expectations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTATIONS = (
    WORKSPACE
    / "protocols"
    / "2607.17674"
    / "citation_calibration_expectations.v1.0.0.json"
)


class ComparisonError(RuntimeError):
    """Raised when a calibration comparison input is malformed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ComparisonError(f"could not read valid JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise ComparisonError(f"expected a JSON object: {path.name}")
    return value


def citation_key(occurrence_id: str) -> str:
    marker = ":occurrence-"
    if marker not in occurrence_id:
        raise ComparisonError(f"malformed occurrence id: {occurrence_id}")
    return occurrence_id.split(marker, 1)[0]


def require_path_outside_trace(trace_root: Path, candidate: Path) -> None:
    try:
        candidate.expanduser().resolve().relative_to(trace_root.expanduser().resolve())
    except ValueError:
        return
    raise ComparisonError("comparison output must be outside the trace root")


def compare(
    trace_root: Path,
    expectations_path: Path = DEFAULT_EXPECTATIONS,
    *,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a non-authorizing comparison against frozen expectation ranges."""

    trace_root = trace_root.resolve()
    expectations_path = expectations_path.resolve()
    if not trace_root.is_dir():
        raise ComparisonError("trace root must be an existing directory")
    expectations = load_object(expectations_path)
    expected_items = expectations.get("occurrences")
    if not isinstance(expected_items, list) or not expected_items:
        raise ComparisonError("expectations contain no occurrences")

    keys = sorted(
        {citation_key(str(item.get("occurrence_id", ""))) for item in expected_items}
    )
    completion_path = trace_root / "calibration-completion.json"
    completion = load_object(completion_path)
    completion_results = completion.get("results")
    if completion.get("phase") != "calibration" or not isinstance(
        completion_results, list
    ):
        raise ComparisonError("calibration completion record is malformed")
    completion_by_key: dict[str, dict[str, Any]] = {}
    for item in completion_results:
        if not isinstance(item, dict) or not isinstance(item.get("citation_key"), str):
            raise ComparisonError("calibration completion result is malformed")
        key = item["citation_key"]
        if key in completion_by_key:
            raise ComparisonError("calibration completion contains a duplicate source")
        completion_by_key[key] = item
    if set(completion_by_key) != set(keys):
        raise ComparisonError("calibration completion source set differs")

    final_reviews: dict[str, dict[str, Any]] = {}
    final_review_bindings: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    for key in keys:
        path = trace_root / "sources" / key / "final-review.json"
        if not path.is_file():
            missing_sources.append(key)
            continue
        completion_item = completion_by_key[key]
        expected_relative_path = f"sources/{key}/final-review.json"
        if completion_item.get(
            "final_review_relative_path"
        ) != expected_relative_path or completion_item.get(
            "final_review_sha256"
        ) != sha256_file(path):
            raise ComparisonError(f"final review differs from completion: {key}")
        review = load_object(path)
        if review.get("citation_key") != key:
            raise ComparisonError(f"final review citation key differs: {key}")
        assessments = review.get("occurrence_assessments")
        if not isinstance(assessments, list):
            raise ComparisonError(f"final review lacks occurrence assessments: {key}")
        final_reviews[key] = review
        final_review_bindings.append(
            {
                "citation_key": key,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    comparisons: list[dict[str, Any]] = []
    missing_occurrences: list[str] = []
    for expected in expected_items:
        occurrence_id = str(expected.get("occurrence_id", ""))
        key = citation_key(occurrence_id)
        review = final_reviews.get(key)
        if review is None:
            missing_occurrences.append(occurrence_id)
            continue
        matches = [
            item
            for item in review["occurrence_assessments"]
            if item.get("occurrence_id") == occurrence_id
        ]
        if len(matches) != 1:
            missing_occurrences.append(occurrence_id)
            continue
        observed = matches[0]
        observed_class = observed.get("support_class")
        observed_score = observed.get("citation_appropriateness_score")
        acceptable_classes = expected.get("acceptable_support_classes")
        minimum = expected.get("acceptable_score_min")
        maximum = expected.get("acceptable_score_max")
        if (
            not isinstance(acceptable_classes, list)
            or not all(isinstance(value, str) for value in acceptable_classes)
            or not isinstance(minimum, int)
            or not isinstance(maximum, int)
            or not isinstance(observed_score, int)
        ):
            raise ComparisonError(f"invalid comparison fields: {occurrence_id}")
        comparisons.append(
            {
                "occurrence_id": occurrence_id,
                "expected": {
                    "acceptable_support_classes": acceptable_classes,
                    "acceptable_score_min": minimum,
                    "acceptable_score_max": maximum,
                    "watch_for": expected.get("watch_for", ""),
                },
                "observed": {
                    "support_class": observed_class,
                    "citation_appropriateness_score": observed_score,
                    "confidence": observed.get("confidence"),
                    "limitation_or_correction": observed.get(
                        "limitation_or_correction", ""
                    ),
                },
                "support_class_within_expected_set": (
                    observed_class in acceptable_classes
                ),
                "score_within_expected_range": minimum <= observed_score <= maximum,
            }
        )

    expected_identity = expectations.get("source_identity_expectation")
    identity_comparisons = [
        {
            "citation_key": key,
            "expected_status": expected_identity,
            "observed_status": final_reviews[key]
            .get("source_identity", {})
            .get("status"),
            "matches": final_reviews[key].get("source_identity", {}).get("status")
            == expected_identity,
        }
        for key in sorted(final_reviews)
    ]
    complete = not missing_sources and not missing_occurrences
    summary = {
        "expected_source_count": len(keys),
        "observed_source_count": len(final_reviews),
        "expected_occurrence_count": len(expected_items),
        "observed_occurrence_count": len(comparisons),
        "support_class_within_expected_count": sum(
            item["support_class_within_expected_set"] for item in comparisons
        ),
        "score_within_expected_count": sum(
            item["score_within_expected_range"] for item in comparisons
        ),
        "identity_match_count": sum(item["matches"] for item in identity_comparisons),
        "comparison_complete": complete,
    }
    return {
        "schema_version": 1,
        "paper_id": expectations.get("paper_id"),
        "created_at_utc": created_at_utc or utc_now(),
        "trace_root_basename": trace_root.name,
        "expectations": {
            "basename": expectations_path.name,
            "sha256": sha256_file(expectations_path),
            "created_before_qwen_review": expectations.get(
                "created_before_qwen_review"
            ),
        },
        "final_review_bindings": final_review_bindings,
        "identity_comparisons": identity_comparisons,
        "occurrence_comparisons": comparisons,
        "missing_sources": missing_sources,
        "missing_occurrences": missing_occurrences,
        "summary": summary,
        "interpretation": "Expectation mismatches trigger documented source-based adjudication; they are not automatic scientific vetoes and the expectations are not ground truth.",
        "controls": {
            "operator_read_required": True,
            "remaining_phase_automatically_authorized": False,
            "teacher_input_authorized": False,
            "publication_authorized": False,
            "training_authorized": False,
            "email_authorized": False,
        },
    }


def write_new(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path = path.expanduser().resolve()
    if not path.parent.is_dir():
        raise ComparisonError("output parent must be an existing directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise ComparisonError("refusing to overwrite an existing comparison") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--expectations", type=Path, default=DEFAULT_EXPECTATIONS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        require_path_outside_trace(args.trace_root, args.output)
        result = compare(args.trace_root, args.expectations)
        write_new(args.output, result)
    except ComparisonError as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    if not result["summary"]["comparison_complete"]:
        raise SystemExit("calibration comparison is incomplete")


if __name__ == "__main__":
    main()

import importlib.util
import json
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "compare_2607_17674_citation_calibration.py"
SPEC = importlib.util.spec_from_file_location(
    "compare_2607_17674_citation_calibration", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def expectations() -> dict:
    return {
        "paper_id": "2607.17674",
        "created_before_qwen_review": True,
        "source_identity_expectation": "match",
        "occurrences": [
            {
                "occurrence_id": "sourceA:occurrence-001",
                "acceptable_support_classes": ["supports", "partially_supports"],
                "acceptable_score_min": 7,
                "acceptable_score_max": 9,
                "watch_for": "bounded caveat",
            },
            {
                "occurrence_id": "sourceB:occurrence-001",
                "acceptable_support_classes": ["partially_supports"],
                "acceptable_score_min": 5,
                "acceptable_score_max": 7,
                "watch_for": "indirect use",
            },
        ],
    }


def review(key: str, support_class: str, score: int) -> dict:
    return {
        "citation_key": key,
        "source_identity": {"status": "match"},
        "occurrence_assessments": [
            {
                "occurrence_id": f"{key}:occurrence-001",
                "support_class": support_class,
                "citation_appropriateness_score": score,
                "confidence": 0.8,
                "limitation_or_correction": "bounded",
            }
        ],
    }


def write_completion(trace: Path, keys: list[str]) -> None:
    results = []
    for key in keys:
        path = trace / "sources" / key / "final-review.json"
        results.append(
            {
                "citation_key": key,
                "final_review_relative_path": f"sources/{key}/final-review.json",
                "final_review_sha256": MODULE.sha256_file(path),
            }
        )
    write_json(
        trace / "calibration-completion.json",
        {"phase": "calibration", "results": results},
    )


def test_compare_reports_matches_and_mismatches_without_authorizing(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "attempt"
    expectation_path = tmp_path / "expectations.json"
    write_json(expectation_path, expectations())
    write_json(
        trace / "sources" / "sourceA" / "final-review.json",
        review("sourceA", "supports", 8),
    )
    write_json(
        trace / "sources" / "sourceB" / "final-review.json",
        review("sourceB", "supports", 9),
    )
    write_completion(trace, ["sourceA", "sourceB"])

    result = MODULE.compare(
        trace,
        expectation_path,
        created_at_utc="2026-08-02T00:00:00Z",
    )

    assert result["summary"] == {
        "expected_source_count": 2,
        "observed_source_count": 2,
        "expected_occurrence_count": 2,
        "observed_occurrence_count": 2,
        "support_class_within_expected_count": 1,
        "score_within_expected_count": 1,
        "identity_match_count": 2,
        "comparison_complete": True,
    }
    assert result["controls"]["remaining_phase_automatically_authorized"] is False
    mismatch = result["occurrence_comparisons"][1]
    assert mismatch["support_class_within_expected_set"] is False
    assert mismatch["score_within_expected_range"] is False


def test_compare_rejects_trace_without_terminal_calibration(tmp_path: Path) -> None:
    trace = tmp_path / "attempt"
    trace.mkdir()
    expectation_path = tmp_path / "expectations.json"
    write_json(expectation_path, expectations())

    try:
        MODULE.compare(trace, expectation_path)
    except MODULE.ComparisonError as error:
        assert "calibration-completion.json" in str(error)
    else:
        raise AssertionError("nonterminal calibration was not rejected")


def test_compare_rejects_output_inside_trace(tmp_path: Path) -> None:
    trace = tmp_path / "attempt"
    trace.mkdir()

    try:
        MODULE.require_path_outside_trace(trace, trace / "comparison.json")
    except MODULE.ComparisonError as error:
        assert "outside" in str(error)
    else:
        raise AssertionError("in-trace comparison output was not rejected")


def test_write_new_is_append_only(tmp_path: Path) -> None:
    output = tmp_path / "comparison.json"
    MODULE.write_new(output, {"first": True})

    try:
        MODULE.write_new(output, {"second": True})
    except MODULE.ComparisonError as error:
        assert "refusing to overwrite" in str(error)
    else:
        raise AssertionError("comparison overwrite was not rejected")

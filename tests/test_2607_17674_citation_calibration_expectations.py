from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
PROTOCOL = WORKSPACE / "protocols/2607.17674"


def load(name: str) -> dict:
    return json.loads((PROTOCOL / name).read_text())


def test_blind_calibration_expectations_cover_exact_registered_occurrences() -> None:
    expectations = load("citation_calibration_expectations.v1.0.0.json")
    audit = load("citation_audit_config.v1.0.1.json")
    inventory = load("citation_inventory.json")
    calibration = set(audit["calibration_keys"])
    expected_ids = {
        f"{record['key']}:occurrence-{index:03d}"
        for record in inventory["records"]
        if record["key"] in calibration
        for index, _ in enumerate(record["occurrences"], start=1)
    }
    observed = {item["occurrence_id"] for item in expectations["occurrences"]}
    assert observed == expected_ids
    assert len(observed) == 10


def test_calibration_ranges_use_registered_classes_and_valid_scores() -> None:
    expectations = load("citation_calibration_expectations.v1.0.0.json")
    schema = load("citation_review.schema.json")
    classes = set(
        schema["properties"]["occurrence_assessments"]["items"]["properties"][
            "support_class"
        ]["enum"]
    )
    for item in expectations["occurrences"]:
        assert set(item["acceptable_support_classes"]) <= classes
        assert 1 <= item["acceptable_score_min"] <= item["acceptable_score_max"] <= 10
        assert item["watch_for"].strip()

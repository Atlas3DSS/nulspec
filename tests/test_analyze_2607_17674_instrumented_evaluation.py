from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "analyze_2607_17674_instrumented_evaluation.py"
SPEC = importlib.util.spec_from_file_location(
    "analyze_2607_17674_instrumented_evaluation",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_trace(
    root: Path,
    *,
    mode: str,
    fidelity_outcomes: list[str],
    analogical_decisions: list[dict[str, bool]],
) -> Path:
    root.mkdir()
    start = {
        "schema_version": 1,
        "instrumentation_version": "1.0.1",
        "rng_mode": mode,
        "seed": 314159,
        "batch_size": 2,
        "num_pairs": len(analogical_decisions),
        "checkpoint_sha256": "a" * 64,
        "factorization_config_sha256": "b" * 64,
        "workspace_revision": "d" * 40,
        "workspace_tracked_clean": True,
        "upstream_revision": "c" * 40,
        "upstream_tracked_clean": True,
        "device": "cuda",
        "environment": {"device": "cuda", "gpu": {"name": "test"}},
    }
    fidelity_rows = [
        {
            "index": index,
            "example_id": index,
            "task_name": "task-a",
            "outcome": outcome,
        }
        for index, outcome in enumerate(fidelity_outcomes)
    ]
    analogical_rows = [
        {
            "pair_index": index,
            "source_example_id": index,
            "target_example_id": index + 10,
            "task_name": "task-a",
            "source_strategies": ["a"],
            "target_strategies": (["a"] if decisions["released_overlap"] else ["b"]),
            "decisions": decisions,
        }
        for index, decisions in enumerate(analogical_decisions)
    ]
    write_json(root / "run.start.json", start)
    write_jsonl(root / "fidelity.jsonl", fidelity_rows)
    write_jsonl(root / "analogical.jsonl", analogical_rows)
    metrics = {
        **MODULE.fidelity_summary(fidelity_rows),
        **MODULE.analogical_summary(analogical_rows),
        "rng_mode": mode,
    }
    write_json(root / "metrics.json", metrics)
    hashes = {
        name: sha256(root / name)
        for name in (
            "run.start.json",
            "fidelity.jsonl",
            "analogical.jsonl",
            "metrics.json",
        )
    }
    write_json(
        root / "run.complete.json",
        {**start, "status": "complete", "artifact_sha256": hashes},
    )
    return root


def decisions(value: bool) -> dict[str, bool]:
    return {
        "released_overlap": value,
        "nonempty_set_equality": value,
        "unique_only": value,
    }


def test_trace_validation_recomputes_metrics_and_hashes(tmp_path: Path) -> None:
    trace = make_trace(
        tmp_path / "released",
        mode="released-reseed",
        fidelity_outcomes=["unique_strategy", "parse_failure"],
        analogical_decisions=[decisions(True), decisions(False)],
    )
    validated = MODULE.validate_trace_dir(trace, expected_mode="released-reseed")
    assert validated["metrics"]["distributional_fidelity"] == 0.5
    assert validated["metrics"]["analogical_consistency"] == 0.5


def test_trace_validation_rejects_tampering(tmp_path: Path) -> None:
    trace = make_trace(
        tmp_path / "released",
        mode="released-reseed",
        fidelity_outcomes=["unique_strategy"],
        analogical_decisions=[decisions(True)],
    )
    with (trace / "fidelity.jsonl").open("a") as handle:
        handle.write("{}\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        MODULE.validate_trace_dir(trace, expected_mode="released-reseed")


def test_analysis_requires_primary_parity_and_reports_paired_change(
    tmp_path: Path,
) -> None:
    released = make_trace(
        tmp_path / "released",
        mode="released-reseed",
        fidelity_outcomes=["unique_strategy", "parse_failure"],
        analogical_decisions=[decisions(True), decisions(False)],
    )
    advancing = make_trace(
        tmp_path / "advancing",
        mode="advancing",
        fidelity_outcomes=["unique_strategy", "ambiguous_strategy"],
        analogical_decisions=[decisions(True), decisions(True)],
    )
    primary = tmp_path / "primary.json"
    write_json(
        primary,
        {"distributional_fidelity": 0.5, "analogical_consistency": 0.5},
    )
    payload = MODULE.build_analysis(
        primary_metrics_path=primary,
        released_dir=released,
        advancing_dir=advancing,
        repetitions=100,
        bootstrap_seed=7,
    )
    assert payload["primary_parity"]["exact_match"] is True
    assert (
        payload["paired_advancing_minus_released"]["distributional_fidelity"][
            "estimate_advancing_minus_released"
        ]
        == 0.5
    )
    assert (
        payload["paired_advancing_minus_released"]["analogical_released_overlap"][
            "estimate_advancing_minus_released"
        ]
        == 0.5
    )

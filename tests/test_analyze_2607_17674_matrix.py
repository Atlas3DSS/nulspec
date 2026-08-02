from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "analyze_2607_17674_matrix.py"
SPEC = importlib.util.spec_from_file_location("analyze_2607_17674_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_empty_matrix_is_deferred(tmp_path: Path) -> None:
    payload = ANALYZER.build_payload(tmp_path / "runs")
    assert payload["summary"]["execution_counts"]["pending"] == 4
    assert (
        payload["summary"]["released_global_token_result"]
        == "deferred_until_both_released_arms_complete"
    )


def test_completed_arm_is_validated_and_compared(tmp_path: Path) -> None:
    arm_id = "R-qwen2.5-0.5b-global-token-b0.01-warmup-s314159"
    attempt = tmp_path / "runs" / arm_id / "attempt-20260802T000000Z-deadbeef"
    metrics_path = attempt / "evaluation" / "metrics.json"
    write_json(
        metrics_path,
        {"analogical_consistency": 0.90, "distributional_fidelity": 0.98},
    )
    metrics_hash = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
    write_json(
        attempt / "evaluation.file-manifest.json",
        {"files": [{"path": "metrics.json", "sha256": metrics_hash}]},
    )
    write_json(
        attempt / "run.complete.json",
        {
            "arm_id": arm_id,
            "phase": "end",
            "protocol_version": "1.0.0",
            "exit_code": 0,
        },
    )
    write_json(
        attempt / "factorization" / "config.json",
        {
            "response_source": "benchmark",
            "task_name": "multi_task",
            "beta": 0.01,
            "seed": 314159,
            "reconstruction_family": "model_directed",
            "alpha": 0.05,
            "gamma": 0.25,
            "continuous_latent_dim": 64,
            "use_bfloat16": True,
        },
    )

    payload = ANALYZER.build_payload(tmp_path / "runs")
    row = next(row for row in payload["arms"] if row["arm_id"] == arm_id)
    assert row["execution"] == "completed"
    assert row["close_numerical_reproduction"] is True
    assert row["directional_support"] is True
    assert row["uncertainty"]["within_evaluation_95_ci"] is None


def test_hash_mismatch_invalidates_completed_attempt(tmp_path: Path) -> None:
    arm_id = "R-qwen2.5-0.5b-global-token-b0.01-warmup-s314159"
    attempt = tmp_path / "runs" / arm_id / "attempt-20260802T000000Z-deadbeef"
    write_json(
        attempt / "evaluation" / "metrics.json",
        {"analogical_consistency": 0.90, "distributional_fidelity": 0.98},
    )
    write_json(
        attempt / "evaluation.file-manifest.json",
        {"files": [{"path": "metrics.json", "sha256": "0" * 64}]},
    )
    write_json(
        attempt / "run.complete.json",
        {
            "arm_id": arm_id,
            "phase": "end",
            "protocol_version": "1.0.0",
            "exit_code": 0,
        },
    )
    write_json(
        attempt / "factorization" / "config.json",
        {
            "response_source": "benchmark",
            "task_name": "multi_task",
            "beta": 0.01,
            "seed": 314159,
            "reconstruction_family": "model_directed",
            "alpha": 0.05,
            "gamma": 0.25,
            "continuous_latent_dim": 64,
            "use_bfloat16": True,
        },
    )

    payload = ANALYZER.build_payload(tmp_path / "runs")
    row = next(row for row in payload["arms"] if row["arm_id"] == arm_id)
    assert row["execution"] == "invalid_complete"
    assert any("hash" in error for error in row["validation_errors"])

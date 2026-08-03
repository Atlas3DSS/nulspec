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


def test_recovered_evaluation_is_explicit_and_validated(tmp_path: Path) -> None:
    arm_id = "R-qwen2.5-1.5b-global-token-b0.01-warmup-s314159"
    attempt = tmp_path / "runs" / arm_id / "attempt-20260802T000000Z-deadbeef"
    recovery = (
        attempt / "evaluation-recovery-attempts" / "recovery-20260802T010000Z-deadbeef"
    )
    metrics_path = attempt / "evaluation" / "metrics.json"
    write_json(
        metrics_path,
        {"analogical_consistency": 0.89, "distributional_fidelity": 0.98},
    )
    write_json(
        attempt / "evaluation.file-manifest.json",
        {
            "files": [
                {
                    "path": "metrics.json",
                    "sha256": hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
                }
            ]
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
    write_json(attempt / "factorization" / "metrics.json", {"global_step": 782})
    write_json(
        attempt / "run.failed.json",
        {
            "arm_id": arm_id,
            "phase": "end",
            "protocol_version": "1.0.0",
            "exit_code": 141,
        },
    )
    write_json(
        recovery / "recovery.start.json",
        {
            "arm_id": arm_id,
            "phase": "start",
            "protocol_version": "1.0.0",
            "exit_code": None,
            "upstream": {"head": "0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe"},
        },
    )
    write_json(
        recovery / "recovery.complete.json",
        {
            "arm_id": arm_id,
            "phase": "end",
            "protocol_version": "1.0.0",
            "exit_code": 0,
            "upstream": {"head": "0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe"},
        },
    )
    write_json(
        recovery / "source.json",
        {
            "schema_version": 2,
            "runtime_amendment": "1.0.2",
            "recovery_attempt_id": recovery.name,
            "recovery_reason": "observer_output_transport_sigpipe",
            "scientific_change": False,
            "source_attempt": attempt.name,
            "source_exit_code": 141,
            "source_run_failed_sha256": hashlib.sha256(
                (attempt / "run.failed.json").read_bytes()
            ).hexdigest(),
            "factorization_config_sha256": hashlib.sha256(
                (attempt / "factorization" / "config.json").read_bytes()
            ).hexdigest(),
            "factorization_metrics_sha256": hashlib.sha256(
                (attempt / "factorization" / "metrics.json").read_bytes()
            ).hexdigest(),
            "checkpoint_relative_path": "factorization/checkpoints/epoch-0001.pt",
            "checkpoint_sha256": "1" * 64,
            "evaluation_config_sha256": (
                "39731599084d4c678d52edad50b301fa11716b123ce7b1041dcc64eb4f00bb0a"
            ),
            "evaluator_source_sha256": (
                "6a6d8326108f29f3e522258a731f8ebb343092a6b8a0019cf868a75b7b51b330"
            ),
        },
    )

    payload = ANALYZER.build_payload(tmp_path / "runs")
    row = next(row for row in payload["arms"] if row["arm_id"] == arm_id)
    assert row["execution"] == "completed_recovered_evaluation"
    assert row["operational_recovery"] == {
        "used": True,
        "reason": "observer_output_transport_sigpipe",
        "scientific_change": False,
        "source_failure_exit_code": 141,
    }
    assert row["close_numerical_reproduction"] is True


def test_recovered_evaluation_rejects_wrong_source_hash(tmp_path: Path) -> None:
    arm_id = "R-qwen2.5-1.5b-global-token-b0.01-warmup-s314159"
    attempt = tmp_path / "runs" / arm_id / "attempt-20260802T000000Z-deadbeef"
    recovery = (
        attempt / "evaluation-recovery-attempts" / "recovery-20260802T010000Z-deadbeef"
    )
    write_json(
        attempt / "evaluation" / "metrics.json",
        {"analogical_consistency": 0.89, "distributional_fidelity": 0.98},
    )
    metrics = attempt / "evaluation" / "metrics.json"
    write_json(
        attempt / "evaluation.file-manifest.json",
        {
            "files": [
                {
                    "path": "metrics.json",
                    "sha256": hashlib.sha256(metrics.read_bytes()).hexdigest(),
                }
            ]
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
    write_json(attempt / "factorization" / "metrics.json", {"global_step": 782})
    for path, phase, exit_code in (
        (attempt / "run.failed.json", "end", 141),
        (recovery / "recovery.start.json", "start", None),
        (recovery / "recovery.complete.json", "end", 0),
    ):
        manifest = {
            "arm_id": arm_id,
            "phase": phase,
            "protocol_version": "1.0.0",
            "exit_code": exit_code,
        }
        if path.parent == recovery:
            manifest["upstream"] = {"head": "0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe"}
        write_json(path, manifest)
    write_json(
        recovery / "source.json",
        {
            "schema_version": 2,
            "runtime_amendment": "1.0.2",
            "recovery_attempt_id": recovery.name,
            "recovery_reason": "observer_output_transport_sigpipe",
            "scientific_change": False,
            "source_attempt": attempt.name,
            "source_exit_code": 141,
            "source_run_failed_sha256": "0" * 64,
            "factorization_config_sha256": hashlib.sha256(
                (attempt / "factorization" / "config.json").read_bytes()
            ).hexdigest(),
            "factorization_metrics_sha256": hashlib.sha256(
                (attempt / "factorization" / "metrics.json").read_bytes()
            ).hexdigest(),
            "checkpoint_relative_path": "factorization/checkpoints/epoch-0001.pt",
            "checkpoint_sha256": "1" * 64,
            "evaluation_config_sha256": (
                "39731599084d4c678d52edad50b301fa11716b123ce7b1041dcc64eb4f00bb0a"
            ),
            "evaluator_source_sha256": (
                "6a6d8326108f29f3e522258a731f8ebb343092a6b8a0019cf868a75b7b51b330"
            ),
        },
    )

    payload = ANALYZER.build_payload(tmp_path / "runs")
    row = next(row for row in payload["arms"] if row["arm_id"] == arm_id)
    assert row["execution"] == "invalid_recovered_evaluation"
    assert any(
        "source_run_failed_sha256" in error for error in row["validation_errors"]
    )

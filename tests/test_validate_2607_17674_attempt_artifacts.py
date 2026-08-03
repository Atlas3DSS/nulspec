from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "validate_2607_17674_attempt_artifacts.py"
SPEC = importlib.util.spec_from_file_location("validate_primary_attempt", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


ARM_ID = "M-qwen2.5-0.5b-global-token-b0.01-warmup-s314159"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def valid_attempt(tmp_path: Path) -> Path:
    attempt = tmp_path / "attempt-20260803T000000Z-deadbeef0000"
    write_json(
        attempt / "factorization/config.json",
        {
            "response_source": "base-model",
            "task_name": "multi_task",
            "beta": 0.01,
            "seed": 314159,
            "num_epochs": 1,
        },
    )
    write_json(attempt / "factorization/metrics.json", {"global_step": 782.0})
    checkpoint = attempt / "factorization/checkpoints/epoch-0001.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    metrics = attempt / "evaluation/metrics.json"
    write_json(
        metrics,
        {"distributional_fidelity": 0.98, "analogical_consistency": 0.90},
    )
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
    return attempt


def test_preterminal_validation_accepts_full_artifact_set(tmp_path: Path) -> None:
    result = VALIDATOR.validate(valid_attempt(tmp_path), ARM_ID, False)
    assert result["valid"] is True
    assert result["errors"] == []


def test_partial_training_cannot_be_marked_valid(tmp_path: Path) -> None:
    attempt = valid_attempt(tmp_path)
    write_json(attempt / "factorization/metrics.json", {"global_step": 120.0})
    result = VALIDATOR.validate(attempt, ARM_ID, False)
    assert result["valid"] is False
    assert any("expected 782" in error for error in result["errors"])


def test_terminal_validation_requires_complete_manifest(tmp_path: Path) -> None:
    result = VALIDATOR.validate(valid_attempt(tmp_path), ARM_ID, True)
    assert result["valid"] is False
    assert "validated terminal attempt lacks run.complete.json" in result["errors"]

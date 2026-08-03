#!/usr/bin/env python3
"""Validate one primary attempt before it can be marked complete."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = WORKSPACE / "protocols" / "2607.17674"
MATRIX_PATH = PROTOCOL_ROOT / "matrix.csv"
EXPECTED_GLOBAL_STEPS = 782
REQUIRED_FILES = (
    "factorization/config.json",
    "factorization/metrics.json",
    "factorization/checkpoints/epoch-0001.pt",
    "evaluation/metrics.json",
    "evaluation.file-manifest.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return value


def registered_arm(arm_id: str) -> dict[str, str]:
    with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
        matches = [row for row in csv.DictReader(handle) if row["arm_id"] == arm_id]
    if len(matches) != 1:
        raise ValueError(
            f"expected one registered arm named {arm_id}, found {len(matches)}"
        )
    return matches[0]


def validate(attempt: Path, arm_id: str, require_terminal: bool) -> dict[str, Any]:
    errors: list[str] = []
    arm = registered_arm(arm_id)
    if attempt.name.startswith("attempt-") is False:
        errors.append("attempt directory name is not immutable-attempt shaped")
    for relative in REQUIRED_FILES:
        path = attempt / relative
        if not path.is_file():
            errors.append(f"missing {relative}")
        elif path.stat().st_size == 0:
            errors.append(f"empty {relative}")

    complete = attempt / "run.complete.json"
    failed = attempt / "run.failed.json"
    if complete.is_file() and failed.is_file():
        errors.append("attempt has both complete and failed terminal manifests")
    if require_terminal and not complete.is_file():
        errors.append("validated terminal attempt lacks run.complete.json")

    factorization_config = attempt / "factorization" / "config.json"
    factorization_metrics = attempt / "factorization" / "metrics.json"
    evaluation_metrics = attempt / "evaluation" / "metrics.json"
    evaluation_manifest = attempt / "evaluation.file-manifest.json"
    if factorization_config.is_file():
        try:
            config = load_object(factorization_config)
            expected = {
                "response_source": arm["response_source"],
                "task_name": "multi_task",
                "beta": float(arm["beta"]),
                "seed": int(arm["seed"]),
                "num_epochs": 1,
            }
            for key, value in expected.items():
                if config.get(key) != value:
                    errors.append(
                        f"factorization config {key} is {config.get(key)!r}, expected {value!r}"
                    )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"invalid factorization config: {error}")

    if factorization_metrics.is_file():
        try:
            metrics = load_object(factorization_metrics)
            global_step = metrics.get("global_step")
            if not isinstance(global_step, (int, float)) or isinstance(
                global_step, bool
            ):
                errors.append(
                    "factorization metrics global_step is missing or nonnumeric"
                )
            elif float(global_step) != float(EXPECTED_GLOBAL_STEPS):
                errors.append(
                    f"factorization global_step is {global_step}, expected {EXPECTED_GLOBAL_STEPS}"
                )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"invalid factorization metrics: {error}")

    if evaluation_metrics.is_file():
        try:
            metrics = load_object(evaluation_metrics)
            for key in ("distributional_fidelity", "analogical_consistency"):
                value = metrics.get(key)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"evaluation metric {key} is missing or nonnumeric")
                elif not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
                    errors.append(f"evaluation metric {key} is outside [0, 1]")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"invalid evaluation metrics: {error}")

    if evaluation_manifest.is_file() and evaluation_metrics.is_file():
        try:
            manifest = load_object(evaluation_manifest)
            matches = [
                item
                for item in manifest.get("files", [])
                if isinstance(item, dict) and item.get("path") == "metrics.json"
            ]
            if len(matches) != 1:
                errors.append(
                    "evaluation manifest lacks exactly one metrics.json record"
                )
            elif matches[0].get("sha256") != sha256(evaluation_metrics):
                errors.append("evaluation metrics hash differs from its file manifest")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"invalid evaluation manifest: {error}")

    return {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "arm_id": arm_id,
        "attempt_id": attempt.name,
        "required_global_steps": EXPECTED_GLOBAL_STEPS,
        "required_files": list(REQUIRED_FILES),
        "terminal_required": require_terminal,
        "valid": not errors,
        "errors": errors,
    }


def write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"refusing to overwrite validation record: {path}")
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True, type=Path)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-terminal", action="store_true")
    args = parser.parse_args()

    attempt = args.attempt.expanduser().resolve()
    result = validate(attempt, args.arm_id, args.require_terminal)
    if args.output is not None:
        write_new(args.output.expanduser().resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()

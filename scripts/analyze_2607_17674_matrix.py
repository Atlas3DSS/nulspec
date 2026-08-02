#!/usr/bin/env python3
"""Analyze arXiv:2607.17674 attempts without rewriting primary artifacts."""

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
CONFIG_PATH = PROTOCOL_ROOT / "config.json"
PROTOCOL_VERSION = "1.0.0"
REQUIRED_ATTEMPT_FILES = (
    "run.complete.json",
    "factorization/config.json",
    "evaluation/metrics.json",
    "evaluation.file-manifest.json",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_arms() -> list[dict[str, str]]:
    with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def attempts_for(arm: dict[str, str], runs_root: Path) -> list[Path]:
    arm_root = runs_root / arm["arm_id"]
    return sorted(arm_root.glob("attempt-*")) if arm_root.is_dir() else []


def terminal_attempt(
    arm: dict[str, str], runs_root: Path
) -> tuple[str, Path | None]:
    attempts = attempts_for(arm, runs_root)
    completed = [path for path in attempts if (path / "run.complete.json").is_file()]
    if completed:
        return "completed", completed[-1]
    failed = [path for path in attempts if (path / "run.failed.json").is_file()]
    if failed:
        return "failed", failed[-1]
    if attempts:
        return "unterminated", attempts[-1]
    return "pending", None


def validate_file_manifest(attempt: Path, metrics_path: Path) -> list[str]:
    violations: list[str] = []
    manifest = load_json(attempt / "evaluation.file-manifest.json")
    matches = [
        record
        for record in manifest.get("files", [])
        if record.get("path") == "metrics.json"
    ]
    if len(matches) != 1:
        return ["evaluation manifest does not contain exactly one metrics.json"]
    if matches[0].get("sha256") != sha256(metrics_path):
        violations.append("evaluation metrics hash does not match its file manifest")
    return violations


def validate_primary_artifacts(
    arm: dict[str, str], attempt: Path
) -> tuple[list[str], dict[str, float] | None]:
    violations = [
        f"missing {relative}"
        for relative in REQUIRED_ATTEMPT_FILES
        if not (attempt / relative).is_file()
    ]
    if violations:
        return violations, None

    run_manifest = load_json(attempt / "run.complete.json")
    expected_manifest = {
        "arm_id": arm["arm_id"],
        "phase": "end",
        "protocol_version": PROTOCOL_VERSION,
        "exit_code": 0,
    }
    for key, expected in expected_manifest.items():
        if run_manifest.get(key) != expected:
            violations.append(
                f"run manifest {key} is {run_manifest.get(key)!r}, "
                f"expected {expected!r}"
            )

    factorization = load_json(attempt / "factorization/config.json")
    expected_factorization: dict[str, Any] = {
        "response_source": arm["response_source"],
        "task_name": "multi_task",
        "beta": float(arm["beta"]),
        "seed": int(arm["seed"]),
        "reconstruction_family": "model_directed",
        "alpha": 0.05,
        "gamma": 0.25,
        "continuous_latent_dim": 64,
        "use_bfloat16": True,
    }
    for key, expected in expected_factorization.items():
        if factorization.get(key) != expected:
            violations.append(
                f"factorization config {key} is {factorization.get(key)!r}, "
                f"expected {expected!r}"
            )

    metrics_path = attempt / "evaluation/metrics.json"
    raw_metrics = load_json(metrics_path)
    metrics: dict[str, float] = {}
    for key in ("distributional_fidelity", "analogical_consistency"):
        value = raw_metrics.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            violations.append(f"evaluation metric {key} is missing or nonnumeric")
            continue
        numeric = float(value)
        if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
            violations.append(f"evaluation metric {key} is outside [0, 1]")
            continue
        metrics[key] = numeric

    violations.extend(validate_file_manifest(attempt, metrics_path))
    if violations or len(metrics) != 2:
        return violations, None
    return [], metrics


def complete_arm_result(
    arm: dict[str, str], attempt: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    violations, metrics = validate_primary_artifacts(arm, attempt)
    if violations or metrics is None:
        return {
            **arm,
            "execution": "invalid_complete",
            "attempt_id": attempt.name,
            "validation_errors": violations,
        }

    reference = protocol["digitized_figure_3"][arm["model"]]
    tolerance = float(
        protocol["digitized_figure_3"]["close_reproduction_absolute_tolerance"]
    )
    observed = {
        "distributional_fidelity": metrics["distributional_fidelity"],
        "strategy_alignment": metrics["analogical_consistency"],
    }
    digitized = {
        "distributional_fidelity": float(
            reference["global+token_distributional_fidelity"]
        ),
        "strategy_alignment": float(reference["global+token_strategy_alignment"]),
    }
    absolute_differences = {
        key: abs(observed[key] - digitized[key]) for key in observed
    }
    close_by_metric = {
        key: difference <= tolerance
        for key, difference in absolute_differences.items()
    }
    metrics_path = attempt / "evaluation/metrics.json"
    return {
        **arm,
        "execution": "completed",
        "attempt_id": attempt.name,
        "observed": observed,
        "digitized_reference": digitized,
        "absolute_difference": absolute_differences,
        "close_reproduction_tolerance": tolerance,
        "close_reproduction_by_metric": close_by_metric,
        "close_numerical_reproduction": all(close_by_metric.values()),
        "directional_thresholds": {
            "distributional_fidelity": 0.95,
            "strategy_alignment": 0.80,
        },
        "directional_support": (
            observed["distributional_fidelity"] >= 0.95
            and observed["strategy_alignment"] >= 0.80
        ),
        "uncertainty": {
            "within_evaluation_95_ci": None,
            "status": "unavailable_from_released_aggregate_only_output",
            "fidelity_generations": 10_000,
            "analogical_pairs": int(protocol["evaluation"]["num_pairs"]),
            "fresh_training_or_decoding_variance": "not_identified",
        },
        "artifact_sha256": {
            "run_manifest": sha256(attempt / "run.complete.json"),
            "factorization_config": sha256(attempt / "factorization/config.json"),
            "evaluation_metrics": sha256(metrics_path),
            "evaluation_file_manifest": sha256(
                attempt / "evaluation.file-manifest.json"
            ),
        },
    }


def arm_result(
    arm: dict[str, str], runs_root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    execution, attempt = terminal_attempt(arm, runs_root)
    if execution == "completed" and attempt is not None:
        return complete_arm_result(arm, attempt, protocol)
    result: dict[str, Any] = {**arm, "execution": execution}
    if attempt is not None:
        result["attempt_id"] = attempt.name
        terminal_name = "run.failed.json" if execution == "failed" else "run.start.json"
        terminal_path = attempt / terminal_name
        if terminal_path.is_file():
            result["terminal_manifest_sha256"] = sha256(terminal_path)
    return result


def released_result_assessment(rows: list[dict[str, Any]]) -> str:
    released = [row for row in rows if row["track"] == "R"]
    if any(row["execution"] in {"failed", "invalid_complete"} for row in released):
        return "released_recipe_not_reproduced"
    if not all(row["execution"] == "completed" for row in released):
        return "deferred_until_both_released_arms_complete"
    if all(row["close_numerical_reproduction"] for row in released):
        return "close_numerical_reproduction"
    if all(row["directional_support"] for row in released):
        return "directional_support_without_close_numerical_reproduction"
    if any(row["directional_support"] for row in released):
        return "mixed"
    return "released_recipe_does_not_support_registered_direction"


def response_source_differences(rows: list[dict[str, Any]]) -> dict[str, Any]:
    differences: dict[str, Any] = {}
    for model in sorted({row["model"] for row in rows}):
        model_rows = {
            row["track"]: row
            for row in rows
            if row["model"] == model and row["execution"] == "completed"
        }
        if set(model_rows) != {"R", "M"}:
            differences[model] = {"status": "pending_both_tracks"}
            continue
        differences[model] = {
            "status": "available",
            "manuscript_minus_release": {
                key: (
                    model_rows["M"]["observed"][key]
                    - model_rows["R"]["observed"][key]
                )
                for key in ("distributional_fidelity", "strategy_alignment")
            },
        }
    return differences


def build_payload(runs_root: Path) -> dict[str, Any]:
    protocol = load_json(CONFIG_PATH)
    rows = [arm_result(arm, runs_root, protocol) for arm in load_arms()]
    states = ("pending", "unterminated", "failed", "invalid_complete", "completed")
    return {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "protocol_version": PROTOCOL_VERSION,
        "analysis_policy": {
            "attempt_selection": (
                "lexicographically latest completed attempt; otherwise latest "
                "failed or unterminated attempt"
            ),
            "comparison": "absolute difference from digitized Figure 3 bar",
            "uncertainty": (
                "unavailable in exact released evaluator because individual "
                "outcomes are not persisted"
            ),
        },
        "summary": {
            "execution_counts": {
                state: sum(row["execution"] == state for row in rows)
                for state in states
            },
            "released_global_token_result": released_result_assessment(rows),
            "headline_comparative_claim": (
                "not_testable_from_public_v1_matrix_missing_baseline_recipes"
            ),
            "response_source_comparison": response_source_differences(rows),
        },
        "arms": rows,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# arXiv:2607.17674 matrix status",
        "",
        "| Arm | Execution | Fidelity | Strategy alignment | Close | Direction |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in payload["arms"]:
        if row["execution"] != "completed":
            lines.append(
                f"| {row['arm_id']} | {row['execution']} | — | — | — | — |"
            )
            continue
        lines.append(
            f"| {row['arm_id']} | completed | "
            f"{row['observed']['distributional_fidelity']:.4f} | "
            f"{row['observed']['strategy_alignment']:.4f} | "
            f"{'yes' if row['close_numerical_reproduction'] else 'no'} | "
            f"{'supports' if row['directional_support'] else 'does not support'} |"
        )
    lines.extend(
        [
            "",
            "The exact released evaluator saves aggregate metrics only, so the "
            "registered within-evaluation interval is unavailable. Independent "
            "training and decoding variance is also not identified.",
            "",
            "The public v1 matrix cannot test the full comparative headline "
            "claim because exact baseline recipes are not released.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=(
            WORKSPACE
            / "research"
            / "replications"
            / "2607.17674"
            / "work"
            / "primary"
            / "runs"
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    payload = build_payload(args.runs_root.expanduser().resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.markdown is not None:
        write_markdown(args.markdown.expanduser().resolve(), payload)
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()

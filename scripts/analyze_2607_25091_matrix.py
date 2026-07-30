#!/usr/bin/env python3
"""Consolidate the frozen 30-arm matrix without rewriting run artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

WORKSPACE_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_PATH))

from reprolab.protocol import WORKSPACE, Arm, load_arms
from scripts.audit_reported_statistics import holm_adjust


REQUIRED_COMPLETE_FILES = (
    "run.complete.json",
    "paired_eval.json",
    "eval_sft/evaluation_results.json",
    "eval_ppo/evaluation_results.json",
    "eval_sft/all_generations.json",
    "eval_ppo/all_generations.json",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def stable_seed(label: str) -> int:
    digest = hashlib.sha256(label.encode()).digest()
    return int.from_bytes(digest[:8], "big")


def bootstrap_mean_interval(
    values: np.ndarray,
    *,
    label: str,
    replicates: int = 10_000,
) -> list[float]:
    rng = np.random.default_rng(stable_seed(label))
    indices = rng.integers(
        0,
        len(values),
        size=(replicates, len(values)),
    )
    means = values[indices].mean(axis=1)
    interval = np.quantile(means, [0.025, 0.975])
    return [float(interval[0]), float(interval[1])]


def direction_assessment(
    published_delta: float,
    rerun_delta: float,
    interval: list[float],
) -> str:
    low, high = interval
    if low <= 0.0 <= high:
        return "practically_indistinguishable_from_zero"
    if math.copysign(1.0, published_delta) == math.copysign(
        1.0, rerun_delta
    ):
        return "agrees"
    return "disagrees"


def attempts_for(arm: Arm, runs_root: Path) -> list[Path]:
    root = runs_root / arm.arm_id
    return sorted(root.glob("attempt-*")) if root.is_dir() else []


def terminal_attempt(arm: Arm, runs_root: Path) -> tuple[str, Path | None]:
    attempts = attempts_for(arm, runs_root)
    complete = [
        path for path in attempts if (path / "run.complete.json").is_file()
    ]
    if complete:
        return "completed", complete[-1]
    failed = [
        path for path in attempts if (path / "run.failed.json").is_file()
    ]
    if failed:
        return "failed", failed[-1]
    if attempts:
        return "unterminated", attempts[-1]
    return "pending", None


def aligned_release_rewards(
    sft_path: Path,
    ppo_path: Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    sft_rows = load_json(sft_path)
    ppo_rows = load_json(ppo_path)
    if len(sft_rows) != 200 or len(ppo_rows) != 200:
        raise ValueError(
            f"expected 200 release rows, found {len(sft_rows)}/"
            f"{len(ppo_rows)}"
        )
    for sft, ppo in zip(sft_rows, ppo_rows, strict=True):
        if sft["index"] != ppo["index"] or sft["prompt"] != ppo["prompt"]:
            raise ValueError("release evaluation rows are not prompt-aligned")
        if sft.get("reward") is None or ppo.get("reward") is None:
            raise ValueError("release evaluation row is missing reward telemetry")
    differences = np.asarray(
        [
            float(ppo["reward"]) - float(sft["reward"])
            for sft, ppo in zip(sft_rows, ppo_rows, strict=True)
        ],
        dtype=np.float64,
    )
    return differences, {
        "samples": len(differences),
        "sft_generation_sha256": hashlib.sha256(
            sft_path.read_bytes()
        ).hexdigest(),
        "ppo_generation_sha256": hashlib.sha256(
            ppo_path.read_bytes()
        ).hexdigest(),
    }


def published_row(
    published: dict[str, Any],
    model: str,
    dataset: str,
) -> dict[str, Any]:
    return published["our_models"][model]["datasets"][dataset]


def complete_arm_result(
    arm: Arm,
    attempt: Path,
    published: dict[str, Any],
) -> dict[str, Any]:
    missing = [
        relative
        for relative in REQUIRED_COMPLETE_FILES
        if not (attempt / relative).is_file()
    ]
    if missing:
        return {
            "arm_id": arm.arm_id,
            "track": arm.track,
            "model": arm.model,
            "dataset": arm.dataset,
            "seed": arm.seed,
            "execution": "invalid_complete",
            "attempt": str(attempt),
            "missing_required_files": missing,
        }

    sft_eval = load_json(
        attempt / "eval_sft" / "evaluation_results.json"
    )["metrics"]
    ppo_eval = load_json(
        attempt / "eval_ppo" / "evaluation_results.json"
    )["metrics"]
    paired = load_json(attempt / "paired_eval.json")
    differences, release_artifacts = aligned_release_rewards(
        attempt / "eval_sft" / "all_generations.json",
        attempt / "eval_ppo" / "all_generations.json",
    )
    release_delta = float(differences.mean())
    release_interval = bootstrap_mean_interval(
        differences,
        label=f"{arm.arm_id}:release-bootstrap-v1",
    )
    target = published_row(published, arm.model, arm.dataset)
    published_delta = float(target["reward_delta"])
    numerical_match = (
        release_interval[0] <= published_delta <= release_interval[1]
    )
    paired_reward = paired["reward"]

    return {
        "arm_id": arm.arm_id,
        "track": arm.track,
        "model": arm.model,
        "dataset": arm.dataset,
        "seed": arm.seed,
        "execution": "completed",
        "attempt": str(attempt),
        "run_manifest": load_json(attempt / "run.complete.json"),
        "published": {
            "sft_perplexity": float(target["sft_perplexity"]),
            "ppo_perplexity": float(target["ppo_perplexity"]),
            "reward_delta": published_delta,
        },
        "release_protocol": {
            "sft_perplexity": float(sft_eval["perplexity"]),
            "ppo_perplexity": float(ppo_eval["perplexity"]),
            "sft_reward_mean": float(sft_eval["reward_mean"]),
            "ppo_reward_mean": float(ppo_eval["reward_mean"]),
            "reward_delta_from_aggregates": (
                float(ppo_eval["reward_mean"])
                - float(sft_eval["reward_mean"])
            ),
            "prompt_paired_reward_delta": release_delta,
            "prompt_paired_bootstrap_95_ci": release_interval,
            "absolute_published_delta_discrepancy": abs(
                release_delta - published_delta
            ),
            "published_delta_inside_bootstrap_95_ci": numerical_match,
            "directional_assessment": direction_assessment(
                published_delta,
                release_delta,
                release_interval,
            ),
            "artifacts": release_artifacts,
        },
        "independent_paired": paired,
    }


def arm_result(
    arm: Arm,
    runs_root: Path,
    published: dict[str, Any],
) -> dict[str, Any]:
    execution, attempt = terminal_attempt(arm, runs_root)
    if execution == "completed" and attempt is not None:
        return complete_arm_result(arm, attempt, published)
    result: dict[str, Any] = {
        "arm_id": arm.arm_id,
        "track": arm.track,
        "model": arm.model,
        "dataset": arm.dataset,
        "seed": arm.seed,
        "execution": execution,
    }
    if attempt is not None:
        result["attempt"] = str(attempt)
        terminal = attempt / (
            "run.failed.json"
            if execution == "failed"
            else "run.start.json"
        )
        if terminal.is_file():
            result["run_manifest"] = load_json(terminal)
    return result


def add_holm_families(rows: list[dict[str, Any]]) -> None:
    for track in ("R", "M"):
        track_rows = [row for row in rows if row["track"] == track]
        raw = []
        for row in track_rows:
            if row["execution"] == "completed":
                raw.append(
                    float(
                        row["independent_paired"]["reward"][
                            "paired_sign_flip_pvalue"
                        ]
                    )
                )
            else:
                raw.append(1.0)
        adjusted = holm_adjust(raw)
        for row, p_value in zip(track_rows, adjusted, strict=True):
            if row["execution"] == "completed":
                row["independent_paired"]["reward"][
                    "paired_sign_flip_pvalue_holm_15"
                ] = p_value


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for track in ("R", "M"):
        selected = [row for row in rows if row["track"] == track]
        completed = [
            row for row in selected if row["execution"] == "completed"
        ]
        result[track] = {
            "execution_counts": {
                state: sum(row["execution"] == state for row in selected)
                for state in (
                    "pending",
                    "unterminated",
                    "failed",
                    "invalid_complete",
                    "completed",
                )
            },
            "numerical_matches": sum(
                row["release_protocol"][
                    "published_delta_inside_bootstrap_95_ci"
                ]
                for row in completed
            ),
            "direction_counts": {
                state: sum(
                    row["release_protocol"]["directional_assessment"]
                    == state
                    for row in completed
                )
                for state in (
                    "agrees",
                    "disagrees",
                    "practically_indistinguishable_from_zero",
                )
            },
            "claim_level_assessment": (
                "ready_for_interpretation"
                if len(completed) == 15
                else "deferred_until_all_15_complete"
            ),
        }
    return result


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# arXiv:2607.25091 matrix status",
        "",
        "| Arm | Execution | Published delta | Rerun release delta "
        "(95% bootstrap CI) | Direction |",
        "|---|---|---:|---:|---|",
    ]
    for row in payload["arms"]:
        if row["execution"] != "completed":
            lines.append(
                f"| {row['arm_id']} | {row['execution']} | — | — | — |"
            )
            continue
        release = row["release_protocol"]
        low, high = release["prompt_paired_bootstrap_95_ci"]
        lines.append(
            f"| {row['arm_id']} | completed | "
            f"{row['published']['reward_delta']:+.4f} | "
            f"{release['prompt_paired_reward_delta']:+.4f} "
            f"[{low:+.4f}, {high:+.4f}] | "
            f"{release['directional_assessment']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=WORKSPACE / "paper_repro" / "full_matrix_runs",
    )
    parser.add_argument(
        "--published-results",
        type=Path,
        default=(
            WORKSPACE
            / "paper_repro"
            / "SLM-RL-Agents"
            / "results"
            / "all_results.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=WORKSPACE / "paper_repro" / "full_matrix_analysis.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=WORKSPACE / "paper_repro" / "FULL_MATRIX_REPORT.md",
    )
    args = parser.parse_args()

    published = load_json(args.published_results)
    rows = [
        arm_result(arm, args.runs_root, published) for arm in load_arms()
    ]
    add_holm_families(rows)
    payload = {
        "schema_version": 1,
        "paper_id": "2607.25091",
        "protocol_version": "1.0.0",
        "analysis": {
            "release_reward_interval": (
                "prompt-paired 10000-replicate bootstrap"
            ),
            "bootstrap_seed": (
                "first 64 bits of SHA-256(arm_id + "
                "':release-bootstrap-v1')"
            ),
            "multiple_testing": (
                "Holm adjustment within each 15-arm track; missing arms "
                "enter the interim family with p=1"
            ),
            "immutable_attempt_selection": (
                "lexicographically latest completed attempt, otherwise "
                "latest failed or unterminated attempt"
            ),
        },
        "summary": summary(rows),
        "arms": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    write_markdown(args.markdown, payload)
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()

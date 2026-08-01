#!/usr/bin/env python3
"""Describe post-hoc epoch-level stability without changing the verdict."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import torch

from analyze_trials import fmt, sha256, summarize


MODEL_STAGES = (
    "control_student",
    "control_teacher",
    "rkd_paper_weak_teacher",
    "rkd_upstream_asr_teacher",
    "sprkd_paper_random_init",
    "sprkd_upstream_direct_init",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def stage_summary(
    checkpoint_path: Path, completed_model: dict[str, Any]
) -> dict[str, Any]:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    history = checkpoint.get("history", {}).get("VALIDATION", {})
    accuracies = [float(value) for value in history.get("ACCURACIES", [])]
    losses = [float(value) for value in history.get("LOSSES", [])]
    if len(accuracies) != 500 or len(losses) != 500:
        raise ValueError(f"expected 500 validation epochs: {checkpoint_path}")
    if not all(math.isfinite(value) for value in accuracies + losses):
        raise ValueError(f"non-finite validation history: {checkpoint_path}")
    best_index = max(range(500), key=accuracies.__getitem__)
    drops = [accuracies[index - 1] - accuracies[index] for index in range(1, 500)]
    gains = [accuracies[index] - accuracies[index - 1] for index in range(1, 500)]
    largest_drop_index = max(range(1, 500), key=lambda index: drops[index - 1])
    largest_gain_index = max(range(1, 500), key=lambda index: gains[index - 1])
    if not math.isclose(
        accuracies[-1],
        float(completed_model["final_valid_accuracy_unweighted_batch_mean"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(f"final history accuracy differs: {checkpoint_path}")
    if not math.isclose(
        accuracies[best_index],
        float(completed_model["best_valid_accuracy_unweighted_batch_mean"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(f"best history accuracy differs: {checkpoint_path}")

    first_above_85 = next(
        (index for index, value in enumerate(accuracies) if value >= 85.0), None
    )
    return {
        "checkpoint_sha256": sha256(checkpoint_path),
        "best_accuracy_unweighted_batch_mean": accuracies[best_index],
        "best_epoch_1_based": best_index + 1,
        "final_accuracy_unweighted_batch_mean": accuracies[-1],
        "best_to_final_drop_points": accuracies[best_index] - accuracies[-1],
        "largest_one_epoch_drop_points": drops[largest_drop_index - 1],
        "largest_drop_arrival_epoch_1_based": largest_drop_index + 1,
        "largest_one_epoch_gain_points": gains[largest_gain_index - 1],
        "largest_gain_arrival_epoch_1_based": largest_gain_index + 1,
        "epochs_below_60_after_first_epoch_at_or_above_85": (
            sum(value < 60.0 for value in accuracies[first_above_85 + 1 :])
            if first_above_85 is not None
            else None
        ),
        "final_50_epoch_accuracy_mean": sum(accuracies[-50:]) / 50,
        "validation_epoch_count": len(accuracies),
    }


def main() -> int:
    args = parse_args()
    base_root = args.base_root.resolve()
    seeds: dict[int, dict[str, Any]] = {}
    for seed in range(5):
        complete_path = base_root / f"seed-{seed}" / "complete.json"
        if not complete_path.is_file():
            continue
        complete = json.loads(complete_path.read_text())
        if complete.get("complete") is not True or complete.get("seed") != seed:
            raise ValueError(f"invalid completion metadata for seed {seed}")
        models = complete.get("models", {})
        if not set(MODEL_STAGES) <= set(models):
            raise ValueError(f"seed {seed} lacks a required stability stage")
        seeds[seed] = {
            stage: stage_summary(
                base_root / f"seed-{seed}" / "stages" / f"{stage}.pth",
                models[stage],
            )
            for stage in MODEL_STAGES
        }

    aggregates = {
        stage: {
            "best_to_final_drop_points": summarize(
                [seeds[seed][stage]["best_to_final_drop_points"] for seed in seeds]
            ),
            "largest_one_epoch_drop_points": summarize(
                [seeds[seed][stage]["largest_one_epoch_drop_points"] for seed in seeds]
            ),
        }
        for stage in MODEL_STAGES
    }
    output = {
        "schema_version": "nulspec-sprkd-posthoc-stability-v1",
        "status": "complete" if len(seeds) == 5 else "incomplete",
        "complete_seeds": sorted(seeds),
        "expected_seeds": list(range(5)),
        "interpretation_scope": (
            "Post-hoc descriptive analysis added after seed 1 exposed a sharp "
            "accuracy drop; it cannot alter the preregistered verdict."
        ),
        "accuracy_weighting": "unweighted_validation_batch_mean_per_epoch",
        "seeds": {str(seed): seeds[seed] for seed in sorted(seeds)},
        "aggregates": aggregates,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "training_stability_summary.json"
    json_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    lines = [
        "# Post-hoc training-stability results",
        "",
        f"Status: **{output['status']}** ({len(seeds)}/5 frozen seeds).",
        "",
        "This descriptive analysis was specified after seed 1 exposed a sharp "
        "epoch-level drop. It does not alter the preregistered verdict.",
        "",
        "| Seed | Model | Best (epoch) | Final | Largest one-epoch drop (arrival) |",
        "|---:|---|---:|---:|---:|",
    ]
    for seed in sorted(seeds):
        for stage in MODEL_STAGES:
            row = seeds[seed][stage]
            lines.append(
                f"| {seed} | `{stage}` | "
                f"{fmt(row['best_accuracy_unweighted_batch_mean'])} "
                f"({row['best_epoch_1_based']}) | "
                f"{fmt(row['final_accuracy_unweighted_batch_mean'])} | "
                f"{fmt(row['largest_one_epoch_drop_points'])} "
                f"({row['largest_drop_arrival_epoch_1_based']}) |"
            )
    lines.extend(
        [
            "",
            "Values are the released runner's unweighted validation-batch means. "
            "Final sample-weighted metrics remain the primary outcomes.",
            "",
        ]
    )
    (args.output_dir / "TRAINING_STABILITY_RESULTS.md").write_text("\n".join(lines))
    print(
        f"TRAINING_STABILITY_ANALYSIS status={output['status']} "
        f"seeds={len(seeds)} output={json_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

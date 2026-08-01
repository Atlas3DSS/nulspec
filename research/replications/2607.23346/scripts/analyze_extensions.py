#!/usr/bin/env python3
"""Validate and aggregate the frozen SPRKD diagnostic extensions."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import torch

from analyze_trials import exact_mcnemar, fmt, sha256, summarize, validate_seed


EXTENSION_MODELS = {
    "rkd_conventional_logits",
    "sprkd_lowest_loss_random_init",
}
COMPARISONS = {
    "rkd_conventional_logits_minus_released_rkd": (
        "extension",
        "rkd_conventional_logits",
        "base",
        "rkd_paper_weak_teacher",
    ),
    "lowest_loss_asr_minus_last_snapshot_asr": (
        "extension",
        "sprkd_lowest_loss_random_init",
        "base",
        "sprkd_paper_random_init",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--extension-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_validated_seed(
    base_root: Path, extension_root: Path, seed: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    base_dir = base_root / f"seed-{seed}"
    extension_dir = extension_root / f"seed-{seed}"
    base_path = base_dir / "complete.json"
    extension_path = extension_dir / "complete.json"
    if not base_path.is_file() or not extension_path.is_file():
        return None

    base = json.loads(base_path.read_text())
    base_predictions, base_checks = validate_seed(base_root, seed, base)
    extension = json.loads(extension_path.read_text())
    config_path = extension_dir / "config.json"
    config = json.loads(config_path.read_text())
    if base.get("complete") is not True or extension.get("complete") is not True:
        raise ValueError(f"seed {seed}: completion flag is not true")
    if extension.get("schema_version") != "nulspec-sprkd-extension-v1":
        raise ValueError(f"seed {seed}: extension schema differs")
    if extension.get("seed") != seed or config.get("seed") != seed:
        raise ValueError(f"seed {seed}: seed metadata differs")
    if extension.get("config_sha256") != sha256(config_path):
        raise ValueError(f"seed {seed}: extension config hash differs")
    if config.get("base_complete_sha256") != sha256(base_path):
        raise ValueError(f"seed {seed}: base result hash differs")
    if config.get("base_config_sha256") != sha256(base_dir / "config.json"):
        raise ValueError(f"seed {seed}: base config hash differs")
    if config.get("base_split_indices_sha256") != sha256(
        base_dir / "split_indices.pth"
    ):
        raise ValueError(f"seed {seed}: base split hash differs")
    if set(extension.get("models", {})) != EXTENSION_MODELS:
        raise ValueError(f"seed {seed}: extension model set differs")

    prediction_path = extension_dir / "predictions.pth"
    predictions = torch.load(prediction_path, map_location="cpu", weights_only=False)
    targets = torch.as_tensor(predictions["targets"]).long().reshape(-1)
    base_targets = torch.as_tensor(base_predictions["targets"]).long().reshape(-1)
    if targets.numel() != 6_890 or not torch.equal(targets, base_targets):
        raise ValueError(f"seed {seed}: extension targets differ from base")
    if not set(targets.tolist()) <= {0, 1}:
        raise ValueError(f"seed {seed}: target label outside binary classes")
    if set(predictions["predictions"]) != EXTENSION_MODELS:
        raise ValueError(f"seed {seed}: extension prediction set differs")
    for model in sorted(EXTENSION_MODELS):
        predicted = (
            torch.as_tensor(predictions["predictions"][model]).long().reshape(-1)
        )
        if predicted.numel() != targets.numel():
            raise ValueError(f"seed {seed}: {model} prediction count differs")
        if not set(predicted.tolist()) <= {0, 1}:
            raise ValueError(f"seed {seed}: {model} emitted a non-binary class")
        observed = 100.0 * float((predicted == targets).sum().item()) / targets.numel()
        recorded = float(extension["models"][model]["accuracy_sample_weighted"])
        if not math.isclose(observed, recorded, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"seed {seed}: {model} recorded accuracy differs")

    selected = config.get("selected_saddles", [])
    if len(selected) != 3:
        raise ValueError(f"seed {seed}: selected-saddle metadata differs")
    for row in selected:
        teacher_index = int(row["teacher_index"])
        checkpoint = torch.load(
            base_dir / "stages" / f"weak_teacher_{teacher_index}.pth",
            map_location="cpu",
            weights_only=False,
        )
        losses = [float(value) for value in checkpoint["saddle_losses"]]
        finite = [
            (index, loss) for index, loss in enumerate(losses) if math.isfinite(loss)
        ]
        expected_index, expected_loss = min(finite, key=lambda item: item[1])
        if row["selected_index"] != expected_index or not math.isclose(
            float(row["selected_loss"]), expected_loss, rel_tol=0.0, abs_tol=0.0
        ):
            raise ValueError(f"seed {seed}: lowest-loss selection differs")

    checks = {
        "status": "passed",
        "base_complete_sha256": sha256(base_path),
        "base_predictions_sha256": base_checks["predictions_sha256"],
        "base_integrity_revalidated": True,
        "extension_complete_sha256": sha256(extension_path),
        "extension_config_sha256": sha256(config_path),
        "extension_predictions_sha256": sha256(prediction_path),
        "extension_checkpoint_sha256s": {
            model: sha256(extension_dir / f"{model}.pth")
            for model in sorted(EXTENSION_MODELS)
        },
        "lowest_loss_asr_sha256": sha256(extension_dir / "lowest_loss_asr.pth"),
        "targets_equal_base": True,
        "n_targets": targets.numel(),
        "lowest_loss_selections_recomputed": True,
    }
    bundle = {
        "extension": predictions,
        "base": base_predictions,
    }
    return (
        base,
        extension,
        {
            "checks": checks,
            "predictions": bundle,
            "selected_saddles": selected,
        },
    )


def main() -> None:
    args = parse_args()
    seeds = {}
    for seed in range(5):
        loaded = load_validated_seed(
            args.base_root.resolve(), args.extension_root.resolve(), seed
        )
        if loaded is not None:
            seeds[seed] = loaded

    models = {}
    for model in sorted(EXTENSION_MODELS):
        accuracies = [
            float(seeds[seed][1]["models"][model]["accuracy_sample_weighted"])
            for seed in sorted(seeds)
        ]
        losses = [
            float(seeds[seed][1]["models"][model]["cross_entropy_sample_weighted"])
            for seed in sorted(seeds)
        ]
        models[model] = {
            "accuracy": summarize(accuracies),
            "cross_entropy": summarize(losses),
        }

    comparisons = {}
    for label, (left_layer, left, right_layer, right) in COMPARISONS.items():
        differences = []
        tests = []
        for seed in sorted(seeds):
            base, extension, metadata = seeds[seed]
            left_result = extension if left_layer == "extension" else base
            right_result = extension if right_layer == "extension" else base
            differences.append(
                float(left_result["models"][left]["accuracy_sample_weighted"])
                - float(right_result["models"][right]["accuracy_sample_weighted"])
            )
            prediction_bundle = metadata["predictions"]
            left_predictions = prediction_bundle[left_layer]["predictions"][left]
            right_predictions = prediction_bundle[right_layer]["predictions"][right]
            targets = prediction_bundle["extension"]["targets"]
            tests.append(
                {
                    "seed": seed,
                    **exact_mcnemar(
                        left_predictions,
                        right_predictions,
                        targets,
                    ),
                }
            )
        comparisons[label] = {
            "accuracy_point_difference": summarize(differences),
            "per_seed_mcnemar_exact": tests,
        }

    output = {
        "schema_version": "nulspec-sprkd-extension-aggregate-v1",
        "status": "complete" if len(seeds) == 5 else "incomplete",
        "complete_seeds": sorted(seeds),
        "expected_seeds": [0, 1, 2, 3, 4],
        "models": models,
        "comparisons": comparisons,
        "integrity_checks": {
            str(seed): seeds[seed][2]["checks"] for seed in sorted(seeds)
        },
        "runs": [
            {
                "run_id": f"extension-seed-{seed}",
                "seed": seed,
                "models": {
                    name: {
                        key: row[key]
                        for key in (
                            "accuracy_sample_weighted",
                            "cross_entropy_sample_weighted",
                            "best_valid_accuracy_unweighted_batch_mean",
                            "final_valid_accuracy_unweighted_batch_mean",
                            "elapsed_seconds",
                            "parameter_count",
                        )
                        if key in row
                    }
                    for name, row in sorted(seeds[seed][1]["models"].items())
                },
                "selected_saddles": seeds[seed][2]["selected_saddles"],
                "integrity": seeds[seed][2]["checks"],
            }
            for seed in sorted(seeds)
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "extension_summary.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    with (args.output_dir / "extension_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["model", "n", "mean_accuracy", "sample_sd", "t95_low", "t95_high"]
        )
        for model in sorted(models):
            summary = models[model]["accuracy"]
            writer.writerow(
                [
                    model,
                    summary["n"],
                    summary["mean"],
                    summary["sample_sd"],
                    *summary["t95_interval"],
                ]
            )

    lines = [
        "# Extension results",
        "",
        f"Status: **{output['status']}** ({len(seeds)}/5 frozen seeds).",
        "",
        "| Model | n | Mean accuracy | SD | 95% t interval | Mean CE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model in sorted(models):
        accuracy = models[model]["accuracy"]
        low, high = accuracy["t95_interval"]
        lines.append(
            f"| `{model}` | {accuracy['n']} | {fmt(accuracy['mean'])} | "
            f"{fmt(accuracy['sample_sd'])} | [{fmt(low)}, {fmt(high)}] | "
            f"{fmt(models[model]['cross_entropy']['mean'])} |"
        )
    lines.extend(
        [
            "",
            "These prospectively specified extensions do not alter the "
            "preregistered verdict.",
            "",
            "## Run-level outcomes",
            "",
            "| Run | Lowest-loss ASR | Conventional-logit RKD |",
            "|---|---:|---:|",
        ]
    )
    for run in output["runs"]:
        lines.append(
            f"| `{run['run_id']}` | "
            f"{fmt(run['models']['sprkd_lowest_loss_random_init']['accuracy_sample_weighted'])} | "
            f"{fmt(run['models']['rkd_conventional_logits']['accuracy_sample_weighted'])} |"
        )
    lines.append("")
    (args.output_dir / "EXTENSION_RESULTS.md").write_text("\n".join(lines))
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

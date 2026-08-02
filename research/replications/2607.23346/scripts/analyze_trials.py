#!/usr/bin/env python3
"""Aggregate complete SPRKD trials into JSON, CSV, and a concise Markdown table."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

import torch
from scipy.special import logsumexp
from scipy.stats import binom, binomtest
from scipy.stats import t as student_t

from sprkd.stats import mcnemar_table


REPORTED = {
    "weak_teacher_ensemble_mean": 70.13,
    "control_teacher": 94.50,
    "control_student": 94.47,
    "rkd_upstream_asr_teacher": 70.10,
    "rkd_paper_weak_teacher": 70.10,
    "sprkd_upstream_direct_init": 94.80,
    "sprkd_paper_random_init": 94.80,
}

EXPECTED_CONFIG = {
    "schema_version": "nulspec-sprkd-trial-v1",
    "epochs": 500,
    "teacher_epochs": 2,
    "n_teachers": 3,
    "batch_size": 64,
    "train_fraction": 0.75,
    "dataset_samples": 27_558,
    "train_samples": 20_668,
    "valid_samples": 6_890,
    "learning_rate": 0.001,
    "saddle_steps": 1,
    "n_top_eigs": 4,
    "saddle_rule": "magnitude",
    "saddle_magnitude_threshold": 7.0,
    "upstream_commit": "7f1655ff1295c9a6dcf8d24f6410a036cd7e3497",
}
PREDICTION_MODELS = {
    "control_student",
    "control_teacher",
    "rkd_paper_weak_teacher",
    "rkd_upstream_asr_teacher",
    "sprkd_paper_random_init",
    "sprkd_upstream_direct_init",
}
EXPECTED_STAGES = PREDICTION_MODELS | {
    "asr",
    "weak_teacher_0",
    "weak_teacher_1",
    "weak_teacher_2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def summarize(values: list[float]) -> dict[str, Any]:
    n = len(values)
    mean = statistics.fmean(values) if values else float("nan")
    sd = statistics.stdev(values) if n >= 2 else float("nan")
    if n >= 2:
        margin = float(student_t.ppf(0.975, n - 1)) * sd / math.sqrt(n)
        interval = [mean - margin, mean + margin]
    else:
        interval = [float("nan"), float("nan")]
    return {
        "n": n,
        "values": values,
        "mean": mean,
        "sample_sd": sd,
        "t95_interval": interval,
    }


def fmt(value: float) -> str:
    return "—" if not math.isfinite(value) else f"{value:.3f}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def public_environment(value: dict[str, Any] | None) -> dict[str, Any]:
    """Retain reproducibility fields without publishing machine identifiers."""
    environment = dict(value or {})
    environment.pop("hostname", None)
    gpu = dict(environment.get("gpu") or {})
    gpu.pop("visible_devices", None)
    if gpu:
        environment["gpu"] = gpu
    return environment


def exact_mcnemar(
    predictions_a: torch.Tensor,
    predictions_b: torch.Tensor,
    targets: torch.Tensor,
) -> dict[str, Any]:
    """Numerically stable two-sided exact McNemar result.

    The released package evaluates ``comb(n, i) * 0.5**n`` in binary64 and
    overflows on the full validation set. SciPy's exact binomial test computes
    the same two-sided test without materializing enormous binomial
    coefficients.
    """
    a, b, c, d = mcnemar_table(predictions_a, predictions_b, targets)
    discordant = b + c
    p_value = (
        float(binomtest(min(b, c), discordant, 0.5, alternative="two-sided").pvalue)
        if discordant
        else 1.0
    )
    if not discordant or b == c:
        log10_p_value = 0.0
    else:
        lower_tail = [
            float(binom.logpmf(index, discordant, 0.5))
            for index in range(min(b, c) + 1)
        ]
        log_p_value = min(0.0, math.log(2.0) + float(logsumexp(lower_tail)))
        log10_p_value = log_p_value / math.log(10.0)
    n = a + b + c + d
    return {
        "n": n,
        "a_correct_b_correct": a,
        "a_correct_b_wrong": b,
        "a_wrong_b_correct": c,
        "a_wrong_b_wrong": d,
        "statistic": float(min(b, c)),
        "p_value": p_value,
        "log10_p_value": log10_p_value,
        "method": "exact binomial (scipy.stats.binomtest)",
        "accuracy_a": (a + b) / max(1, n),
        "accuracy_b": (a + c) / max(1, n),
    }


def validate_seed(
    input_root: Path, seed: int, payload: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fail closed unless a completed seed is internally self-consistent."""
    trial_dir = input_root / f"seed-{seed}"
    config_path = trial_dir / "config.json"
    split_path = trial_dir / "split_indices.pth"
    predictions_path = trial_dir / "predictions.pth"
    if payload.get("complete") is not True:
        raise ValueError(f"seed {seed}: completion flag is not true")
    if payload.get("schema_version") != "nulspec-sprkd-trial-v1":
        raise ValueError(f"seed {seed}: unexpected result schema")
    if int(payload.get("seed", -1)) != seed:
        raise ValueError(f"seed {seed}: result seed does not match directory")
    for required in (config_path, split_path, predictions_path):
        if not required.is_file():
            raise FileNotFoundError(f"seed {seed}: missing {required.name}")

    config = json.loads(config_path.read_text())
    if int(config.get("seed", -1)) != seed:
        raise ValueError(f"seed {seed}: config seed does not match directory")
    for key, expected in EXPECTED_CONFIG.items():
        if config.get(key) != expected:
            raise ValueError(
                f"seed {seed}: config {key}={config.get(key)!r}, expected {expected!r}"
            )
    config_digest = sha256(config_path)
    if payload.get("config_sha256") != config_digest:
        raise ValueError(f"seed {seed}: config hash does not match result")

    split = torch.load(split_path, map_location="cpu", weights_only=False)
    train_indices = [int(value) for value in split["train_indices"]]
    valid_indices = [int(value) for value in split["valid_indices"]]
    if len(train_indices) != EXPECTED_CONFIG["train_samples"]:
        raise ValueError(f"seed {seed}: wrong training split length")
    if len(valid_indices) != EXPECTED_CONFIG["valid_samples"]:
        raise ValueError(f"seed {seed}: wrong validation split length")
    if len(set(train_indices)) != len(train_indices):
        raise ValueError(f"seed {seed}: duplicate training index")
    if len(set(valid_indices)) != len(valid_indices):
        raise ValueError(f"seed {seed}: duplicate validation index")
    if set(train_indices) & set(valid_indices):
        raise ValueError(f"seed {seed}: train/validation overlap")
    if set(train_indices) | set(valid_indices) != set(range(27_558)):
        raise ValueError(f"seed {seed}: split does not partition the dataset")

    stage_names = {path.stem for path in (trial_dir / "stages").glob("*.pth")}
    if stage_names != EXPECTED_STAGES:
        raise ValueError(f"seed {seed}: stage set differs; got {sorted(stage_names)}")

    prediction_payload = torch.load(
        predictions_path, map_location="cpu", weights_only=False
    )
    targets = torch.as_tensor(prediction_payload["targets"]).long().reshape(-1)
    predictions = prediction_payload["predictions"]
    if targets.numel() != EXPECTED_CONFIG["valid_samples"]:
        raise ValueError(f"seed {seed}: wrong prediction target count")
    if set(predictions) != PREDICTION_MODELS:
        raise ValueError(f"seed {seed}: prediction model set differs")
    if not set(targets.tolist()) <= {0, 1}:
        raise ValueError(f"seed {seed}: target label outside binary classes")
    for model in sorted(PREDICTION_MODELS):
        predicted = torch.as_tensor(predictions[model]).long().reshape(-1)
        if predicted.numel() != targets.numel():
            raise ValueError(f"seed {seed}: {model} prediction count differs")
        if not set(predicted.tolist()) <= {0, 1}:
            raise ValueError(f"seed {seed}: {model} emitted a non-binary class")
        observed = 100.0 * float((predicted == targets).sum().item()) / targets.numel()
        recorded = float(payload["models"][model]["accuracy_sample_weighted"])
        if not math.isclose(observed, recorded, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"seed {seed}: {model} accuracy {recorded} != {observed}")

    index_digest = hashlib.sha256(
        json.dumps(valid_indices, separators=(",", ":")).encode()
    ).hexdigest()
    checks = {
        "status": "passed",
        "complete_sha256": sha256(trial_dir / "complete.json"),
        "config_sha256": config_digest,
        "split_indices_sha256": sha256(split_path),
        "validation_indices_sha256": index_digest,
        "predictions_sha256": sha256(predictions_path),
        "stage_count": len(stage_names),
        "stage_checkpoint_sha256s": {
            name: sha256(trial_dir / "stages" / f"{name}.pth")
            for name in sorted(stage_names)
        },
        "prediction_models": sorted(predictions),
        "n_validation_targets": targets.numel(),
    }
    return prediction_payload, checks


def main() -> None:
    args = parse_args()
    seeds: dict[int, dict[str, Any]] = {}
    for seed in range(5):
        path = args.input_root / f"seed-{seed}" / "complete.json"
        if path.is_file():
            seeds[seed] = json.loads(path.read_text())

    prediction_payloads: dict[int, dict[str, Any]] = {}
    integrity_checks: dict[str, Any] = {}
    for seed, payload in sorted(seeds.items()):
        predictions, checks = validate_seed(args.input_root, seed, payload)
        prediction_payloads[seed] = predictions
        integrity_checks[str(seed)] = checks

    model_names = sorted(
        {
            model
            for payload in seeds.values()
            for model in payload.get("models", {})
            if "accuracy_sample_weighted" in payload["models"][model]
        }
    )
    models: dict[str, Any] = {}
    for model in model_names:
        accuracies = [
            float(seeds[seed]["models"][model]["accuracy_sample_weighted"])
            for seed in sorted(seeds)
            if model in seeds[seed]["models"]
        ]
        losses = [
            float(seeds[seed]["models"][model]["cross_entropy_sample_weighted"])
            for seed in sorted(seeds)
            if model in seeds[seed]["models"]
        ]
        best_history_accuracies = [
            float(
                seeds[seed]["models"][model][
                    "best_valid_accuracy_unweighted_batch_mean"
                ]
            )
            for seed in sorted(seeds)
            if model in seeds[seed]["models"]
            and "best_valid_accuracy_unweighted_batch_mean"
            in seeds[seed]["models"][model]
        ]
        final_history_accuracies = [
            float(
                seeds[seed]["models"][model][
                    "final_valid_accuracy_unweighted_batch_mean"
                ]
            )
            for seed in sorted(seeds)
            if model in seeds[seed]["models"]
            and "final_valid_accuracy_unweighted_batch_mean"
            in seeds[seed]["models"][model]
        ]
        model_result = {
            "accuracy": summarize(accuracies),
            "cross_entropy": summarize(losses),
            "reported_accuracy": REPORTED.get(model),
        }
        if best_history_accuracies:
            model_result["best_history_accuracy_unweighted_batch_mean"] = summarize(
                best_history_accuracies
            )
        if final_history_accuracies:
            model_result["final_history_accuracy_unweighted_batch_mean"] = summarize(
                final_history_accuracies
            )
        models[model] = model_result
        reported = REPORTED.get(model)
        if reported is not None and len(accuracies) >= 2:
            low, high = models[model]["accuracy"]["t95_interval"]
            models[model]["reported_accuracy_inside_t95"] = low <= reported <= high

    weak_teacher_accuracies = [
        statistics.fmean(
            float(
                seeds[seed]["models"][f"weak_teacher_{index}"][
                    "accuracy_sample_weighted"
                ]
            )
            for index in range(3)
        )
        for seed in sorted(seeds)
    ]
    weak_teacher_losses = [
        statistics.fmean(
            float(
                seeds[seed]["models"][f"weak_teacher_{index}"][
                    "cross_entropy_sample_weighted"
                ]
            )
            for index in range(3)
        )
        for seed in sorted(seeds)
    ]
    weak_summary = summarize(weak_teacher_accuracies)
    models["weak_teacher_ensemble_mean"] = {
        "accuracy": weak_summary,
        "cross_entropy": summarize(weak_teacher_losses),
        "best_history_accuracy_unweighted_batch_mean": summarize(
            [
                statistics.fmean(
                    float(
                        seeds[seed]["models"][f"weak_teacher_{index}"][
                            "best_valid_accuracy_unweighted_batch_mean"
                        ]
                    )
                    for index in range(3)
                )
                for seed in sorted(seeds)
            ]
        ),
        "final_history_accuracy_unweighted_batch_mean": summarize(
            [
                statistics.fmean(
                    float(
                        seeds[seed]["models"][f"weak_teacher_{index}"][
                            "final_valid_accuracy_unweighted_batch_mean"
                        ]
                    )
                    for index in range(3)
                )
                for seed in sorted(seeds)
            ]
        ),
        "reported_accuracy": REPORTED["weak_teacher_ensemble_mean"],
    }
    if len(weak_teacher_accuracies) >= 2:
        low, high = weak_summary["t95_interval"]
        models["weak_teacher_ensemble_mean"]["reported_accuracy_inside_t95"] = (
            low <= REPORTED["weak_teacher_ensemble_mean"] <= high
        )
    model_names = sorted(models)

    comparisons: dict[str, Any] = {}
    pairs = [
        ("sprkd_upstream_direct_init", "control_student"),
        ("sprkd_upstream_direct_init", "rkd_upstream_asr_teacher"),
        ("sprkd_paper_random_init", "control_student"),
        ("sprkd_paper_random_init", "rkd_paper_weak_teacher"),
        ("rkd_upstream_asr_teacher", "rkd_paper_weak_teacher"),
    ]
    for left, right in pairs:
        differences = []
        mcnemar = []
        for seed in sorted(seeds):
            left_row = seeds[seed]["models"].get(left)
            right_row = seeds[seed]["models"].get(right)
            if not left_row or not right_row:
                continue
            differences.append(
                float(left_row["accuracy_sample_weighted"])
                - float(right_row["accuracy_sample_weighted"])
            )
            if seed in prediction_payloads:
                prediction_payload = prediction_payloads[seed]
                result = exact_mcnemar(
                    prediction_payload["predictions"][left],
                    prediction_payload["predictions"][right],
                    prediction_payload["targets"],
                )
                mcnemar.append({"seed": seed, **result})
        comparisons[f"{left}_minus_{right}"] = {
            "accuracy_point_difference": summarize(differences),
            "per_seed_mcnemar_exact": mcnemar,
        }

    saddle_counts = {
        f"weak_teacher_{index}": summarize(
            [
                float(seeds[seed]["models"][f"weak_teacher_{index}"]["saddle_count"])
                for seed in sorted(seeds)
            ]
        )
        for index in range(3)
    }
    recorded_stage_seconds = [
        sum(
            float(row["elapsed_seconds"])
            for row in seeds[seed]["models"].values()
            if "elapsed_seconds" in row
        )
        for seed in sorted(seeds)
    ]
    runs = []
    for seed in sorted(seeds):
        payload = seeds[seed]
        run_models = {
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
            for name, row in sorted(payload["models"].items())
            if "accuracy_sample_weighted" in row
        }
        run_models["weak_teacher_ensemble_mean"] = {
            "accuracy_sample_weighted": statistics.fmean(
                float(
                    payload["models"][f"weak_teacher_{index}"][
                        "accuracy_sample_weighted"
                    ]
                )
                for index in range(3)
            ),
            "cross_entropy_sample_weighted": statistics.fmean(
                float(
                    payload["models"][f"weak_teacher_{index}"][
                        "cross_entropy_sample_weighted"
                    ]
                )
                for index in range(3)
            ),
        }
        config = json.loads(
            (args.input_root / f"seed-{seed}" / "config.json").read_text()
        )
        runs.append(
            {
                "run_id": f"seed-{seed}",
                "seed": seed,
                "environment": public_environment(config.get("environment")),
                "integrity": integrity_checks[str(seed)],
                "models": run_models,
            }
        )
    output = {
        "schema_version": "nulspec-sprkd-aggregate-v1",
        "complete_seeds": sorted(seeds),
        "expected_seeds": [0, 1, 2, 3, 4],
        "status": "complete" if len(seeds) == 5 else "incomplete",
        "models": models,
        "comparisons": comparisons,
        "integrity_checks": integrity_checks,
        "runs": runs,
        "operations": {
            "recorded_training_stage_seconds": summarize(recorded_stage_seconds),
            "sum_recorded_training_stage_seconds_all_seeds": sum(
                recorded_stage_seconds
            ),
            "saddle_counts": saddle_counts,
        },
        "environments": {
            str(seed): public_environment(
                seeds[seed].get("environment")
                or json.loads(
                    (args.input_root / f"seed-{seed}" / "config.json").read_text()
                ).get("environment")
            )
            for seed in sorted(seeds)
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "scratch_summary.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    with (args.output_dir / "scratch_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "model",
                "n",
                "reported_accuracy",
                "mean_accuracy",
                "sample_sd",
                "t95_low",
                "t95_high",
                "mean_cross_entropy",
                "mean_best_history_accuracy_unweighted_batch_mean",
            ]
        )
        for model in model_names:
            accuracy = models[model]["accuracy"]
            writer.writerow(
                [
                    model,
                    accuracy["n"],
                    models[model]["reported_accuracy"],
                    accuracy["mean"],
                    accuracy["sample_sd"],
                    *accuracy["t95_interval"],
                    models[model]["cross_entropy"]["mean"],
                    (
                        models[model]
                        .get("best_history_accuracy_unweighted_batch_mean", {})
                        .get("mean")
                    ),
                ]
            )

    lines = [
        "# Scratch-run results",
        "",
        f"Status: **{output['status']}** ({len(seeds)}/5 frozen seeds).",
        "",
        "| Model | n | Paper acc. | Mean acc. | SD | 95% t interval | Mean CE |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in model_names:
        accuracy = models[model]["accuracy"]
        low, high = accuracy["t95_interval"]
        reported = models[model]["reported_accuracy"]
        lines.append(
            f"| `{model}` | {accuracy['n']} | "
            f"{fmt(float(reported)) if reported is not None else '—'} | "
            f"{fmt(accuracy['mean'])} | {fmt(accuracy['sample_sd'])} | "
            f"[{fmt(low)}, {fmt(high)}] | "
            f"{fmt(models[model]['cross_entropy']['mean'])} |"
        )
    lines.extend(
        [
            "",
            "Accuracies and losses are final, sample-weighted full-validation metrics. "
            "Intervals describe fresh-training variability over the frozen seeds; they "
            "are not prompt/bootstrap intervals.",
            "",
            "## Run-level outcomes",
            "",
            "| Run | GPU | Exact SPRKD | Intent SPRKD | Control-S | Exact RKD | Intent RKD |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for run in runs:
        run_models = run["models"]
        gpu = run["environment"].get("gpu", {}).get("name", "unknown")
        lines.append(
            f"| `{run['run_id']}` | {gpu} | "
            f"{fmt(run_models['sprkd_upstream_direct_init']['accuracy_sample_weighted'])} | "
            f"{fmt(run_models['sprkd_paper_random_init']['accuracy_sample_weighted'])} | "
            f"{fmt(run_models['control_student']['accuracy_sample_weighted'])} | "
            f"{fmt(run_models['rkd_upstream_asr_teacher']['accuracy_sample_weighted'])} | "
            f"{fmt(run_models['rkd_paper_weak_teacher']['accuracy_sample_weighted'])} |"
        )
    lines.append("")
    (args.output_dir / "SCRATCH_RESULTS.md").write_text("\n".join(lines))
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

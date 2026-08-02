#!/usr/bin/env python3
"""Validate and aggregate the post-hoc supervised-logit diagnostic."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import torch

from analyze_trials import exact_mcnemar, fmt, sha256, summarize, validate_seed


MODELS = {"control_student_logit_ce", "sprkd_logit_ce_random_init"}
COMPARISONS = {
    "logit_control_minus_released_control": (
        "extension",
        "control_student_logit_ce",
        "base",
        "control_student",
    ),
    "logit_sprkd_minus_released_intent_sprkd": (
        "extension",
        "sprkd_logit_ce_random_init",
        "base",
        "sprkd_paper_random_init",
    ),
    "logit_sprkd_minus_logit_control": (
        "extension",
        "sprkd_logit_ce_random_init",
        "extension",
        "control_student_logit_ce",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--extension-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def validated_seed(
    base_root: Path, extension_root: Path, seed: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    base_dir = base_root / f"seed-{seed}"
    extension_dir = extension_root / f"seed-{seed}"
    base_path = base_dir / "complete.json"
    complete_path = extension_dir / "complete.json"
    config_path = extension_dir / "config.json"
    if not complete_path.is_file():
        return None
    if not base_path.is_file() or not config_path.is_file():
        raise FileNotFoundError(f"seed {seed}: missing base or extension config")
    base = json.loads(base_path.read_text())
    base_predictions, base_checks = validate_seed(base_root, seed, base)
    extension = json.loads(complete_path.read_text())
    config = json.loads(config_path.read_text())
    if base.get("complete") is not True or extension.get("complete") is not True:
        raise ValueError(f"seed {seed}: completion flag differs")
    if extension.get("schema_version") != "nulspec-sprkd-loss-contract-extension-v1":
        raise ValueError(f"seed {seed}: extension schema differs")
    if extension.get("seed") != seed or config.get("seed") != seed:
        raise ValueError(f"seed {seed}: seed metadata differs")
    if extension.get("config_sha256") != sha256(config_path):
        raise ValueError(f"seed {seed}: config hash differs")
    if config.get("base_complete_sha256") != sha256(base_path):
        raise ValueError(f"seed {seed}: base completion hash differs")
    if config.get("base_config_sha256") != sha256(base_dir / "config.json"):
        raise ValueError(f"seed {seed}: base config hash differs")
    if config.get("base_split_indices_sha256") != sha256(
        base_dir / "split_indices.pth"
    ):
        raise ValueError(f"seed {seed}: base split hash differs")
    expected_base_hashes = {
        path.stem: sha256(path) for path in sorted((base_dir / "stages").glob("*.pth"))
    }
    if config.get("base_stage_sha256s") != expected_base_hashes:
        raise ValueError(f"seed {seed}: base stage hashes differ")
    if config.get("asr_sha256") != expected_base_hashes["asr"]:
        raise ValueError(f"seed {seed}: ASR hash differs")
    if config.get("specified_after_completed_seeds") != [0, 1, 2]:
        raise ValueError(f"seed {seed}: post-hoc specification marker differs")
    if set(extension.get("models", {})) != MODELS:
        raise ValueError(f"seed {seed}: model set differs")

    prediction_path = extension_dir / "predictions.pth"
    predictions = torch.load(prediction_path, map_location="cpu", weights_only=False)
    targets = torch.as_tensor(predictions["targets"]).long().reshape(-1)
    base_targets = torch.as_tensor(base_predictions["targets"]).long().reshape(-1)
    if targets.numel() != 6_890 or not torch.equal(targets, base_targets):
        raise ValueError(f"seed {seed}: extension targets differ from base")
    if not set(targets.tolist()) <= {0, 1}:
        raise ValueError(f"seed {seed}: target label outside binary classes")
    if set(predictions.get("predictions", {})) != MODELS:
        raise ValueError(f"seed {seed}: prediction set differs")
    for model in sorted(MODELS):
        predicted = (
            torch.as_tensor(predictions["predictions"][model]).long().reshape(-1)
        )
        if predicted.numel() != targets.numel():
            raise ValueError(f"seed {seed}: {model} prediction count differs")
        if not set(predicted.tolist()) <= {0, 1}:
            raise ValueError(f"seed {seed}: {model} emitted a non-binary class")
        observed = 100.0 * float((predicted == targets).sum()) / targets.numel()
        recorded = float(extension["models"][model]["accuracy_sample_weighted"])
        if not math.isclose(observed, recorded, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"seed {seed}: {model} accuracy differs")

    checks = {
        "status": "passed",
        "base_complete_sha256": sha256(base_path),
        "base_predictions_sha256": base_checks["predictions_sha256"],
        "base_integrity_revalidated": True,
        "base_stage_sha256s": expected_base_hashes,
        "extension_complete_sha256": sha256(complete_path),
        "extension_config_sha256": sha256(config_path),
        "extension_predictions_sha256": sha256(prediction_path),
        "extension_checkpoint_sha256s": {
            model: sha256(extension_dir / f"{model}.pth") for model in sorted(MODELS)
        },
        "targets_equal_base": True,
        "n_targets": targets.numel(),
    }
    return (
        base,
        extension,
        {
            "checks": checks,
            "predictions": {"base": base_predictions, "extension": predictions},
        },
    )


def main() -> int:
    args = parse_args()
    seeds = {}
    for seed in range(5):
        loaded = validated_seed(
            args.base_root.resolve(), args.extension_root.resolve(), seed
        )
        if loaded is not None:
            seeds[seed] = loaded

    models = {
        model: {
            "accuracy": summarize(
                [
                    float(seeds[seed][1]["models"][model]["accuracy_sample_weighted"])
                    for seed in sorted(seeds)
                ]
            ),
            "cross_entropy": summarize(
                [
                    float(
                        seeds[seed][1]["models"][model]["cross_entropy_sample_weighted"]
                    )
                    for seed in sorted(seeds)
                ]
            ),
        }
        for model in sorted(MODELS)
    }

    comparisons = {}
    for label, (left_layer, left, right_layer, right) in COMPARISONS.items():
        differences = []
        tests = []
        for seed in sorted(seeds):
            base, extension, metadata = seeds[seed]
            layers = {"base": base, "extension": extension}
            differences.append(
                float(layers[left_layer]["models"][left]["accuracy_sample_weighted"])
                - float(
                    layers[right_layer]["models"][right]["accuracy_sample_weighted"]
                )
            )
            prediction_layers = metadata["predictions"]
            tests.append(
                {
                    "seed": seed,
                    **exact_mcnemar(
                        prediction_layers[left_layer]["predictions"][left],
                        prediction_layers[right_layer]["predictions"][right],
                        prediction_layers["extension"]["targets"],
                    ),
                }
            )
        comparisons[label] = {
            "accuracy_point_difference": summarize(differences),
            "per_seed_mcnemar_exact": tests,
        }

    runs = [
        {
            "run_id": f"loss-contract-seed-{seed}",
            "seed": seed,
            "models": seeds[seed][1]["models"],
            "integrity": seeds[seed][2]["checks"],
        }
        for seed in sorted(seeds)
    ]
    output = {
        "schema_version": "nulspec-sprkd-loss-contract-aggregate-v1",
        "status": "complete" if len(seeds) == 5 else "incomplete",
        "complete_seeds": sorted(seeds),
        "expected_seeds": list(range(5)),
        "interpretation_scope": (
            "Outcome-motivated post-hoc one-change diagnostic; cannot alter "
            "the preregistered replication verdict."
        ),
        "models": models,
        "comparisons": comparisons,
        "runs": runs,
        "integrity_checks": {
            str(seed): seeds[seed][2]["checks"] for seed in sorted(seeds)
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "loss_contract_extension_summary.json"
    json_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    with (args.output_dir / "loss_contract_extension_summary.csv").open(
        "w", newline=""
    ) as handle:
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
        "# Post-hoc supervised-logit results",
        "",
        f"Status: **{output['status']}** ({len(seeds)}/5 frozen seeds).",
        "",
        "This outcome-motivated diagnostic changes only the terminal activation "
        "so supervised `CrossEntropyLoss` receives logits. It cannot alter the "
        "preregistered verdict.",
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
            "## Run-level outcomes",
            "",
            "| Run | Logit Control-S | Logit SPRKD | Final SPRKD NHE count |",
            "|---|---:|---:|---:|",
        ]
    )
    for run in runs:
        state = (
            run["models"]["sprkd_logit_ce_random_init"]
            .get("diagnostic_metadata", {})
            .get("sprkd_final_state", {})
        )
        lines.append(
            f"| `{run['run_id']}` | "
            f"{fmt(run['models']['control_student_logit_ce']['accuracy_sample_weighted'])} | "
            f"{fmt(run['models']['sprkd_logit_ce_random_init']['accuracy_sample_weighted'])} | "
            f"{state.get('n_nhe_taken', '—')} |"
        )
    lines.append("")
    (args.output_dir / "LOSS_CONTRACT_EXTENSION_RESULTS.md").write_text(
        "\n".join(lines)
    )
    print(
        f"LOSS_CONTRACT_ANALYSIS status={output['status']} seeds={len(seeds)} "
        f"output={json_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

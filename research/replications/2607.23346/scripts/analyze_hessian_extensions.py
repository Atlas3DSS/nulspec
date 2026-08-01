#!/usr/bin/env python3
"""Validate and aggregate common-probe Hessian trace diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

from analyze_trials import fmt, sha256, summarize
from run_hessian_extensions import MODEL_STAGES, TESTSET_SHA256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--hessian-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def validated_seed(
    base_root: Path, hessian_root: Path, seed: int
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    base_path = base_root / f"seed-{seed}" / "complete.json"
    result_path = hessian_root / f"seed-{seed}" / "complete.json"
    config_path = hessian_root / f"seed-{seed}" / "config.json"
    if not result_path.is_file():
        return None
    if not base_path.is_file() or not config_path.is_file():
        raise FileNotFoundError(f"seed {seed}: missing base result or Hessian config")
    result = json.loads(result_path.read_text())
    config = json.loads(config_path.read_text())
    if result.get("complete") is not True or result.get("seed") != seed:
        raise ValueError(f"seed {seed}: invalid completion metadata")
    if result.get("schema_version") != "nulspec-sprkd-hessian-extension-v1":
        raise ValueError(f"seed {seed}: unexpected Hessian result schema")
    if result.get("config_sha256") != sha256(config_path):
        raise ValueError(f"seed {seed}: Hessian config hash differs")
    if config.get("base_complete_sha256") != sha256(base_path):
        raise ValueError(f"seed {seed}: base completion hash differs")
    expected_model_hashes = {
        model: sha256(base_root / f"seed-{seed}" / "stages" / f"{model}.pth")
        for model in MODEL_STAGES
    }
    if config.get("base_model_sha256s") != expected_model_hashes:
        raise ValueError(f"seed {seed}: base model checkpoint hashes differ")
    if config.get("testset_sha256") != TESTSET_SHA256:
        raise ValueError(f"seed {seed}: test-set hash differs")
    if config.get("n_probes") != 100 or config.get("probe_seed") != 100_000 + seed:
        raise ValueError(f"seed {seed}: probe configuration differs")
    if set(result.get("models", {})) != set(MODEL_STAGES):
        raise ValueError(f"seed {seed}: Hessian model set differs")

    for model in MODEL_STAGES:
        row = result["models"][model]
        probes = [float(value) for value in row.get("probe_values", [])]
        if len(probes) != 100 or not all(math.isfinite(value) for value in probes):
            raise ValueError(f"seed {seed}: {model} probes are invalid")
        if not math.isclose(
            float(row["trace_mean"]),
            statistics.fmean(probes),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"seed {seed}: {model} trace mean differs")
        if not math.isclose(
            float(row["probe_sample_sd"]),
            statistics.stdev(probes),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"seed {seed}: {model} probe SD differs")
    return result, {
        "status": "passed",
        "base_complete_sha256": sha256(base_path),
        "base_model_sha256s": expected_model_hashes,
        "config_sha256": sha256(config_path),
        "complete_sha256": sha256(result_path),
        "models": list(MODEL_STAGES),
        "probes_per_model": 100,
    }


def main() -> None:
    args = parse_args()
    seeds = {}
    checks = {}
    for seed in range(5):
        loaded = validated_seed(
            args.base_root.resolve(), args.hessian_root.resolve(), seed
        )
        if loaded is not None:
            seeds[seed], checks[str(seed)] = loaded

    models = {
        model: summarize(
            [float(seeds[seed]["models"][model]["trace_mean"]) for seed in seeds]
        )
        for model in MODEL_STAGES
    }
    comparison_pairs = {
        "exact_control_minus_sprkd": (
            "control_student",
            "sprkd_upstream_direct_init",
        ),
        "exact_rkd_minus_sprkd": (
            "rkd_upstream_asr_teacher",
            "sprkd_upstream_direct_init",
        ),
        "paper_intent_control_minus_sprkd": (
            "control_student",
            "sprkd_paper_random_init",
        ),
        "paper_intent_rkd_minus_sprkd": (
            "rkd_paper_weak_teacher",
            "sprkd_paper_random_init",
        ),
    }
    comparisons = {}
    for label, (left, right) in comparison_pairs.items():
        comparisons[label] = summarize(
            [
                float(seeds[seed]["models"][left]["trace_mean"])
                - float(seeds[seed]["models"][right]["trace_mean"])
                for seed in seeds
            ]
        )

    ordering = {
        "exact_sprkd_lower_than_both": [],
        "paper_intent_sprkd_lower_than_both": [],
        "exact_sprkd_lower_than_control_lower_than_rkd": [],
        "paper_intent_sprkd_lower_than_control_lower_than_rkd": [],
    }
    for seed in seeds:
        traces = {
            model: float(seeds[seed]["models"][model]["trace_mean"])
            for model in MODEL_STAGES
        }
        ordering["exact_sprkd_lower_than_both"].append(
            traces["sprkd_upstream_direct_init"] < traces["control_student"]
            and traces["sprkd_upstream_direct_init"]
            < traces["rkd_upstream_asr_teacher"]
        )
        ordering["paper_intent_sprkd_lower_than_both"].append(
            traces["sprkd_paper_random_init"] < traces["control_student"]
            and traces["sprkd_paper_random_init"] < traces["rkd_paper_weak_teacher"]
        )
        ordering["exact_sprkd_lower_than_control_lower_than_rkd"].append(
            traces["sprkd_upstream_direct_init"]
            < traces["control_student"]
            < traces["rkd_upstream_asr_teacher"]
        )
        ordering["paper_intent_sprkd_lower_than_control_lower_than_rkd"].append(
            traces["sprkd_paper_random_init"]
            < traces["control_student"]
            < traces["rkd_paper_weak_teacher"]
        )
    ordering_summary = {
        label: {
            "per_seed": values,
            "matching_seed_count": sum(values),
            "n": len(values),
        }
        for label, values in ordering.items()
    }

    output = {
        "schema_version": "nulspec-sprkd-hessian-aggregate-v1",
        "status": "complete" if len(seeds) == 5 else "incomplete",
        "complete_seeds": sorted(seeds),
        "expected_seeds": list(range(5)),
        "models": models,
        "paired_trace_differences": comparisons,
        "ordering": ordering_summary,
        "integrity_checks": checks,
        "runs": [
            {
                "run_id": f"hessian-seed-{seed}",
                "seed": seed,
                "models": {
                    model: {
                        key: seeds[seed]["models"][model][key]
                        for key in (
                            "trace_mean",
                            "probe_sample_sd",
                            "n_probes",
                            "elapsed_seconds",
                            "probe_values",
                        )
                    }
                    for model in MODEL_STAGES
                },
                "integrity": checks[str(seed)],
            }
            for seed in sorted(seeds)
        ],
        "interpretation_scope": (
            "Exploratory common-probe ordering on the fixed released 100-image "
            "batch; not numerically comparable to Table 1."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "hessian_extension_summary.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    with (args.output_dir / "hessian_extension_summary.csv").open(
        "w", newline=""
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["model", "n", "mean_trace", "sample_sd", "t95_low", "t95_high"]
        )
        for model in MODEL_STAGES:
            summary = models[model]
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
        "# Exploratory scratch-model Hessian traces",
        "",
        f"Status: **{output['status']}** ({len(seeds)}/5 frozen seeds).",
        "",
        "| Model | n | Mean trace | SD | 95% t interval |",
        "|---|---:|---:|---:|---:|",
    ]
    for model in MODEL_STAGES:
        summary = models[model]
        low, high = summary["t95_interval"]
        lines.append(
            f"| `{model}` | {summary['n']} | {fmt(summary['mean'])} | "
            f"{fmt(summary['sample_sd'])} | [{fmt(low)}, {fmt(high)}] |"
        )
    lines.extend(
        [
            "",
            "These are 100-probe estimates on the fixed released 100-image batch. "
            "They test ordering only and are not estimates of the paper's under-"
            "specified Table 1 values.",
            "",
            "## Run-level trace estimates",
            "",
            "| Run | Exact SPRKD | Intent SPRKD | Control-S | Exact RKD | Intent RKD |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for run in output["runs"]:
        run_models = run["models"]
        lines.append(
            f"| `{run['run_id']}` | "
            f"{fmt(run_models['sprkd_upstream_direct_init']['trace_mean'])} | "
            f"{fmt(run_models['sprkd_paper_random_init']['trace_mean'])} | "
            f"{fmt(run_models['control_student']['trace_mean'])} | "
            f"{fmt(run_models['rkd_upstream_asr_teacher']['trace_mean'])} | "
            f"{fmt(run_models['rkd_paper_weak_teacher']['trace_mean'])} |"
        )
    lines.append("")
    (args.output_dir / "HESSIAN_EXTENSION_RESULTS.md").write_text("\n".join(lines))
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

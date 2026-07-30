#!/usr/bin/env python3
"""Reconstruct the paper's aggregate z tests from its released result table."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def holm_adjust(p_values: list[float]) -> list[float]:
    """Return Holm-adjusted p-values in the input order."""
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    running_max = 0.0
    count = len(p_values)
    for rank, (index, p_value) in enumerate(ordered):
        candidate = min(1.0, (count - rank) * p_value)
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted


def audit(results_path: Path, sample_size: int) -> dict[str, Any]:
    payload = json.loads(results_path.read_text())
    rows: list[dict[str, Any]] = []

    for model, model_result in payload["our_models"].items():
        for dataset, result in model_result["datasets"].items():
            sft_mean = float(result["sft_reward_mean"])
            ppo_mean = float(result["ppo_reward_mean"])
            sft_std = float(result["sft_reward_std"])
            ppo_std = float(result["ppo_reward_std"])
            reported_delta = float(result["reward_delta"])
            delta = ppo_mean - sft_mean
            marginal_variance = sft_std**2 + ppo_std**2
            standard_error = math.sqrt(marginal_variance / sample_size)
            z_value = delta / standard_error
            p_value = math.erfc(abs(z_value) / math.sqrt(2.0))
            half_width = 1.96 * standard_error
            analytic_win_rate = normal_cdf(
                delta / math.sqrt(marginal_variance)
            )
            rows.append(
                {
                    "model": model,
                    "dataset": dataset,
                    "reported_delta": reported_delta,
                    "recomputed_delta": delta,
                    "delta_matches": math.isclose(
                        delta, reported_delta, abs_tol=1e-12
                    ),
                    "standard_error": standard_error,
                    "z": z_value,
                    "p_two_sided": p_value,
                    "ci95": [delta - half_width, delta + half_width],
                    "analytic_win_rate": analytic_win_rate,
                }
            )

    adjusted = holm_adjust([row["p_two_sided"] for row in rows])
    for row, adjusted_p in zip(rows, adjusted, strict=True):
        row["p_holm_15"] = adjusted_p
        row["significant_uncorrected_0_05"] = row["p_two_sided"] < 0.05
        row["significant_holm_0_05"] = adjusted_p < 0.05

    return {
        "schema_version": 1,
        "source": str(results_path),
        "sample_size_assumed": sample_size,
        "formula": {
            "delta": "ppo_mean - sft_mean",
            "standard_error": (
                "sqrt((sft_std^2 + ppo_std^2) / sample_size)"
            ),
            "ci95": "delta +/- 1.96 * standard_error",
            "p_two_sided": "2 * (1 - Phi(abs(delta / standard_error)))",
            "analytic_win_rate": (
                "Phi(delta / sqrt(sft_std^2 + ppo_std^2))"
            ),
        },
        "interpretation": (
            "These calculations use marginal means and standard deviations as "
            "if SFT and PPO scores were independent. They reproduce the "
            "released intervals and analytic win rates, but they are not a "
            "paired same-prompt analysis."
        ),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("paper_repro/SLM-RL-Agents/results/all_results.json"),
    )
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args()
    if args.sample_size <= 1:
        raise SystemExit("--sample-size must be greater than one")
    print(
        json.dumps(
            audit(args.results, args.sample_size),
            indent=args.indent,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

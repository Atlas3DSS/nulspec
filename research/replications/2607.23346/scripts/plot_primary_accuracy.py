#!/usr/bin/env python3
"""Plot run-level primary accuracies from the validated scratch summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SERIES = {
    "sprkd": {
        "label": "SPRKD",
        "color": "#009E73",
        "reported": 94.80,
    },
    "control": {
        "label": "Control-S",
        "color": "#4C566A",
        "reported": 94.47,
    },
    "rkd": {
        "label": "Response KD",
        "color": "#D55E00",
        "reported": 70.10,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def values(runs: list[dict[str, Any]], model: str) -> list[float]:
    return [float(run["models"][model]["accuracy_sample_weighted"]) for run in runs]


def panel(
    axis: Any,
    runs: list[dict[str, Any]],
    title: str,
    models: dict[str, str],
) -> None:
    seeds = [int(run["seed"]) for run in runs]
    for role, model in models.items():
        style = SERIES[role]
        axis.plot(
            seeds,
            values(runs, model),
            color=style["color"],
            linewidth=1.8,
            marker="o",
            markersize=5,
            label=style["label"],
        )
        axis.axhline(
            style["reported"],
            color=style["color"],
            linewidth=1,
            linestyle=(0, (2, 3)),
            alpha=0.55,
        )
    axis.set_title(title, loc="left", fontsize=11, fontweight="bold")
    axis.set_xticks(seeds)
    axis.set_xlabel("Frozen training seed")
    axis.set_ylim(45, 100)
    axis.grid(axis="y", color="#D8DEE9", linewidth=0.7)
    axis.spines[["top", "right"]].set_visible(False)


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text())
    if payload.get("status") != "complete" or payload.get("complete_seeds") != [
        0,
        1,
        2,
        3,
        4,
    ]:
        raise ValueError("scratch summary must contain all five frozen seeds")
    runs = sorted(payload["runs"], key=lambda run: int(run["seed"]))

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
        }
    )
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    panel(
        axes[0],
        runs,
        "A  Exact released-script path",
        {
            "sprkd": "sprkd_upstream_direct_init",
            "control": "control_student",
            "rkd": "rkd_upstream_asr_teacher",
        },
    )
    panel(
        axes[1],
        runs,
        "B  Narrow paper-intent reconstruction",
        {
            "sprkd": "sprkd_paper_random_init",
            "control": "control_student",
            "rkd": "rkd_paper_weak_teacher",
        },
    )
    axes[0].set_ylabel("Final full-validation accuracy (%)")
    axes[1].legend(frameon=False, loc="lower left", ncol=1)
    figure.suptitle(
        "SPRKD malaria replication: final accuracy varies sharply by seed",
        x=0.055,
        y=1.01,
        ha="left",
        fontsize=13,
        fontweight="bold",
    )
    figure.text(
        0.055,
        -0.02,
        "Solid lines are independent runs; matching dotted lines are the paper's reported five-trial means.",
        fontsize=8.5,
        color="#4C566A",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        args.output,
        dpi=180,
        bbox_inches="tight",
        metadata={"Software": "NULSPEC plot_primary_accuracy.py"},
    )
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

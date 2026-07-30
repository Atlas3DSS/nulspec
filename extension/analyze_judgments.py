from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


def parse_label_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, path = value.split("=", 1)
    return label, Path(path)


def load_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def summarize(records: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["pair_id"]].append(record)

    outcomes: list[str] = []
    inconsistent = 0
    incomplete = 0
    raw_a_wins = 0
    raw_b_wins = 0
    raw_ties = 0
    for pair_records in grouped.values():
        for record in pair_records:
            if record["winner"] == "A":
                raw_a_wins += 1
            elif record["winner"] == "B":
                raw_b_wins += 1
            else:
                raw_ties += 1
        by_orientation = {
            record["orientation"]: record
            for record in pair_records
        }
        if set(by_orientation) != {"sft_first", "ppo_first"}:
            incomplete += 1
            continue
        mapped = {
            by_orientation["sft_first"]["mapped_winner"],
            by_orientation["ppo_first"]["mapped_winner"],
        }
        if len(mapped) != 1:
            inconsistent += 1
            continue
        outcomes.append(mapped.pop())

    ppo_wins = outcomes.count("ppo")
    sft_wins = outcomes.count("sft")
    ties = outcomes.count("tie")
    scores = np.asarray(
        [1.0 if value == "ppo" else 0.0 if value == "sft" else 0.5
         for value in outcomes],
        dtype=np.float64,
    )
    if scores.size:
        rng = np.random.default_rng(42)
        indexes = rng.integers(
            0, scores.size, size=(10_000, scores.size)
        )
        interval = np.quantile(
            scores[indexes].mean(axis=1), [0.025, 0.975]
        )
        win_rate = float(scores.mean())
    else:
        interval = (float("nan"), float("nan"))
        win_rate = float("nan")
    non_ties = ppo_wins + sft_wins
    sign_p = (
        float(stats.binomtest(ppo_wins, non_ties, 0.5).pvalue)
        if non_ties
        else 1.0
    )
    total_raw = raw_a_wins + raw_b_wins + raw_ties
    return {
        "input_pairs": len(grouped),
        "position_consistent_pairs": len(outcomes),
        "position_inconsistent_pairs": inconsistent,
        "incomplete_pairs": incomplete,
        "ppo_wins": ppo_wins,
        "sft_wins": sft_wins,
        "ties": ties,
        "ppo_win_rate_ties_half": win_rate,
        "paired_bootstrap_95_ci": [
            float(interval[0]),
            float(interval[1]),
        ],
        "sign_test_pvalue": sign_p,
        "raw_a_choice_rate": raw_a_wins / total_raw if total_raw else None,
        "raw_b_choice_rate": raw_b_wins / total_raw if total_raw else None,
        "raw_tie_rate": raw_ties / total_raw if total_raw else None,
    }


def write_markdown(
    output: Path, summaries: dict[str, dict], calibration_label: str
) -> None:
    lines = [
        "# Independent Qwen-27B evaluation",
        "",
        "Every response pair was judged in both A/B orders. Only decisions "
        "that mapped to the same winner in both orders enter the paired "
        "effect estimate.",
        "",
        "| Arm | Consistent / total | PPO wins | SFT wins | Ties | PPO win "
        "rate (95% bootstrap CI) | p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, summary in summaries.items():
        if label == calibration_label:
            continue
        low, high = summary["paired_bootstrap_95_ci"]
        lines.append(
            f"| {label} | {summary['position_consistent_pairs']} / "
            f"{summary['input_pairs']} | {summary['ppo_wins']} | "
            f"{summary['sft_wins']} | {summary['ties']} | "
            f"{summary['ppo_win_rate_ties_half']:.3f} "
            f"[{low:.3f}, {high:.3f}] | "
            f"{summary['sign_test_pvalue']:.4f} |"
        )
    if calibration_label in summaries:
        calibration = summaries[calibration_label]
        lines.extend(
            [
                "",
                "## Judge calibration",
                "",
                "For calibration, `ppo` denotes the released chosen response "
                "and `sft` the rejected response.",
                "",
                f"- Position-consistent pairs: "
                f"{calibration['position_consistent_pairs']} / "
                f"{calibration['input_pairs']}",
                f"- Chosen-response preference: "
                f"{calibration['ppo_win_rate_ties_half']:.3f}",
                f"- Raw A-choice rate: "
                f"{calibration['raw_a_choice_rate']:.3f}",
            ]
        )
    output.write_text("\n".join(lines) + "\n")


def write_plot(path: Path, summaries: dict[str, dict], calibration: str) -> None:
    labels = [label for label in summaries if label != calibration]
    values = [summaries[label]["ppo_win_rate_ties_half"] for label in labels]
    intervals = [
        summaries[label]["paired_bootstrap_95_ci"] for label in labels
    ]
    lower = [value - interval[0] for value, interval in zip(values, intervals)]
    upper = [interval[1] - value for value, interval in zip(values, intervals)]
    colors = [
        "#00d4ff" if label.startswith("exact") else "#ff4f81"
        for label in labels
    ]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(labels))
    ax.bar(
        x,
        values,
        color=colors,
        yerr=np.asarray([lower, upper]),
        capsize=5,
    )
    ax.axhline(0.5, color="#2d3436", linestyle="--", linewidth=1.2)
    ax.set_ylim(0, 1)
    ax.set_xticks(x, labels, rotation=15, ha="right")
    ax.set_ylabel("Position-consistent PPO preference")
    ax.set_title("Independent Qwen-27B paired evaluation")
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--judgments",
        action="append",
        type=parse_label_path,
        required=True,
    )
    parser.add_argument("--calibration-label", default="calibration")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--plot", type=Path, required=True)
    args = parser.parse_args()

    summaries = {
        label: summarize(load_records(path))
        for label, path in args.judgments
    }
    payload = {
        "protocol": {
            "judge": "Qwen3.6 27B local llama.cpp route",
            "orientations_per_pair": 2,
            "position_inconsistent_policy": "exclude from effect estimate",
            "bootstrap_replicates": 10_000,
        },
        "arms": summaries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2))
    write_markdown(args.markdown, summaries, args.calibration_label)
    write_plot(args.plot, summaries, args.calibration_label)
    print(f"Wrote {args.output}, {args.markdown}, and {args.plot}")


if __name__ == "__main__":
    main()

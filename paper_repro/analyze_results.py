from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


ROOT = Path(__file__).resolve().parent
UPSTREAM_RESULTS = ROOT / "SLM-RL-Agents" / "results" / "all_results.json"
OUTPUTS = ROOT / "outputs"
CORRECTED_OUTPUTS = ROOT / "outputs_corrected"
LOGS = ROOT / "logs"
CORRECTED_LOGS = ROOT / "logs_corrected"
ARTIFACTS = ROOT / "artifacts"
MODELS = ("pythia-70m", "pythia-410m")
TRACE_PATTERN = re.compile(
    r"PPO_STEP (?P<step>\d+)/(?P<total>\d+) "
    r"reward=(?P<reward>-?[\d.]+) kl=(?P<kl>-?[\d.]+) "
    r"best=(?P<best>-?[\d.]+)"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def published_rows() -> list[dict]:
    raw = load_json(UPSTREAM_RESULTS)["our_models"]
    rows: list[dict] = []
    for model_name, model_data in raw.items():
        for dataset_name, metrics in model_data["datasets"].items():
            rows.append(
                {
                    "model": model_name,
                    "dataset": dataset_name,
                    "params_m": model_data["params_m"],
                    "sft_perplexity": metrics["sft_perplexity"],
                    "reward_delta": metrics["reward_delta"],
                }
            )
    return rows


def parse_trace(model: str, log_dir: Path) -> list[dict]:
    path = log_dir / f"{model}_tinystories_ppo.log"
    rows: list[dict] = []
    if not path.exists():
        return rows
    for match in TRACE_PATTERN.finditer(path.read_text(errors="replace")):
        rows.append(
            {
                "step": int(match["step"]),
                "total": int(match["total"]),
                "reward": float(match["reward"]),
                "kl": float(match["kl"]),
                "best": float(match["best"]),
            }
        )
    return rows


def ppo_diagnostics(model: str, log_dir: Path, trace: list[dict]) -> dict:
    log_path = log_dir / f"{model}_tinystories_ppo.log"
    log_text = log_path.read_text(errors="replace")
    kl_values = [row["kl"] for row in trace]
    rollback_count = log_text.count("rolling back")
    return {
        "finite_logged_updates": len(trace),
        "attempted_updates_including_rollbacks": len(trace) + rollback_count,
        "negative_kl_steps": sum(value < 0 for value in kl_values),
        "minimum_kl": min(kl_values),
        "maximum_kl": max(kl_values),
        "ratio_threshold_warning_count": log_text.count(
            "The average ratio of batch"
        ),
        "negative_kl_warning_count": log_text.count(
            "KL divergence is starting to become negative"
        ),
        "rollback_warning_count": rollback_count,
        "optimizer_reset_count": log_text.count("reset optimizer moments"),
        "too_many_rollbacks_stop_count": log_text.count("Too many rollbacks"),
        "early_stop_count": log_text.count("stopping early"),
    }


def run_metrics(model: str, corrected: bool = False) -> dict:
    output_dir = CORRECTED_OUTPUTS if corrected else OUTPUTS
    log_dir = CORRECTED_LOGS if corrected else LOGS
    run_root = output_dir / model / "tinystories"
    sft = load_json(run_root / "eval_sft" / "evaluation_results.json")["metrics"]
    ppo = load_json(run_root / "eval_ppo" / "evaluation_results.json")["metrics"]
    paired = load_json(run_root / "paired_eval.json")
    paper = load_json(UPSTREAM_RESULTS)["our_models"][model]["datasets"]["tinystories"]
    trace = parse_trace(model, log_dir)
    return {
        "paper": paper,
        "upstream_release_protocol": {
            "sft": sft,
            "ppo": ppo,
            "reward_delta": ppo["reward_mean"] - sft["reward_mean"],
        },
        "paired_seeded_protocol": paired,
        "ppo_trace": trace,
        "ppo_diagnostics": ppo_diagnostics(model, log_dir, trace),
    }


def plot_landscape(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    color_map = {
        "tinystories": "#00d4ff",
        "cnn_dailymail": "#ffb000",
        "wikitext": "#ff4f81",
    }
    for dataset in color_map:
        selected = [row for row in rows if row["dataset"] == dataset]
        ax.scatter(
            [row["sft_perplexity"] for row in selected],
            [row["reward_delta"] for row in selected],
            s=52,
            alpha=0.85,
            color=color_map[dataset],
            label=dataset.replace("_", " "),
        )
    for row in rows:
        if row["dataset"] == "tinystories" and row["model"] in MODELS:
            ax.annotate(
                row["model"].replace("pythia-", ""),
                (row["sft_perplexity"], row["reward_delta"]),
                xytext=(7, 7),
                textcoords="offset points",
                fontsize=9,
                weight="bold",
            )
    ax.axhline(0, color="#95a1b8", linewidth=1)
    ax.axvline(20, color="#f6e58d", linestyle="--", linewidth=1.5, label="paper threshold")
    ax.set_xscale("log")
    ax.set_xlabel("Released SFT reference-text perplexity (log scale)")
    ax.set_ylabel("Released PPO − SFT reward")
    ax.set_title("All 15 released configurations: capacity is necessary, not sufficient")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "paper_landscape.png", dpi=180)
    plt.close(fig)


def plot_precision_audit() -> None:
    audits = {
        "bfloat16": load_json(
            ARTIFACTS / "reward_batch_equivalence_410m.json"
        ),
        "float32": load_json(
            ARTIFACTS / "reward_batch_equivalence_410m_float32.json"
        ),
    }
    batch_sizes = ("2", "4", "8")
    x = np.arange(len(batch_sizes))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.6, 5.5))
    for offset, (dtype, audit) in enumerate(audits.items()):
        values = [
            audit["right_padded_batches"][size]["max_absolute_error"]
            for size in batch_sizes
        ]
        ax.bar(
            x + (offset - 0.5) * width,
            values,
            width,
            label=dtype,
            color="#ff4f81" if dtype == "bfloat16" else "#00d4ff",
        )
    ax.set_yscale("log")
    ax.set_xticks(x, [f"batch {size}" for size in batch_sizes])
    ax.set_ylabel("Max |batched − single-example reward| (log scale)")
    ax.set_title("410M reward inference is batch-shape sensitive in bfloat16")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "reward_precision_audit.png", dpi=180)
    plt.close(fig)


def plot_traces(results: dict, corrected_results: dict) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)
    colors = {"pythia-70m": "#ff4f81", "pythia-410m": "#00d4ff"}
    for model in MODELS:
        for series, linestyle, suffix in (
            (results, "-", "release code"),
            (corrected_results, "--", "paper-faithful"),
        ):
            trace = series[model]["ppo_trace"]
            steps = [row["step"] for row in trace]
            reward = [row["reward"] for row in trace]
            kl = [row["kl"] for row in trace]
            label = f"{model} · {suffix}"
            axes[0].plot(
                steps,
                reward,
                color=colors[model],
                linestyle=linestyle,
                alpha=0.82,
                label=label,
            )
            axes[1].plot(
                steps,
                kl,
                color=colors[model],
                linestyle=linestyle,
                alpha=0.82,
                label=label,
            )
    axes[0].set_ylabel("Batch reward")
    axes[1].set_ylabel("Objective KL")
    axes[1].set_xlabel("PPO step")
    axes[0].set_title("PPO telemetry by finite logged update")
    for ax in axes:
        ax.grid(alpha=0.18)
        ax.axhline(0, color="#95a1b8", linewidth=0.8)
        ax.legend(frameon=False)
    fig.text(
        0.01,
        0.005,
        "Reward scales are specific to each separately trained reward model; "
        "compare stability and within-run trends, not absolute height across protocols.",
        fontsize=8,
        color="#57606f",
    )
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(ARTIFACTS / "ppo_training_trace.png", dpi=180)
    plt.close(fig)


def plot_comparison(results: dict, corrected_results: dict) -> None:
    labels = ["70M", "410M"]
    paper_delta = [
        results[model]["paper"]["reward_delta"]
        for model in MODELS
    ]
    repro_delta = [
        results[model]["paired_seeded_protocol"]["reward"]["paired_delta_mean"]
        for model in MODELS
    ]
    intervals = [
        results[model]["paired_seeded_protocol"]["reward"]["paired_bootstrap_95_ci"]
        for model in MODELS
    ]
    corrected_delta = [
        corrected_results[model]["paired_seeded_protocol"]["reward"][
            "paired_delta_mean"
        ]
        for model in MODELS
    ]
    corrected_intervals = [
        corrected_results[model]["paired_seeded_protocol"]["reward"][
            "paired_bootstrap_95_ci"
        ]
        for model in MODELS
    ]
    lower = [value - interval[0] for value, interval in zip(repro_delta, intervals)]
    upper = [interval[1] - value for value, interval in zip(repro_delta, intervals)]
    corrected_lower = [
        value - interval[0]
        for value, interval in zip(corrected_delta, corrected_intervals)
    ]
    corrected_upper = [
        interval[1] - value
        for value, interval in zip(corrected_delta, corrected_intervals)
    ]

    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9.5, 5.9))
    ax.bar(x - width, paper_delta, width, color="#95a1b8", label="paper table")
    ax.bar(
        x,
        repro_delta,
        width,
        yerr=np.asarray([lower, upper]),
        capsize=5,
        color="#00d4ff",
        alpha=0.7,
        label="release-code paired rerun",
    )
    ax.bar(
        x + width,
        corrected_delta,
        width,
        yerr=np.asarray([corrected_lower, corrected_upper]),
        capsize=5,
        color="#ff4f81",
        hatch="//",
        label="paper-faithful paired rerun",
    )
    ax.axhline(0, color="#2d3436", linewidth=1)
    ax.set_xticks(x, labels)
    ax.set_ylabel("PPO − SFT reward")
    ax.set_title("Published claim versus independent paired rerun")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "reproduction_comparison.png", dpi=180)
    plt.close(fig)


def main() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    rows = published_rows()
    results = {model: run_metrics(model) for model in MODELS}
    corrected_results = {
        model: run_metrics(model, corrected=True)
        for model in MODELS
    }
    below_material = sum(
        row["sft_perplexity"] < 20 and row["reward_delta"] > 0.2
        for row in rows
    )
    below_not_material = sum(
        row["sft_perplexity"] < 20 and row["reward_delta"] <= 0.2
        for row in rows
    )
    above_material = sum(
        row["sft_perplexity"] >= 20 and row["reward_delta"] > 0.2
        for row in rows
    )
    above_not_material = sum(
        row["sft_perplexity"] >= 20 and row["reward_delta"] <= 0.2
        for row in rows
    )
    fisher = stats.fisher_exact(
        [
            [below_material, below_not_material],
            [above_material, above_not_material],
        ],
        alternative="greater",
    )
    summary = {
        "paper": {
            "arxiv": "2607.25091",
            "upstream_commit": "64acb621037c711395f2d77516bee70d8a49b819",
            "released_configuration_count": len(rows),
        },
        "released_landscape": {
            "ppl_below_20_count": sum(row["sft_perplexity"] < 20 for row in rows),
            "ppl_below_20_positive_delta_count": sum(
                row["sft_perplexity"] < 20 and row["reward_delta"] > 0
                for row in rows
            ),
            "ppl_above_20_positive_delta_count": sum(
                row["sft_perplexity"] >= 20 and row["reward_delta"] > 0
                for row in rows
            ),
            "material_gain_definition": "reward_delta > 0.2",
            "ppl_below_20_material_gain_count": below_material,
            "ppl_above_20_material_gain_count": above_material,
            "exploratory_one_sided_fisher_exact_pvalue": float(fisher.pvalue),
            "fisher_note": (
                "Descriptive only: the paper's PPL threshold and material-gain "
                "cutoff were not preregistered for this reanalysis."
            ),
            "rows": rows,
        },
        "reruns": results,
        "paper_faithful_followups": corrected_results,
    }
    (ARTIFACTS / "results_summary.json").write_text(json.dumps(summary, indent=2))
    plot_landscape(rows)
    plot_precision_audit()
    plot_traces(results, corrected_results)
    plot_comparison(results, corrected_results)
    print(
        f"Wrote {ARTIFACTS / 'results_summary.json'} and four figures "
        f"for {len(results) + len(corrected_results)} reruns."
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from scipy import stats
from transformers import AutoTokenizer

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))

from paper_repro.paired_eval import load_reward_model, score  # noqa: E402


def parse_arm(values: list[str]) -> tuple[str, Path, Path, Path]:
    label, reward, pairs, judgments = values
    return label, Path(reward), Path(pairs), Path(judgments)


def qwen_outcomes(path: Path) -> tuple[dict[str, str], int]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            grouped[record["pair_id"]].append(record)
    outcomes = {}
    inconsistent = 0
    for pair_id, records in grouped.items():
        orientations = {record["orientation"] for record in records}
        mapped = {record["mapped_winner"] for record in records}
        if orientations != {"sft_first", "ppo_first"} or len(mapped) != 1:
            inconsistent += 1
            continue
        outcomes[pair_id] = mapped.pop()
    return outcomes, inconsistent


def summarize_arm(
    reward_path: Path, pairs_path: Path, judgments_path: Path
) -> dict:
    source = json.loads(pairs_path.read_text())
    pairs = source["pairs"]
    tokenizer = AutoTokenizer.from_pretrained(
        reward_path, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = load_reward_model(reward_path, torch.float32)
    model.config.pad_token_id = tokenizer.pad_token_id
    prompts = [pair["prompt"] for pair in pairs]
    sft_scores = score(
        model, tokenizer, prompts, [pair["sft"] for pair in pairs], 1
    )
    ppo_scores = score(
        model, tokenizer, prompts, [pair["ppo"] for pair in pairs], 1
    )
    del model
    torch.cuda.empty_cache()

    outcomes, inconsistent = qwen_outcomes(judgments_path)
    deltas = ppo_scores - sft_scores
    rows = [
        (pair["pair_id"], float(delta), outcomes.get(pair["pair_id"]))
        for pair, delta in zip(pairs, deltas)
        if pair["pair_id"] in outcomes
    ]
    by_outcome = {}
    for outcome in ("ppo", "sft", "tie"):
        values = np.asarray(
            [delta for _, delta, value in rows if value == outcome],
            dtype=np.float64,
        )
        by_outcome[outcome] = {
            "pairs": int(values.size),
            "mean_reward_delta": (
                float(values.mean()) if values.size else None
            ),
            "median_reward_delta": (
                float(np.median(values)) if values.size else None
            ),
            "reward_prefers_ppo_rate": (
                float((values > 0).mean()) if values.size else None
            ),
        }

    directional = [
        (delta > 0) if outcome == "ppo" else (delta < 0)
        for _, delta, outcome in rows
        if outcome in {"ppo", "sft"}
    ]
    reward_direction = np.sign([delta for _, delta, _ in rows])
    qwen_direction = np.asarray(
        [
            1.0 if outcome == "ppo" else -1.0 if outcome == "sft" else 0.0
            for _, _, outcome in rows
        ]
    )
    correlation = (
        float(stats.spearmanr(reward_direction, qwen_direction).statistic)
        if len(set(reward_direction)) > 1
        and len(set(qwen_direction)) > 1
        else None
    )
    return {
        "pairs_scored": len(pairs),
        "qwen_position_consistent_pairs": len(rows),
        "qwen_position_inconsistent_or_incomplete_pairs": inconsistent,
        "reward_delta_mean": float(deltas.mean()),
        "reward_prefers_ppo_rate": float((deltas > 0).mean()),
        "qwen_non_tie_directional_pairs": len(directional),
        "reward_qwen_directional_agreement": (
            float(np.mean(directional)) if directional else None
        ),
        "reward_qwen_spearman_including_ties": correlation,
        "by_qwen_outcome": by_outcome,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare training-reward direction to independent Qwen."
    )
    parser.add_argument(
        "--arm",
        action="append",
        nargs=4,
        metavar=("LABEL", "REWARD_PATH", "PAIRS", "JUDGMENTS"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for raw_arm in args.arm:
        label, reward, pairs, judgments = parse_arm(raw_arm)
        print(f"Scoring reward/Qwen alignment: {label}")
        results[label] = summarize_arm(reward, pairs, judgments)
    payload = {
        "protocol": {
            "reward_dtype": "float32",
            "reward_scoring": "single example",
            "qwen_filter": "both A/B orders must map to the same outcome",
            "purpose": (
                "post-PPO diagnostic only; never used as training reward"
            ),
        },
        "arms": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

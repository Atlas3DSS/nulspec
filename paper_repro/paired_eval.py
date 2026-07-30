from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from peft import PeftConfig, PeftModel
from scipy import stats
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from reprolab.protocol import extract_prompt_reference


def load_policy(path: Path):
    adapter_config = path / "adapter_config.json"
    if adapter_config.exists():
        config = PeftConfig.from_pretrained(path)
        base = AutoModelForCausalLM.from_pretrained(
            config.base_model_name_or_path,
            torch_dtype=torch.float32,
            trust_remote_code=True,
        )
        return PeftModel.from_pretrained(base, path).merge_and_unload().cuda().eval()
    return (
        AutoModelForCausalLM.from_pretrained(
            path,
            torch_dtype=torch.float32,
            trust_remote_code=True,
        )
        .cuda()
        .eval()
    )


def generate(model, tokenizer, prompts: list[str], batch_size: int) -> list[str]:
    outputs: list[str] = []
    for offset in range(0, len(prompts), batch_size):
        batch = prompts[offset : offset + batch_size]
        encoded = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to("cuda")
        prompt_width = encoded.input_ids.shape[1]
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=96,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
        outputs.extend(
            tokenizer.batch_decode(
                generated[:, prompt_width:],
                skip_special_tokens=True,
            )
        )
    return [text.strip() for text in outputs]


def load_reward_model(path: Path, dtype: torch.dtype):
    adapter_config = path / "adapter_config.json"
    if adapter_config.exists():
        config = PeftConfig.from_pretrained(path)
        base = AutoModelForSequenceClassification.from_pretrained(
            config.base_model_name_or_path,
            torch_dtype=dtype,
            num_labels=1,
            trust_remote_code=True,
        )
        return PeftModel.from_pretrained(base, path).merge_and_unload().cuda().eval()
    return (
        AutoModelForSequenceClassification.from_pretrained(
            path,
            torch_dtype=dtype,
            num_labels=1,
            trust_remote_code=True,
        )
        .cuda()
        .eval()
    )


def score(
    model,
    tokenizer,
    prompts: list[str],
    responses: list[str],
    batch_size: int,
) -> np.ndarray:
    values: list[float] = []
    texts = [f"{p}\n\n{r}" for p, r in zip(prompts, responses)]
    for text_value in texts:
        encoded = tokenizer(
            text_value,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to("cuda")
        with torch.inference_mode():
            value = model(**encoded).logits[0, 0].float().cpu()
        values.append(float(value))
    return np.asarray(values, dtype=np.float64)


def distinct_n(texts: list[str], n: int) -> float:
    grams: list[tuple[str, ...]] = []
    for text in texts:
        words = text.lower().split()
        grams.extend(tuple(words[i : i + n]) for i in range(len(words) - n + 1))
    return len(set(grams)) / len(grams) if grams else 0.0


def paired_sign_flip_pvalue(
    differences: np.ndarray,
    *,
    replicates: int = 100_000,
    seed: int = 42,
) -> float:
    """Two-sided Monte Carlo paired randomization test."""
    observed = abs(float(differences.mean()))
    rng = np.random.default_rng(seed)
    exceedances = 0
    completed = 0
    chunk_size = 2_000
    while completed < replicates:
        count = min(chunk_size, replicates - completed)
        signs = rng.integers(
            0, 2, size=(count, len(differences)), dtype=np.int8
        )
        signs = signs * 2 - 1
        permuted = (signs * differences).mean(axis=1)
        exceedances += int((np.abs(permuted) >= observed).sum())
        completed += count
    return (exceedances + 1) / (replicates + 1)


def sample_id(index: int, prompt: str, sft: str, ppo: str) -> str:
    payload = f"{index}\0{prompt}\0{sft}\0{ppo}".encode()
    return hashlib.sha256(payload).hexdigest()[:24]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--eval-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--sft-path", type=Path)
    parser.add_argument("--ppo-path", type=Path)
    parser.add_argument("--reward-path", type=Path)
    parser.add_argument(
        "--reward-dtype",
        choices=("bfloat16", "float32"),
        default="bfloat16",
    )
    args = parser.parse_args()

    torch.manual_seed(1234)
    np.random.seed(1234)

    sft_path = args.sft_path or args.run_root / "sft" / "final"
    ppo_path = args.ppo_path or args.run_root / "ppo" / "final"
    reward_path = args.reward_path or args.run_root / "reward_model" / "final"

    raw = json.loads(args.eval_data.read_text())[:200]
    extracted = [extract_prompt_reference(row) for row in raw]
    prompts = [prompt for prompt, _ in extracted]

    tokenizer = AutoTokenizer.from_pretrained(sft_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    sft_model = load_policy(sft_path)
    sft_responses = generate(sft_model, tokenizer, prompts, args.batch_size)
    del sft_model
    torch.cuda.empty_cache()

    ppo_model = load_policy(ppo_path)
    ppo_responses = generate(ppo_model, tokenizer, prompts, args.batch_size)
    del ppo_model
    torch.cuda.empty_cache()

    reward_dtype = (
        torch.float32 if args.reward_dtype == "float32" else torch.bfloat16
    )
    reward_model = load_reward_model(reward_path, reward_dtype)
    reward_model.config.pad_token_id = tokenizer.pad_token_id
    sft_scores = score(
        reward_model, tokenizer, prompts, sft_responses, args.batch_size
    )
    ppo_scores = score(
        reward_model, tokenizer, prompts, ppo_responses, args.batch_size
    )

    differences = ppo_scores - sft_scores
    sample_count = len(differences)
    mean_difference = float(differences.mean())
    standard_error = float(stats.sem(differences))
    t_interval = stats.t.interval(
        0.95,
        sample_count - 1,
        loc=mean_difference,
        scale=standard_error,
    )

    rng = np.random.default_rng(42)
    indexes = rng.integers(0, sample_count, size=(10_000, sample_count))
    bootstrap_means = differences[indexes].mean(axis=1)
    bootstrap_interval = np.quantile(bootstrap_means, [0.025, 0.975])

    wins = int((differences > 0).sum())
    losses = int((differences < 0).sum())
    ties = sample_count - wins - losses
    non_ties = wins + losses
    sign_p = (
        float(stats.binomtest(wins, non_ties, 0.5).pvalue)
        if non_ties
        else 1.0
    )
    empirical_win_rate = (wins + 0.5 * ties) / sample_count
    permutation_pvalue = paired_sign_flip_pvalue(differences)
    identical_count = sum(
        sft == ppo for sft, ppo in zip(sft_responses, ppo_responses)
    )

    marginal_scale = math.sqrt(
        float(ppo_scores.var()) + float(sft_scores.var())
    )
    marginal_z = mean_difference / marginal_scale if marginal_scale else 0.0
    analytic_marginal_win_rate = float(stats.norm.cdf(marginal_z))

    result = {
        "protocol": {
            "samples": sample_count,
            "generation": "greedy paired generation",
            "max_new_tokens": 96,
            "bootstrap_replicates": 10_000,
            "sign_flip_replicates": 100_000,
            "reward_dtype": args.reward_dtype,
            "prompt_extraction": (
                "released evaluate.py extraction through "
                "reprolab.protocol.extract_prompt_reference"
            ),
        },
        "reward": {
            "sft_mean": float(sft_scores.mean()),
            "sft_std": float(sft_scores.std()),
            "ppo_mean": float(ppo_scores.mean()),
            "ppo_std": float(ppo_scores.std()),
            "paired_delta_mean": mean_difference,
            "paired_delta_std": float(differences.std(ddof=1)),
            "paired_t_95_ci": [float(t_interval[0]), float(t_interval[1])],
            "paired_t_pvalue": float(stats.ttest_rel(ppo_scores, sft_scores).pvalue),
            "paired_sign_flip_pvalue": permutation_pvalue,
            "paired_bootstrap_95_ci": [
                float(bootstrap_interval[0]),
                float(bootstrap_interval[1]),
            ],
            "empirical_wins": wins,
            "empirical_losses": losses,
            "empirical_ties": ties,
            "empirical_win_rate": empirical_win_rate,
            "sign_test_pvalue": sign_p,
            "paper_style_analytic_marginal_win_rate": analytic_marginal_win_rate,
        },
        "response_identity": {
            "count": identical_count,
            "rate": identical_count / sample_count,
        },
        "diversity": {
            "sft_distinct_1": distinct_n(sft_responses, 1),
            "sft_distinct_2": distinct_n(sft_responses, 2),
            "ppo_distinct_1": distinct_n(ppo_responses, 1),
            "ppo_distinct_2": distinct_n(ppo_responses, 2),
        },
        "samples": [
            {
                "sample_id": sample_id(index, prompt, sft_response, ppo_response),
                "index": index,
                "prompt": prompt,
                "sft": sft_response,
                "ppo": ppo_response,
                "sft_reward": float(sft_reward),
                "ppo_reward": float(ppo_reward),
                "reward_delta": float(delta),
            }
            for index, (
                prompt,
                sft_response,
                ppo_response,
                sft_reward,
                ppo_reward,
                delta,
            ) in enumerate(
                zip(
                    prompts,
                    sft_responses,
                    ppo_responses,
                    sft_scores,
                    ppo_scores,
                    differences,
                )
            )
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))


if __name__ == "__main__":
    main()

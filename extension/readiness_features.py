from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from peft import PeftConfig, PeftModel
from scipy.special import expit
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def parse_run(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=RUN_ROOT")
    label, path = value.split("=", 1)
    return label, Path(path)


def load_model(path: Path, dtype: torch.dtype):
    config = PeftConfig.from_pretrained(path)
    base = AutoModelForSequenceClassification.from_pretrained(
        config.base_model_name_or_path,
        torch_dtype=dtype,
        num_labels=1,
        trust_remote_code=True,
    )
    model = (
        PeftModel.from_pretrained(base, path)
        .merge_and_unload()
        .cuda()
        .eval()
    )
    return model


def sequential_scores(model, tokenizer, texts: list[str]) -> np.ndarray:
    scores: list[float] = []
    for text in texts:
        encoded = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to("cuda")
        with torch.inference_mode():
            scores.append(float(model(**encoded).logits[0, 0].float()))
    return np.asarray(scores, dtype=np.float64)


def batched_scores(
    model, tokenizer, texts: list[str], batch_size: int
) -> np.ndarray:
    scores: list[float] = []
    tokenizer.padding_side = "right"
    for offset in range(0, len(texts), batch_size):
        encoded = tokenizer(
            texts[offset : offset + batch_size],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to("cuda")
        with torch.inference_mode():
            scores.extend(
                model(**encoded).logits[:, 0].float().cpu().tolist()
            )
    return np.asarray(scores, dtype=np.float64)


def numeric_invariance(
    reward_path: Path,
    tokenizer,
    texts: list[str],
    dtype: torch.dtype,
) -> dict:
    model = load_model(reward_path, dtype)
    model.config.pad_token_id = tokenizer.pad_token_id
    sequential = sequential_scores(model, tokenizer, texts)
    batches = {}
    for batch_size in (2, 4, 8):
        batched = batched_scores(model, tokenizer, texts, batch_size)
        errors = np.abs(batched - sequential)
        batches[str(batch_size)] = {
            "max_absolute_error": float(errors.max()),
            "mean_absolute_error": float(errors.mean()),
        }
    del model
    torch.cuda.empty_cache()
    return batches


def reward_features(run_root: Path, rows: list[dict]) -> dict:
    reward_path = run_root / "reward_model" / "final"
    tokenizer = AutoTokenizer.from_pretrained(
        reward_path, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    chosen_texts = [
        f"{row['prompt']}\n\n{row['chosen']}" for row in rows
    ]
    rejected_texts = [
        f"{row['prompt']}\n\n{row['rejected']}" for row in rows
    ]

    model = load_model(reward_path, torch.float32)
    model.config.pad_token_id = tokenizer.pad_token_id
    chosen = sequential_scores(model, tokenizer, chosen_texts)
    rejected = sequential_scores(model, tokenizer, rejected_texts)
    del model
    torch.cuda.empty_cache()

    margins = chosen - rejected
    probabilities = expit(margins)
    subset = chosen_texts[:8]
    invariance = {
        "float32": numeric_invariance(
            reward_path, tokenizer, subset, torch.float32
        ),
        "bfloat16": numeric_invariance(
            reward_path, tokenizer, subset, torch.bfloat16
        ),
    }
    eval_path = run_root / "eval_sft" / "evaluation_results.json"
    sft_perplexity = None
    if eval_path.exists():
        sft_perplexity = json.loads(eval_path.read_text())["metrics"][
            "perplexity"
        ]
    return {
        "sft_reference_text_perplexity": sft_perplexity,
        "preference_pairs": len(rows),
        "reward_accuracy": float((margins > 0).mean()),
        "mean_chosen_minus_rejected_margin": float(margins.mean()),
        "median_margin": float(np.median(margins)),
        "margin_p10": float(np.quantile(margins, 0.1)),
        "mean_bradley_terry_chosen_probability": float(
            probabilities.mean()
        ),
        "brier_to_chosen": float(np.mean((probabilities - 1.0) ** 2)),
        "score_separation_cohens_d": float(
            margins.mean() / margins.std(ddof=1)
        ),
        "batch_shape_invariance": invariance,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", type=parse_run, required=True)
    parser.add_argument("--preference-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = json.loads(args.preference_data.read_text())
    result = {
        "protocol": {
            "features_measured_before_ppo": True,
            "reward_scoring": "single-example float32",
            "numeric_audit_examples": 8,
            "numeric_audit_batch_sizes": [2, 4, 8],
        },
        "arms": {},
    }
    for label, path in args.run:
        print(f"Auditing readiness: {label}")
        result["arms"][label] = reward_features(path, rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from peft import PeftConfig, PeftModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reward-model", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dtype", choices=("bfloat16", "float32"), default="bfloat16")
    args = parser.parse_args()

    dtype = torch.bfloat16 if args.dtype == "bfloat16" else torch.float32
    config = PeftConfig.from_pretrained(args.reward_model)
    tokenizer = AutoTokenizer.from_pretrained(args.reward_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForSequenceClassification.from_pretrained(
        config.base_model_name_or_path,
        torch_dtype=dtype,
        num_labels=1,
    )
    model = (
        PeftModel.from_pretrained(base, args.reward_model)
        .merge_and_unload()
        .cuda()
        .eval()
    )
    model.config.pad_token_id = tokenizer.pad_token_id

    rows = json.loads(args.data.read_text())[:8]
    texts = [f"{row['prompt']}\n\n{row['chosen']}" for row in rows]

    sequential: list[float] = []
    for item in texts:
        encoded = tokenizer(
            item,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to("cuda")
        with torch.inference_mode():
            sequential.append(float(model(**encoded).logits[0, 0].float()))

    batches: dict[str, dict] = {}
    for batch_size in (2, 4, 8):
        batched: list[float] = []
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
                values = model(**encoded).logits[:, 0].float().cpu().tolist()
            batched.extend(values)
        absolute_errors = [
            abs(one - batch)
            for one, batch in zip(sequential, batched)
        ]
        batches[str(batch_size)] = {
            "scores": batched,
            "absolute_errors": absolute_errors,
            "max_absolute_error": max(absolute_errors),
            "mean_absolute_error": sum(absolute_errors) / len(absolute_errors),
            "all_exact": all(error == 0 for error in absolute_errors),
        }

    result = {
        "samples": len(texts),
        "dtype": args.dtype,
        "sequential": sequential,
        "right_padded_batches": batches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))

from paper_repro.paired_eval import generate, load_policy  # noqa: E402


def pair_id(index: int, prompt: str, sft: str, ppo: str) -> str:
    payload = f"{index}\0{prompt}\0{sft}\0{ppo}".encode()
    return hashlib.sha256(payload).hexdigest()[:24]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--sft-path", type=Path, required=True)
    parser.add_argument("--ppo-path", type=Path, required=True)
    parser.add_argument("--eval-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        existing = json.loads(args.output.read_text())
        if len(existing.get("pairs", [])) == args.samples:
            print(f"Reusing {args.output} ({args.samples} pairs)")
            return
        raise SystemExit(f"{args.output} exists but is incomplete; pass --force")

    torch.manual_seed(1234)
    np.random.seed(1234)

    rows = json.loads(args.eval_data.read_text())[: args.samples]
    prompts = [row["text"][:200] for row in rows]
    tokenizer = AutoTokenizer.from_pretrained(
        args.sft_path, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    sft_model = load_policy(args.sft_path)
    sft_responses = generate(
        sft_model, tokenizer, prompts, args.batch_size
    )
    del sft_model
    torch.cuda.empty_cache()

    ppo_model = load_policy(args.ppo_path)
    ppo_responses = generate(
        ppo_model, tokenizer, prompts, args.batch_size
    )
    del ppo_model
    torch.cuda.empty_cache()

    pairs = [
        {
            "pair_id": pair_id(index, prompt, sft, ppo),
            "index": index,
            "prompt": prompt,
            "sft": sft,
            "ppo": ppo,
            "expected_winner": None,
        }
        for index, (prompt, sft, ppo) in enumerate(
            zip(prompts, sft_responses, ppo_responses)
        )
    ]
    result = {
        "label": args.label,
        "protocol": {
            "samples": len(pairs),
            "generation": "greedy",
            "max_new_tokens": 96,
            "prompt_extraction": "first 200 characters",
            "seed": 1234,
        },
        "checkpoints": {
            "sft": str(args.sft_path.resolve()),
            "ppo": str(args.ppo_path.resolve()),
        },
        "pairs": pairs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(f"Wrote {len(pairs)} complete pairs to {args.output}")


if __name__ == "__main__":
    main()

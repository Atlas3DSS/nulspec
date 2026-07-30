from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260730)
    args = parser.parse_args()

    rows = json.loads(args.data.read_text())
    indexes = random.Random(args.seed).sample(
        range(len(rows)), args.samples
    )
    pairs = []
    for output_index, source_index in enumerate(indexes):
        row = rows[source_index]
        digest = hashlib.sha256(
            f"calibration\0{source_index}\0{row['prompt']}".encode()
        ).hexdigest()[:24]
        pairs.append(
            {
                "pair_id": digest,
                "index": output_index,
                "source_index": source_index,
                "prompt": row["prompt"],
                # Reuse the SFT/PPO role names so the generic judge can run.
                "sft": row["rejected"],
                "ppo": row["chosen"],
                "expected_winner": "ppo",
            }
        )
    payload = {
        "label": "calibration",
        "protocol": {
            "samples": len(pairs),
            "source": str(args.data.resolve()),
            "selection_seed": args.seed,
            "role_mapping": "sft=rejected, ppo=chosen",
        },
        "pairs": pairs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(pairs)} calibration pairs to {args.output}")


if __name__ == "__main__":
    main()

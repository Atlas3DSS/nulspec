from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "SLM-RL-Agents" / "results" / "all_results.json"


def main() -> None:
    payload = json.loads(RESULTS.read_text())
    for model in ("pythia-70m", "pythia-410m"):
        row = payload["our_models"][model]["datasets"]["tinystories"]
        z_value = row["reward_delta"] / math.sqrt(
            row["sft_reward_std"] ** 2 + row["ppo_reward_std"] ** 2
        )
        analytic_win_rate = 0.5 * (1.0 + math.erf(z_value / math.sqrt(2.0)))
        print(
            model,
            f"sft_ppl={row['sft_perplexity']}",
            f"reward_delta={row['reward_delta']:+.3f}",
            f"analytic_win_rate={analytic_win_rate:.3f}",
        )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_label_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=LOG_PATH")
    label, path = value.split("=", 1)
    return label, Path(path)


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def summarize(path: Path) -> dict:
    text = path.read_text(errors="replace")
    healthy_steps = [
        int(value)
        for value in re.findall(r"^PPO_STEP (\d+)/\d+", text, re.MULTILINE)
    ]
    corruption_indexes = [
        int(value)
        for value in re.findall(
            r"Step (\d+): weights corrupted after PPO step", text
        )
    ]
    attempted = len(healthy_steps) + len(corruption_indexes)
    ratio_warnings = count(
        r"average ratio of batch .* exceeds threshold", text
    )
    negative_kl_warnings = count(
        r"KL divergence is starting to become negative", text
    )
    completed_target = bool(
        healthy_steps and max(healthy_steps) == 250
    )
    strict_integrity_pass = (
        completed_target
        and not corruption_indexes
        and ratio_warnings == 0
        and negative_kl_warnings / max(attempted, 1) <= 0.01
    )
    return {
        "healthy_updates": len(healthy_steps),
        "attempted_updates": attempted,
        "last_healthy_progress_number": (
            max(healthy_steps) if healthy_steps else 0
        ),
        "corrupted_updates_rolled_back": len(corruption_indexes),
        "ratio_threshold_warnings": ratio_warnings,
        "negative_kl_warnings": negative_kl_warnings,
        "optimizer_resets": count(r"reset optimizer moments", text),
        "rollback_stop": "Too many rollbacks" in text,
        "kl_early_stop": "KL diverged to" in text,
        "completed_target": completed_target,
        "strict_integrity_pass": strict_integrity_pass,
        "log": str(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", action="append", type=parse_label_path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "protocol": {
            "attempted_updates": "healthy updates plus rolled-back updates",
            "warning_counts": "regex counts over raw PPO logs",
            "strict_integrity_pass": (
                "target completed, zero corruptions, zero ratio-threshold "
                "warnings, and negative-KL warnings at most 1% of attempts"
            ),
        },
        "arms": {
            label: summarize(path) for label, path in args.log
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

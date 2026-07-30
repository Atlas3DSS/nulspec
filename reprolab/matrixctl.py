from __future__ import annotations

import argparse
import json
from pathlib import Path

from reprolab.protocol import (
    CONFIG_PATH,
    MATRIX_PATH,
    WORKSPACE,
    Arm,
    load_arms,
    load_config,
    validate_matrix,
)


def run_glob(arm: Arm, workspace: Path) -> list[Path]:
    base = workspace / "paper_repro" / "full_matrix_runs" / arm.arm_id
    return sorted(base.glob("attempt-*")) if base.exists() else []


def arm_status(arm: Arm, workspace: Path) -> str:
    attempts = run_glob(arm, workspace)
    if any((attempt / "run.complete.json").is_file() for attempt in attempts):
        return "complete"
    if attempts:
        return "attempted"
    return "pending"


def arm_command(arm: Arm, gpu: str, expected_gpu: str) -> str:
    return (
        "bash scripts/run_guarded_2607_25091_arm.sh "
        f"{arm.arm_id} '{gpu}' '{expected_gpu}'"
    )


def select_arm(arms: list[Arm], arm_id: str) -> Arm:
    matches = [arm for arm in arms if arm.arm_id == arm_id]
    if len(matches) != 1:
        raise SystemExit(f"unknown or duplicate arm: {arm_id}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("validate", "list", "show", "command")
    )
    parser.add_argument("--arm")
    parser.add_argument("--gpu")
    parser.add_argument("--expected-gpu")
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    args = parser.parse_args()

    config = load_config(args.config)
    arms = load_arms(args.matrix)
    errors = validate_matrix(config, arms)
    if errors:
        raise SystemExit("\n".join(errors))

    if args.action == "validate":
        print(f"valid: {len(arms)} arms")
        return

    if args.action == "list":
        for arm in arms:
            print(
                f"{arm_status(arm, args.workspace):10} "
                f"{arm.arm_id:45} seed={arm.seed}"
            )
        return

    if not args.arm:
        raise SystemExit("--arm is required")
    arm = select_arm(arms, args.arm)
    if args.action == "show":
        payload = {
            **arm.__dict__,
            "status": arm_status(arm, args.workspace),
            "model_config": config["models"][arm.model],
            "track_config": config["tracks"][arm.track],
            "training": config["training"],
        }
        print(json.dumps(payload, indent=2))
        return

    if not args.gpu or not args.expected_gpu:
        raise SystemExit("--gpu and --expected-gpu are required")
    print(arm_command(arm, args.gpu, args.expected_gpu))


if __name__ == "__main__":
    main()

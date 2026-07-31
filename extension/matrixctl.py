from __future__ import annotations

import argparse
import json
from pathlib import Path

MODELS = {
    "pythia-70m": {
        "host": "workstation",
        "gpu_selector": "0",
        "expected_gpu": "RTX 4090",
    },
    "pythia-160m": {
        "host": "workstation",
        "gpu_selector": "0",
        "expected_gpu": "RTX 4090",
    },
    "pythia-410m": {
        "host": "shared-host",
        "gpu_selector": "GPU-d739b9c5-bfbb-e95a-bbf1-7122f38c2cf1",
        "expected_gpu": "RTX PRO 6000",
    },
}
SEEDS = (42, 123, 777)
PROTOCOLS = ("exact", "paper-faithful")


def arms() -> list[dict]:
    result = []
    for model, hardware in MODELS.items():
        for seed in SEEDS:
            for protocol in PROTOCOLS:
                existing_run_root = None
                if seed == 42 and model in {"pythia-70m", "pythia-410m"}:
                    output_root = (
                        "outputs"
                        if protocol == "exact"
                        else "outputs_corrected"
                    )
                    existing_run_root = (
                        f"paper_repro/{output_root}/{model}/tinystories"
                    )
                result.append(
                    {
                        "arm_id": f"{model}-seed{seed}-{protocol}",
                        "model": model,
                        "seed": seed,
                        "protocol": protocol,
                        **hardware,
                        "depends_on": (
                            f"{model}-seed{seed}-exact"
                            if protocol == "paper-faithful"
                            else None
                        ),
                        "existing_run_root": existing_run_root,
                    }
                )
    return result


def arm_command(arm: dict) -> str:
    command = (
        "bash extension/run_matrix_arm.sh "
        f"{arm['model']} {arm['seed']} {arm['protocol']} "
        f"'{arm['gpu_selector']}' '{arm['expected_gpu']}'"
    )
    if arm["host"] == "shared-host":
        return (
            'ssh -tt "${NULSPEC_SHARED_HOST:?set NULSPEC_SHARED_HOST}" '
            '"cd ${NULSPEC_REMOTE_REPO_ROOT:?set NULSPEC_REMOTE_REPO_ROOT} && '
            "systemd-run --user --scope -p MemoryHigh=12G "
            "-p MemoryMax=16G -p CPUQuota=800% nice -n 10 "
            f"ionice -c 2 -n 7 {command}\""
        )
    return (
        "systemd-run --user --scope -p MemoryHigh=24G "
        "-p MemoryMax=32G -p CPUQuota=1200% nice -n 10 "
        f"ionice -c 2 -n 7 {command}"
    )


def arm_complete(workspace: Path, arm: dict) -> bool:
    if arm["existing_run_root"]:
        existing = workspace / arm["existing_run_root"]
        if (existing / "paired_eval.json").exists():
            return True
    root = (
        workspace
        / "extension"
        / "matrix_runs"
        / f"seed-{arm['seed']}"
        / arm["protocol"]
        / arm["model"]
        / "tinystories"
    )
    return (root / "paired_eval.json").exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("list", "write-plan", "command"))
    parser.add_argument("--arm")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()

    plan = arms()
    if args.action == "write-plan":
        if args.output is None:
            raise SystemExit("--output is required")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"arms": plan}, indent=2))
        print(f"Wrote {len(plan)} arms to {args.output}")
        return
    if args.action == "command":
        selected = next(
            (arm for arm in plan if arm["arm_id"] == args.arm), None
        )
        if selected is None:
            raise SystemExit("unknown --arm")
        print(arm_command(selected))
        return
    for arm in plan:
        status = "complete" if arm_complete(args.workspace, arm) else "pending"
        print(f"{status:8} {arm['arm_id']:42} {arm['host']}")


if __name__ == "__main__":
    main()

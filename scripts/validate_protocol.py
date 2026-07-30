from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

WORKSPACE_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_PATH))

from reprolab.protocol import (
    CONFIG_PATH,
    MATRIX_PATH,
    WORKSPACE,
    load_arms,
    load_config,
    sha256_file,
    validate_matrix,
    verify_data,
)


def git_output(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        default=WORKSPACE / "paper_repro" / "data_release",
    )
    parser.add_argument(
        "--upstream",
        type=Path,
        default=WORKSPACE / "paper_repro" / "SLM-RL-Agents",
    )
    parser.add_argument("--skip-data", action="store_true")
    parser.add_argument("--skip-upstream", action="store_true")
    args = parser.parse_args()

    config = load_config(CONFIG_PATH)
    arms = load_arms(MATRIX_PATH)
    errors = validate_matrix(config, arms)

    patch_path = WORKSPACE / config["upstream"]["patch"]
    if not patch_path.is_file():
        errors.append(f"missing reproduction patch: {patch_path}")
    else:
        actual_patch_hash = sha256_file(patch_path)
        expected_patch_hash = config["upstream"]["patch_sha256"]
        if actual_patch_hash != expected_patch_hash:
            errors.append(
                "reproduction patch hash mismatch: "
                f"{actual_patch_hash} != {expected_patch_hash}"
            )

    if not args.skip_data:
        errors.extend(verify_data(args.data_root))

    if not args.skip_upstream:
        if not (args.upstream / ".git").exists():
            errors.append(f"missing upstream checkout: {args.upstream}")
        else:
            revision = git_output(args.upstream, "rev-parse", "HEAD")
            expected = config["upstream"]["revision"]
            if revision != expected:
                errors.append(
                    f"upstream revision mismatch: {revision} != {expected}"
                )
            results_path = args.upstream / "results" / "all_results.json"
            if not results_path.is_file():
                errors.append(
                    f"missing upstream result table: {results_path}"
                )
            else:
                actual_results_hash = sha256_file(results_path)
                expected_results_hash = config["upstream"][
                    "results_sha256"
                ]
                if actual_results_hash != expected_results_hash:
                    errors.append(
                        "upstream result hash mismatch: "
                        f"{actual_results_hash} != {expected_results_hash}"
                    )

    summary = {
        "protocol": config["protocol_version"],
        "arms": len(arms),
        "data_checked": not args.skip_data,
        "upstream_checked": not args.skip_upstream,
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()

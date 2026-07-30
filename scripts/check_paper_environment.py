from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED = {
    "torch": "2.5.1+cu121",
    "transformers": "4.45.2",
    "trl": "0.9.6",
    "peft": "0.18.1",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "python": sys.version,
        "executable": sys.executable,
        "packages": {},
        "cli": {},
        "cuda": {},
        "errors": [],
    }
    for package, expected in EXPECTED.items():
        try:
            module = importlib.import_module(package)
            actual = str(getattr(module, "__version__", "unknown"))
            result["packages"][package] = {
                "expected": expected,
                "actual": actual,
                "match": actual == expected,
            }
            if actual != expected:
                result["errors"].append(
                    f"{package}: expected {expected}, found {actual}"
                )
        except Exception as error:
            result["packages"][package] = {
                "expected": expected,
                "error": f"{type(error).__name__}: {error}",
            }
            result["errors"].append(f"{package}: import failed")

    for script in (
        "train_sft.py",
        "train_reward.py",
        "train_ppo.py",
        "evaluate.py",
    ):
        completed = subprocess.run(
            [
                sys.executable,
                str(args.upstream / "scripts" / script),
                "--help",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        result["cli"][script] = {
            "exit_code": completed.returncode,
            "stderr_tail": completed.stderr[-2000:],
        }
        if completed.returncode:
            result["errors"].append(f"{script}: --help failed")

    try:
        import torch

        result["cuda"] = {
            "available": torch.cuda.is_available(),
            "build": torch.version.cuda,
        }
        if torch.cuda.is_available():
            value = torch.ones(1, device="cuda") + 1
            result["cuda"].update(
                {
                    "gpu": torch.cuda.get_device_name(0),
                    "capability": list(torch.cuda.get_device_capability(0)),
                    "kernel_smoke_value": float(value.item()),
                }
            )
    except Exception as error:
        result["cuda"] = {
            "error": f"{type(error).__name__}: {error}",
        }
        result["errors"].append("CUDA smoke test failed")

    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    raise SystemExit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()

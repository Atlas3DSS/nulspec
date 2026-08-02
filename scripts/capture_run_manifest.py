from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import distributions
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "command": command,
            "error": f"{type(error).__name__}: {error}",
        }


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_memory() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, raw = line.split(":", maxsplit=1)
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                values[f"{key}_kib"] = int(raw.strip().split()[0])
    except (OSError, ValueError):
        pass
    return values


def git_state(path: Path) -> dict[str, Any]:
    if not (path / ".git").exists():
        return {"present": False}
    head = run(["git", "rev-parse", "HEAD"], cwd=path)
    status = run(["git", "status", "--porcelain=v1"], cwd=path)
    diff = run(["git", "diff", "--binary"], cwd=path)
    diff_text = str(diff.get("stdout", ""))
    return {
        "present": True,
        "head": head.get("stdout"),
        "dirty": bool(status.get("stdout")),
        "status": status.get("stdout", "").splitlines(),
        "working_tree_diff_sha256": hashlib.sha256(diff_text.encode()).hexdigest(),
    }


def parse_gpu_csv(text: str) -> list[dict[str, str]]:
    keys = [
        "index",
        "uuid",
        "name",
        "memory_total_mib",
        "memory_used_mib",
        "utilization_gpu_percent",
        "driver_version",
    ]
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        values = [part.strip() for part in line.split(",")]
        if len(values) == len(keys):
            rows.append(dict(zip(keys, values)))
    return rows


def capture_packages() -> dict[str, Any]:
    pip_freeze = run([sys.executable, "-m", "pip", "freeze", "--all"])
    if pip_freeze.get("exit_code") == 0:
        return {
            "packages": str(pip_freeze.get("stdout", "")).splitlines(),
            "method": "pip-freeze-all",
            "exit_code": 0,
            "pip_freeze_exit_code": 0,
            "pip_freeze_stderr": str(pip_freeze.get("stderr", "")),
        }
    try:
        packages = sorted(
            {
                f"{name}=={distribution.version}"
                for distribution in distributions()
                if (name := distribution.metadata.get("Name"))
            },
            key=str.casefold,
        )
    except Exception as error:  # pragma: no cover - defensive trace capture
        return {
            "packages": [],
            "method": "failed",
            "exit_code": 1,
            "pip_freeze_exit_code": pip_freeze.get("exit_code"),
            "pip_freeze_stderr": str(
                pip_freeze.get("stderr", pip_freeze.get("error", ""))
            ),
            "fallback_error": f"{type(error).__name__}: {error}",
        }
    return {
        "packages": packages,
        "method": "importlib-metadata-fallback",
        "exit_code": 0,
        "pip_freeze_exit_code": pip_freeze.get("exit_code"),
        "pip_freeze_stderr": str(pip_freeze.get("stderr", pip_freeze.get("error", ""))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--phase", choices=("start", "end"), required=True)
    parser.add_argument("--protocol-version", required=True)
    parser.add_argument("--paper-id", default="2607.25091")
    parser.add_argument("--invocation", default="")
    parser.add_argument("--exit-code", type=int)
    parser.add_argument(
        "--upstream",
        type=Path,
        default=WORKSPACE / "paper_repro" / "SLM-RL-Agents",
    )
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"refusing to overwrite manifest: {args.output}")

    gpu_query = run(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,name,memory.total,memory.used,"
            "utilization.gpu,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    package_capture = capture_packages()
    cpu_model = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", maxsplit=1)[1].strip()
                break
    except OSError:
        pass

    selected_environment = {
        key: os.environ[key]
        for key in (
            "CUDA_VISIBLE_DEVICES",
            "CUDA_DEVICE_ORDER",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "PYTORCH_CUDA_ALLOC_CONF",
            "TOKENIZERS_PARALLELISM",
        )
        if key in os.environ
    }

    payload: dict[str, Any] = {
        "schema_version": 1,
        "arm_id": args.arm_id,
        "phase": args.phase,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": args.protocol_version,
        "invocation": shlex.split(args.invocation) if args.invocation else [],
        "exit_code": args.exit_code,
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "cpu_model": cpu_model,
            "logical_cpu_count": os.cpu_count(),
            "memory": read_memory(),
            "gpus": parse_gpu_csv(str(gpu_query.get("stdout", ""))),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "packages": package_capture["packages"],
            "package_capture_method": package_capture["method"],
            "package_capture_exit_code": package_capture["exit_code"],
            "pip_freeze_exit_code": package_capture["pip_freeze_exit_code"],
            "pip_freeze_stderr": package_capture["pip_freeze_stderr"],
            **(
                {"package_fallback_error": package_capture["fallback_error"]}
                if "fallback_error" in package_capture
                else {}
            ),
        },
        "environment": selected_environment,
        "repository": git_state(WORKSPACE),
        "upstream": git_state(args.upstream),
        "protocol_files": {
            "config_sha256": sha256(
                WORKSPACE / "protocols" / args.paper_id / "config.json"
            ),
            "matrix_sha256": sha256(
                WORKSPACE / "protocols" / args.paper_id / "matrix.csv"
            ),
            "data_manifest_sha256": sha256(
                WORKSPACE / "protocols" / args.paper_id / "data_manifest.json"
            ),
            "source_manifest_sha256": sha256(
                WORKSPACE / "protocols" / args.paper_id / "SOURCE_MANIFEST.json"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Write an append-only Python package/environment inventory."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
import json
import platform
from pathlib import Path
import re
import sys
from typing import Any


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def encoded_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def package_records() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for distribution in distributions():
        name = distribution.metadata.get("Name")
        if not name:
            continue
        record = {
            "name": str(name),
            "normalized_name": normalized_name(str(name)),
            "version": str(distribution.version),
        }
        direct_url = distribution.read_text("direct_url.json")
        if direct_url is not None:
            record["direct_url_sha256"] = sha256_bytes(direct_url.encode("utf-8"))
        records.append(record)
    return sorted(
        records,
        key=lambda record: (
            record["normalized_name"],
            record["version"],
            record.get("direct_url_sha256", ""),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lockfile", type=Path)
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite environment inventory: {output}")
    lockfile = args.lockfile.expanduser().resolve() if args.lockfile else None
    if lockfile is not None and not lockfile.is_file():
        raise SystemExit(f"lockfile is missing: {lockfile}")

    packages = package_records()
    packages_payload = encoded_json(packages)
    executable = Path(sys.executable).resolve()
    payload = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "capture_method": "importlib.metadata",
        "python": {
            "executable": str(executable),
            "executable_bytes": executable.stat().st_size,
            "executable_sha256": sha256_file(executable),
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "lockfile": (
            {
                "basename": lockfile.name,
                "bytes": lockfile.stat().st_size,
                "sha256": sha256_file(lockfile),
            }
            if lockfile is not None
            else None
        ),
        "package_count": len(packages),
        "packages_sha256": sha256_bytes(packages_payload),
        "packages": packages,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(encoded_json(payload))
    print(output)


if __name__ == "__main__":
    main()

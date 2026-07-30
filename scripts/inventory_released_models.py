#!/usr/bin/env python3
"""Verify the frozen Hugging Face model-repository inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi


def records(repo_id: str, revision: str) -> list[dict[str, Any]]:
    info = HfApi().model_info(
        repo_id,
        revision=revision,
        files_metadata=True,
    )
    output: list[dict[str, Any]] = []
    for sibling in info.siblings:
        output.append(
            {
                "path": sibling.rfilename,
                "size": sibling.size,
                "blob_id": sibling.blob_id,
                "lfs_sha256": (
                    sibling.lfs["sha256"] if sibling.lfs else None
                ),
            }
        )
    output.sort(key=lambda row: row["path"])
    return output


def canonical_digest(rows: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "protocols/2607.25091/released_model_manifest.json"
        ),
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = records(manifest["repository"], manifest["revision"])
    observed = {
        "file_count": len(rows),
        "total_bytes": sum(row["size"] for row in rows),
        "lfs_count": sum(row["lfs_sha256"] is not None for row in rows),
        "lfs_bytes": sum(
            row["size"] for row in rows if row["lfs_sha256"] is not None
        ),
        "canonical_sha256": canonical_digest(rows),
    }
    expected = manifest["repository_inventory"]
    errors = [
        f"{key}: expected {expected[key]!r}, observed {value!r}"
        for key, value in observed.items()
        if expected[key] != value
    ]

    by_path = {row["path"]: row for row in rows}
    for checkpoint in manifest["checkpoints"]:
        path = checkpoint["path"]
        if path not in by_path:
            errors.append(f"missing checkpoint: {path}")
            continue
        actual = by_path[path]
        for key in ("size", "lfs_sha256"):
            if checkpoint[key] != actual[key]:
                errors.append(
                    f"{path} {key}: expected {checkpoint[key]!r}, "
                    f"observed {actual[key]!r}"
                )

    output = {
        "repository": manifest["repository"],
        "revision": manifest["revision"],
        "observed": observed,
        "checkpoint_count": len(manifest["checkpoints"]),
        "errors": errors,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()

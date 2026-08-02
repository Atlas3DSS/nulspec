#!/usr/bin/env python3
"""Build an append-only, path-private content index for an artifact tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IndexError(RuntimeError):
    """Raised when a tree cannot be indexed without ambiguity."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_index(root: Path, *, created_at_utc: str | None = None) -> dict[str, Any]:
    """Return a deterministic file index without serializing the local root path."""

    if root.is_symlink():
        raise IndexError("artifact root must not be a symlink")
    root = root.resolve()
    if not root.is_dir():
        raise IndexError("artifact root must be an existing directory")

    candidates = sorted(
        root.rglob("*"),
        key=lambda path: path.relative_to(root).as_posix().encode("utf-8"),
    )
    records: list[dict[str, Any]] = []
    record_stream = hashlib.sha256()
    total_bytes = 0
    for path in candidates:
        relative_path = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise IndexError(f"artifact tree contains a symlink: {relative_path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise IndexError(
                f"artifact tree contains a non-regular file: {relative_path}"
            )
        if "\t" in relative_path or "\n" in relative_path or "\r" in relative_path:
            raise IndexError("artifact path contains a forbidden control character")
        byte_count = path.stat().st_size
        digest = sha256_file(path)
        record_stream.update(
            f"{relative_path}\t{byte_count}\t{digest}\n".encode("utf-8")
        )
        records.append(
            {
                "relative_path": relative_path,
                "bytes": byte_count,
                "sha256": digest,
            }
        )
        total_bytes += byte_count

    return {
        "schema_version": 1,
        "created_at_utc": created_at_utc or utc_now(),
        "root_basename": root.name,
        "content_index": {
            "algorithm": "sha256-utf8-relative-path-tab-bytes-tab-file-sha256-newline-v1",
            "file_count": len(records),
            "total_bytes": total_bytes,
            "records_sha256": record_stream.hexdigest(),
        },
        "files": records,
    }


def write_new(path: Path, payload: bytes) -> None:
    path = path.expanduser().resolve()
    if not path.parent.is_dir():
        raise IndexError("output parent must be an existing directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise IndexError("refusing to overwrite an existing index") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.root.is_symlink():
        raise SystemExit("artifact root must not be a symlink")
    root = args.root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise SystemExit("output must be outside the indexed tree")

    try:
        index = build_index(root)
        write_new(output, canonical_bytes(index))
    except IndexError as error:
        raise SystemExit(str(error)) from error
    print(
        json.dumps(
            {
                "output_basename": output.name,
                "output_sha256": sha256_file(output),
                **index["content_index"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

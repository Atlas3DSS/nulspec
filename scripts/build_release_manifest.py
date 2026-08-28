#!/usr/bin/env python3
"""Create the deterministic manifest for the static NULSPEC journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MANIFEST_NAME = "release.json"
SITE_MODE = "journal"
POST_PATH = "/blog/scheduling-is-all-you-need/"


class ManifestError(Exception):
    """Raised when a static output cannot become a release."""


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def files_below(directory: Path) -> list[Path]:
    files: list[Path] = []
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ManifestError(f"static output contains a symlink: {path}")
        if path.is_file() and path != directory / MANIFEST_NAME:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(directory).as_posix())


def tree_digest(directory: Path, files: list[Path]) -> str:
    tree = hashlib.sha256()
    for path in files:
        relative = path.relative_to(directory).as_posix()
        tree.update(f"{sha256(path.read_bytes())}  {relative}\n".encode())
    return tree.hexdigest()


def health_target(static_directory: Path, path: str) -> Path:
    if path == "/":
        return static_directory / "index.html"
    if path.endswith("/"):
        return static_directory / path.removeprefix("/") / "index.html"
    return static_directory / path.removeprefix("/")


def atomic_write(path: Path, content: bytes) -> None:
    handle, temporary = tempfile.mkstemp(prefix=".release-manifest-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def build_manifest(static_directory: Path, commit: str) -> dict[str, Any]:
    if not COMMIT.fullmatch(commit):
        raise ManifestError("commit must be a full lowercase Git SHA")
    if not static_directory.is_dir():
        raise ManifestError(f"static output does not exist: {static_directory}")

    health_paths = [
        "/",
        POST_PATH,
        f"{POST_PATH}manifest.json",
        "/release.json",
    ]
    for path in health_paths:
        if path == "/release.json":
            continue
        if not health_target(static_directory, path).is_file():
            raise ManifestError(f"journal health path is absent: {path}")

    files = files_below(static_directory)
    return {
        "schema_version": 1,
        "site_mode": SITE_MODE,
        "git_commit": commit,
        "tree_sha256": tree_digest(static_directory, files),
        "file_count": len(files),
        "health_paths": health_paths,
        "publications": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-dir", type=Path, default=ROOT / "out")
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    static_directory = args.static_dir.resolve()
    try:
        manifest = build_manifest(static_directory, args.commit)
        content = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        atomic_write(static_directory / MANIFEST_NAME, content)
    except (ManifestError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(f"NULSPEC_RELEASE_MANIFEST_FAILED: {exc}")
        return 1
    print(
        "NULSPEC_RELEASE_MANIFEST_READY "
        f"mode={manifest['site_mode']} commit={manifest['git_commit']} "
        f"files={manifest['file_count']} tree={manifest['tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

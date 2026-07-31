#!/usr/bin/env python3
"""Create the deterministic manifest embedded in a static NULSPEC release."""

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


def load_publications() -> list[tuple[dict[str, Any], bytes]]:
    publications: list[tuple[dict[str, Any], bytes]] = []
    for path in sorted((ROOT / "site-data/publications").glob("study-*.json")):
        raw = path.read_bytes()
        value = json.loads(raw)
        if value.get("publication_status") != "ready":
            raise ManifestError(f"publication is not ready: {path.name}")
        publications.append((value, raw))
    if not publications:
        raise ManifestError("no ready publication bundles found")
    return publications


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
    publications = load_publications()
    health_paths = {"/", "/release.json"}
    publication_records = []
    for bundle, raw in publications:
        study_id = bundle["study"]["id"]
        health_paths.add(f"/studies/{study_id}/")
        for artifact in bundle["artifacts"]:
            health_paths.add(f"/{artifact['public_path']}")
        publication_records.append(
            {
                "study_id": study_id,
                "study_title": bundle["study"]["title"],
                "paper": bundle["study"]["paper"],
                "classification": bundle["verdict"]["classification"],
                "bundle_sha256": sha256(raw),
                "evidence_revision": bundle["source"]["evidence_revision"],
                "extension_vote": bundle["extension_call_to_action"],
            }
        )
    for path in health_paths - {"/release.json"}:
        if not health_target(static_directory, path).is_file():
            raise ManifestError(f"health path is absent from static output: {path}")
    files = files_below(static_directory)
    return {
        "schema_version": 1,
        "git_commit": commit,
        "tree_sha256": tree_digest(static_directory, files),
        "file_count": len(files),
        "health_paths": sorted(health_paths),
        "publications": publication_records,
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
    except (ManifestError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"NULSPEC_RELEASE_MANIFEST_FAILED: {exc}")
        return 1
    print(
        "NULSPEC_RELEASE_MANIFEST_READY "
        f"commit={manifest['git_commit']} files={manifest['file_count']} "
        f"tree={manifest['tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

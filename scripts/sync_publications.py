#!/usr/bin/env python3
"""Validate pending typed handoffs and import authorized publications.

This is the build-time bridge between research-owned website handoffs and the
public site. Pending review states are compatibility-checked but remain absent
from public output. An authorized handoff is imported from the exact Git commit
being built.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from import_accuracy_publication import (
    FULL_GIT_SHA,
    HANDOFF_SCHEMA,
    ImportError,
    import_accuracy_publication,
)


def repository_head(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else ""
        raise ImportError(f"cannot resolve the build revision: {detail or exc}") from exc
    revision = result.stdout.strip()
    if not FULL_GIT_SHA.fullmatch(revision):
        raise ImportError("the build revision is not a full Git commit SHA")
    return revision


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportError(f"cannot read typed handoff {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ImportError(f"typed handoff must be a JSON object: {path}")
    return value


def assert_pending_output_absent(root: Path, study_id: str) -> None:
    bundle = root / "site-data" / "publications" / f"study-{study_id}.json"
    artifacts = root / "public" / "studies" / study_id
    present = [path.relative_to(root).as_posix() for path in (bundle, artifacts) if path.exists()]
    if present:
        raise ImportError(
            "review-blocked study has public output: " + ", ".join(present)
        )


def sync_publications(root: Path) -> tuple[int, int]:
    revision = repository_head(root)
    checked = 0
    imported = 0
    handoffs = sorted((root / "research" / "replications").glob("*/WEBSITE_HANDOFF.json"))
    for handoff_path in handoffs:
        handoff = load_json(handoff_path)
        if handoff.get("schema_version") != HANDOFF_SCHEMA:
            continue

        study = handoff.get("study")
        study_id = study.get("id") if isinstance(study, dict) else None
        review = handoff.get("final_peer_review")
        authorized = (
            isinstance(review, dict) and review.get("publication_authorized") is True
        )
        import_accuracy_publication(
            handoff_path=handoff_path,
            source_root=handoff_path.parent,
            site_root=root,
            evidence_revision=revision,
            check_only=not authorized,
        )
        if authorized:
            imported += 1
        else:
            if not isinstance(study_id, str):
                raise ImportError(f"typed handoff has no valid study ID: {handoff_path}")
            assert_pending_output_absent(root, study_id)
            checked += 1

    return checked, imported


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    try:
        checked, imported = sync_publications(root)
    except (ImportError, OSError, TypeError, KeyError, ValueError) as exc:
        print(f"NULSPEC_PUBLICATION_SYNC_FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        "NULSPEC_PUBLICATION_SYNC_OK "
        f"pending_compatible={checked} authorized_imported={imported}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

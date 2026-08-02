#!/usr/bin/env python3
"""Import one validated NULSPEC publication bundle without recursive copying."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")
STUDY_ID = re.compile(r"^[0-9]{3,}$")
FORBIDDEN_KEYS = {
    "email",
    "gpu_uuid",
    "hostname",
    "ip_address",
    "private_key",
    "secret",
    "token",
}
PRIVATE_TEXT = re.compile(
    r"(?:/" + r"home/|/Users/|[A-Za-z]:\\Users\\|BEGIN [A-Z ]*PRIVATE KEY|"
    r"(?:api|access|auth)[_-]?token\s*[=:]|GPU-[0-9a-f-]{36}|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)


class ImportError(Exception):
    """Raised when an import would violate the public boundary."""


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_bundle(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ImportError(f"cannot read bundle: {exc}") from exc
    if len(raw) > 2_000_000:
        raise ImportError("bundle exceeds 2 MB")
    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImportError(f"invalid bundle JSON: {exc}") from exc
    if not isinstance(bundle, dict):
        raise ImportError("bundle must contain an object")
    return bundle, raw


def verify_public_value(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise ImportError(f"forbidden public key at {path}.{key}")
            verify_public_value(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            verify_public_value(child, f"{path}[{index}]")
    elif isinstance(value, str) and PRIVATE_TEXT.search(value):
        raise ImportError(f"private or unrelated operational text at {path}")


def safe_relative(value: str, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("."):
        raise ImportError(f"unsafe {label}: {value}")
    return path


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".nulspec-import-", dir=path.parent)
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


def import_publication(bundle_path: Path, source_root: Path, site_root: Path) -> None:
    bundle, raw_bundle = load_bundle(bundle_path)
    verify_public_value(bundle)
    if bundle.get("schema_version") != 1:
        raise ImportError("schema_version must be 1")
    if bundle.get("publication_status") != "ready":
        raise ImportError("only ready bundles may be imported")
    study = bundle.get("study")
    if not isinstance(study, dict) or not isinstance(study.get("id"), str):
        raise ImportError("study.id is missing")
    study_id = study["id"]
    if not STUDY_ID.fullmatch(study_id):
        raise ImportError("study.id must contain at least three digits")
    completion = bundle.get("completion")
    if not isinstance(completion, dict):
        raise ImportError("completion is missing")
    registered = completion.get("registered_arms")
    if not (
        isinstance(registered, int)
        and registered == completion.get("terminal_arms")
        and registered == completion.get("claim_ready_arms")
        and registered == len(bundle.get("arms", []))
    ):
        raise ImportError("completion counts are not closed")
    gates = completion.get("gates")
    if not isinstance(gates, dict) or not gates or not all(gates.values()):
        raise ImportError("all completion gates must be true")

    frozen = bundle.get("frozen_primary_result")
    if not (
        isinstance(frozen, dict)
        and frozen.get("registered_arms") == registered
        and frozen.get("claim_ready_arms") == registered
        and frozen.get("may_be_rewritten_by_extension") is False
    ):
        raise ImportError("frozen primary result does not match completion")

    extension = bundle.get("extension_call_to_action")
    if not (
        isinstance(extension, dict)
        and extension.get("requested") is True
        and extension.get("implementation_owner") == "website_team"
        and extension.get("button_label") == "Vote to extend this paper"
        and isinstance(extension.get("prompt"), str)
        and extension["prompt"].strip()
        and len(extension["prompt"]) <= 300
        and extension.get("selection_mode") == "single_choice"
        and isinstance(extension.get("options"), list)
        and 1 <= len(extension["options"]) <= 12
    ):
        raise ImportError("extension vote contract is missing or malformed")
    extension_ids: set[str] = set()
    extension_priorities: set[int] = set()
    for option in extension["options"]:
        if not isinstance(option, dict):
            raise ImportError("extension options must be objects")
        option_id = option.get("id")
        priority = option.get("priority")
        if not (
            isinstance(option_id, str)
            and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", option_id)
            and option_id not in extension_ids
            and isinstance(option.get("label"), str)
            and option["label"].strip()
            and len(option["label"]) <= 120
            and isinstance(option.get("role"), str)
            and option["role"].strip()
            and len(option["role"]) <= 120
            and isinstance(priority, int)
            and not isinstance(priority, bool)
            and priority >= 1
            and priority not in extension_priorities
            and isinstance(option.get("summary"), str)
            and option["summary"].strip()
            and len(option["summary"]) <= 700
        ):
            raise ImportError(f"invalid extension option: {option_id}")
        extension_ids.add(option_id)
        extension_priorities.add(priority)

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list):
        raise ImportError("artifacts must be an array")
    roles: set[str] = set()
    destinations: set[str] = set()
    staged: list[tuple[Path, bytes]] = []
    source_root = source_root.resolve()
    public_root = (site_root / "public").resolve()
    prefix = f"studies/{study_id}/artifacts/"
    for item in artifacts:
        if not isinstance(item, dict):
            raise ImportError("artifact entries must be objects")
        role = item.get("role")
        if not isinstance(role, str) or role in roles:
            raise ImportError(f"missing or duplicate artifact role: {role}")
        roles.add(role)
        source_relative = safe_relative(item.get("path", ""), "artifact path")
        public_value = item.get("public_path", "")
        public_relative = safe_relative(public_value, "artifact public_path")
        if not public_value.startswith(prefix) or public_value.endswith("/"):
            raise ImportError(f"artifact public_path is outside {prefix}: {public_value}")
        if public_value in destinations:
            raise ImportError(f"duplicate artifact public_path: {public_value}")
        destinations.add(public_value)
        digest = item.get("sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ImportError(f"invalid artifact digest for {role}")
        source = (source_root / Path(*source_relative.parts)).resolve()
        if source_root not in source.parents or not source.is_file():
            raise ImportError(f"artifact source is unavailable: {source_relative}")
        content = source.read_bytes()
        if sha256(content) != digest:
            raise ImportError(f"artifact digest mismatch: {source_relative}")
        media_type = item.get("media_type")
        if isinstance(media_type, str) and (
            media_type.startswith("text/") or media_type in {"application/json", "application/yaml"}
        ):
            if PRIVATE_TEXT.search(content.decode("utf-8", errors="replace")):
                raise ImportError(f"private or unrelated operational text in {source_relative}")
        destination = (public_root / Path(*public_relative.parts)).resolve()
        if public_root not in destination.parents:
            raise ImportError(f"artifact destination escaped public root: {public_value}")
        staged.append((destination, content))

    required = {
        "result_summary",
        "full_report",
        "machine_analysis",
        "extension_roadmap",
        "website_handoff",
    }
    if not required.issubset(roles):
        raise ImportError("ready bundle is missing required public artifact roles")

    bundle_destination = site_root / "site-data" / "publications" / f"study-{study_id}.json"
    for destination, content in staged:
        atomic_write(destination, content)
    atomic_write(bundle_destination, raw_bundle)
    print(
        "NULSPEC_PUBLICATION_IMPORTED "
        f"study={study_id} arms={registered} bundle_sha256={sha256(raw_bundle)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--site-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        import_publication(
            args.bundle.resolve(), args.source_root.resolve(), args.site_root.resolve()
        )
    except (ImportError, OSError, TypeError) as exc:
        print(f"NULSPEC_PUBLICATION_IMPORT_FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

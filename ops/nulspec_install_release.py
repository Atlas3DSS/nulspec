#!/usr/bin/env python3
"""Install one validated static NULSPEC archive and atomically switch Caddy."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import BinaryIO, Iterator


RELEASE_ROOT = Path("/srv/nulspec/releases")
CURRENT_LINK = Path("/srv/nulspec/current")
LOCK_PATH = Path("/run/lock/nulspec-deploy.lock")
MANIFEST_NAME = "release.json"
PUBLIC_HOST = "nulspec.com"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_MEMBERS = 20_000
COMMIT = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
STUDY_ID = re.compile(r"^[0-9]{3,}$")
CLASSIFICATIONS = {
    "REPRODUCED",
    "PARTIALLY_REPRODUCED",
    "NOT_REPRODUCED",
    "INCONCLUSIVE",
}


class DeployError(Exception):
    """Raised when a release fails validation or activation."""


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_archive() -> bytes:
    archive = sys.stdin.buffer.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise DeployError("release archive exceeds 64 MiB")
    if not archive:
        raise DeployError("release archive is empty")
    return archive


def normalized_member(member: tarfile.TarInfo) -> PurePosixPath | None:
    if "\\" in member.name:
        raise DeployError(f"archive member uses a backslash: {member.name}")
    value = PurePosixPath(member.name)
    if member.name in {".", "./"}:
        return None
    if value.is_absolute() or ".." in value.parts or not value.parts:
        raise DeployError(f"unsafe archive member path: {member.name}")
    if len(value.as_posix()) > 512:
        raise DeployError("archive member path exceeds 512 characters")
    return value


def unpack_archive(archive: bytes, staging: Path) -> None:
    try:
        stream = tarfile.open(fileobj=BytesIO(archive), mode="r:")
    except tarfile.TarError as exc:
        raise DeployError(f"release is not a plain tar archive: {exc}") from exc
    with stream:
        members = stream.getmembers()
        if len(members) > MAX_MEMBERS:
            raise DeployError("release archive has too many members")
        expanded = sum(member.size for member in members if member.isfile())
        if expanded > MAX_EXPANDED_BYTES:
            raise DeployError("expanded release exceeds 256 MiB")
        seen: set[str] = set()
        for member in members:
            relative = normalized_member(member)
            if relative is None:
                continue
            normalized = relative.as_posix()
            if normalized in seen:
                raise DeployError(f"duplicate archive member: {normalized}")
            seen.add(normalized)
            if not (member.isdir() or member.isfile()):
                raise DeployError(f"unsupported archive member type: {normalized}")
            destination = staging.joinpath(*relative.parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True, mode=0o755)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            source: BinaryIO | None = stream.extractfile(member)
            if source is None:
                raise DeployError(f"cannot read archive member: {normalized}")
            with source, destination.open("xb") as output:
                shutil.copyfileobj(source, output)
            if destination.stat().st_size != member.size:
                raise DeployError(f"truncated archive member: {normalized}")
            destination.chmod(0o644)


def release_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise DeployError(f"release contains a symlink: {path}")
        if path.is_file() and path != directory / MANIFEST_NAME:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(directory).as_posix())


def tree_digest(directory: Path, files: list[Path]) -> str:
    tree = hashlib.sha256()
    for path in files:
        relative = path.relative_to(directory).as_posix()
        tree.update(f"{sha256(path.read_bytes())}  {relative}\n".encode())
    return tree.hexdigest()


def health_target(directory: Path, path: str) -> Path:
    if path == "/":
        return directory / "index.html"
    if path.endswith("/"):
        return directory / path.removeprefix("/") / "index.html"
    return directory / path.removeprefix("/")


def validate_release(directory: Path) -> dict[str, object]:
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.stat().st_size > 128 * 1024:
        raise DeployError("release manifest is missing or oversized")
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise DeployError(f"cannot read release manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise DeployError("release manifest schema_version must be 1")
    site_mode = manifest.get("site_mode", "research")
    if site_mode not in {"journal", "placeholder", "research"}:
        raise DeployError("release manifest has an invalid site mode")
    commit = manifest.get("git_commit")
    expected_tree = manifest.get("tree_sha256")
    expected_count = manifest.get("file_count")
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise DeployError("release manifest has an invalid Git commit")
    if not isinstance(expected_tree, str) or not DIGEST.fullmatch(expected_tree):
        raise DeployError("release manifest has an invalid tree digest")
    if not isinstance(expected_count, int) or expected_count < 1:
        raise DeployError("release manifest has an invalid file count")
    files = release_files(directory)
    if len(files) != expected_count:
        raise DeployError(
            f"release file count mismatch: expected {expected_count}, got {len(files)}"
        )
    actual_tree = tree_digest(directory, files)
    if actual_tree != expected_tree:
        raise DeployError(
            f"release tree mismatch: expected {expected_tree}, got {actual_tree}"
        )
    health_paths = manifest.get("health_paths")
    if not isinstance(health_paths, list) or not health_paths:
        raise DeployError("release manifest has no health paths")
    if "/" not in health_paths or "/release.json" not in health_paths:
        raise DeployError("release health paths omit required endpoints")
    for path in health_paths:
        if (
            not isinstance(path, str)
            or not path.startswith("/")
            or ".." in PurePosixPath(path).parts
            or "\r" in path
            or "\n" in path
        ):
            raise DeployError(f"unsafe health path: {path!r}")
        if not health_target(directory, path).is_file():
            raise DeployError(f"health path is absent from release: {path}")
    publications = manifest.get("publications")
    if site_mode in {"journal", "placeholder"}:
        if publications != []:
            raise DeployError(
                f"{site_mode} release must not contain publication provenance"
            )
    if site_mode == "placeholder":
        if len(health_paths) != 2 or set(health_paths) != {"/", "/release.json"}:
            raise DeployError(
                "placeholder release health paths must contain only required endpoints"
            )
        return manifest
    if site_mode == "journal":
        post_path = "/blog/scheduling-is-all-you-need/"
        if post_path not in health_paths:
            raise DeployError("journal release health paths omit the H3 post")
        return manifest
    if not isinstance(publications, list) or not publications:
        raise DeployError("release manifest has no publication provenance")
    seen_studies: set[str] = set()
    for publication in publications:
        if not isinstance(publication, dict):
            raise DeployError("release publication provenance must contain objects")
        study_id = publication.get("study_id")
        if (
            not isinstance(study_id, str)
            or not STUDY_ID.fullmatch(study_id)
            or study_id in seen_studies
        ):
            raise DeployError("release has an invalid or duplicate study ID")
        seen_studies.add(study_id)
        if not DIGEST.fullmatch(str(publication.get("bundle_sha256", ""))):
            raise DeployError(f"release has an invalid bundle digest for study {study_id}")
        if not COMMIT.fullmatch(str(publication.get("evidence_revision", ""))):
            raise DeployError(f"release has an invalid evidence revision for study {study_id}")
        if publication.get("classification") not in CLASSIFICATIONS:
            raise DeployError(f"release has an invalid classification for study {study_id}")
        paper = publication.get("paper")
        if not (
            isinstance(paper, dict)
            and isinstance(paper.get("title"), str)
            and str(paper.get("url", "")).startswith("https://arxiv.org/abs/")
        ):
            raise DeployError(f"release has invalid paper metadata for study {study_id}")
        result_notice = publication.get("result_notification")
        expected_study_url = f"https://nulspec.com/studies/{study_id}/"
        expected_artifact_prefix = f"{expected_study_url}artifacts/"
        full_report_url = str(
            result_notice.get("full_report_url", "")
            if isinstance(result_notice, dict)
            else ""
        )
        if not (
            isinstance(result_notice, dict)
            and result_notice.get("study_url") == expected_study_url
            and full_report_url.startswith(expected_artifact_prefix)
            and ".." not in PurePosixPath(full_report_url).parts
            and "?" not in full_report_url
            and "#" not in full_report_url
            and isinstance(result_notice.get("headline"), str)
            and 1 <= len(result_notice["headline"]) <= 240
            and bool(result_notice["headline"].strip())
            and isinstance(result_notice.get("summary"), str)
            and 1 <= len(result_notice["summary"]) <= 1_200
            and bool(result_notice["summary"].strip())
            and isinstance(result_notice.get("key_findings"), list)
            and 1 <= len(result_notice["key_findings"]) <= 10
            and all(
                isinstance(finding, str)
                and 1 <= len(finding) <= 700
                and bool(finding.strip())
                for finding in result_notice["key_findings"]
            )
        ):
            raise DeployError(
                f"release has an invalid result notice for study {study_id}"
            )
        extension = publication.get("extension_vote")
        if not (
            isinstance(extension, dict)
            and extension.get("requested") is True
            and extension.get("button_label") == "Vote to extend this paper"
            and extension.get("selection_mode") == "single_choice"
            and isinstance(extension.get("options"), list)
            and extension["options"]
        ):
            raise DeployError(f"release has an invalid extension contract for study {study_id}")
        option_ids: set[str] = set()
        for option in extension["options"]:
            option_id = option.get("id") if isinstance(option, dict) else None
            if (
                not isinstance(option_id, str)
                or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", option_id)
                or option_id in option_ids
            ):
                raise DeployError(f"release has an invalid extension option for study {study_id}")
            option_ids.add(option_id)
    return manifest


def switch_current(target: Path) -> None:
    temporary = CURRENT_LINK.parent / f".current-{os.getpid()}"
    try:
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(target)
        os.replace(temporary, CURRENT_LINK)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_release_directory(directory: Path) -> None:
    """Make the validated release root traversable by the unprivileged web server."""
    if directory.is_symlink() or not directory.is_dir():
        raise DeployError("release destination is not a real directory")
    directory.chmod(0o755)
    if directory.stat().st_mode & 0o777 != 0o755:
        raise DeployError("release destination permissions are not 0755")


def verify_live(manifest: dict[str, object]) -> None:
    health_paths = manifest["health_paths"]
    assert isinstance(health_paths, list)
    for path in health_paths:
        assert isinstance(path, str)
        command = [
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "12",
            "--retry",
            "2",
            "--retry-delay",
            "1",
            "--resolve",
            f"{PUBLIC_HOST}:443:127.0.0.1",
            f"https://{PUBLIC_HOST}{path}",
        ]
        result = subprocess.run(command, check=False, capture_output=True)
        if result.returncode != 0:
            detail = result.stderr.decode(errors="replace").strip()
            raise DeployError(f"live health check failed for {path}: {detail}")
        if path == "/release.json":
            try:
                live_manifest = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise DeployError("live release manifest is invalid JSON") from exc
            for key in (
                "site_mode",
                "git_commit",
                "tree_sha256",
                "file_count",
                "health_paths",
                "publications",
            ):
                if live_manifest.get(key) != manifest.get(key):
                    raise DeployError(f"live release manifest mismatch for {key}")


@contextmanager
def deployment_lock() -> Iterator[None]:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def install() -> None:
    if os.geteuid() != 0:
        raise DeployError("installer must run as root")
    if len(sys.argv) != 1:
        raise DeployError("installer does not accept arguments")
    archive = read_archive()
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o755)
    with deployment_lock():
        staging = Path(tempfile.mkdtemp(prefix=".incoming-", dir=RELEASE_ROOT))
        prior_target = CURRENT_LINK.resolve(strict=False) if CURRENT_LINK.exists() else None
        switched = False
        try:
            unpack_archive(archive, staging)
            manifest = validate_release(staging)
            commit = manifest["git_commit"]
            assert isinstance(commit, str)
            destination = RELEASE_ROOT / commit
            if destination.exists():
                existing = validate_release(destination)
                for key in ("git_commit", "tree_sha256", "file_count"):
                    if existing.get(key) != manifest.get(key):
                        raise DeployError(f"existing release disagrees on {key}")
                shutil.rmtree(staging)
            else:
                os.rename(staging, destination)
            prepare_release_directory(destination)
            switch_current(destination)
            switched = True
            try:
                verify_live(manifest)
            except DeployError:
                if prior_target is not None:
                    switch_current(prior_target)
                else:
                    CURRENT_LINK.unlink(missing_ok=True)
                raise
            print(
                "NULSPEC_RELEASE_ACTIVE "
                f"commit={commit} files={manifest['file_count']} "
                f"tree={manifest['tree_sha256']}"
            )
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            if switched and not CURRENT_LINK.exists() and prior_target is not None:
                switch_current(prior_target)


def main() -> int:
    try:
        install()
    except (DeployError, OSError, tarfile.TarError) as exc:
        print(f"NULSPEC_RELEASE_REJECTED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

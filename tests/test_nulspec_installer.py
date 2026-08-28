from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.nulspec_install_release import (
    DeployError,
    prepare_release_directory,
    release_files,
    tree_digest,
    validate_release,
)


def make_release(
    tmp_path: Path,
    *,
    site_mode: str | None,
    publications: list[object],
    health_paths: list[str] | None = None,
) -> Path:
    release = tmp_path / "release"
    release.mkdir()
    selected_health_paths = (
        health_paths if health_paths is not None else ["/", "/release.json"]
    )
    for path in selected_health_paths:
        if path == "/release.json":
            continue
        if path == "/":
            target = release / "index.html"
        else:
            target = release / path.removeprefix("/")
        if path != "/" and path.endswith("/"):
            target = target / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("<h1>NULSPEC</h1>")
    files = release_files(release)
    manifest = {
        "schema_version": 1,
        "git_commit": "a" * 40,
        "tree_sha256": tree_digest(release, files),
        "file_count": len(files),
        "health_paths": selected_health_paths,
        "publications": publications,
    }
    if site_mode is not None:
        manifest["site_mode"] = site_mode
    (release / "release.json").write_text(json.dumps(manifest))
    return release


def test_prepare_release_directory_makes_mkdtemp_root_web_readable(
    tmp_path: Path,
) -> None:
    release = tmp_path / "release"
    release.mkdir(mode=0o700)

    prepare_release_directory(release)

    assert release.stat().st_mode & 0o777 == 0o755


def test_prepare_release_directory_rejects_symlink(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    link = tmp_path / "release-link"
    link.symlink_to(release, target_is_directory=True)

    with pytest.raises(DeployError, match="not a real directory"):
        prepare_release_directory(link)


def test_validate_release_accepts_empty_placeholder(tmp_path: Path) -> None:
    release = make_release(
        tmp_path,
        site_mode="placeholder",
        publications=[],
    )

    manifest = validate_release(release)

    assert manifest["site_mode"] == "placeholder"
    assert manifest["publications"] == []


def test_validate_release_rejects_placeholder_publication(
    tmp_path: Path,
) -> None:
    release = make_release(
        tmp_path,
        site_mode="placeholder",
        publications=[{}],
    )

    with pytest.raises(DeployError, match="must not contain publication"):
        validate_release(release)


def test_validate_release_rejects_extra_placeholder_health_path(
    tmp_path: Path,
) -> None:
    release = make_release(
        tmp_path,
        site_mode="placeholder",
        publications=[],
        health_paths=["/", "/release.json", "/studies/123/"],
    )

    with pytest.raises(DeployError, match="must contain only required endpoints"):
        validate_release(release)


def test_validate_release_accepts_minimal_journal(tmp_path: Path) -> None:
    release = make_release(
        tmp_path,
        site_mode="journal",
        publications=[],
        health_paths=[
            "/",
            "/blog/scheduling-is-all-you-need/",
            "/blog/scheduling-is-all-you-need/manifest.json",
            "/release.json",
        ],
    )

    manifest = validate_release(release)

    assert manifest["site_mode"] == "journal"
    assert "/blog/scheduling-is-all-you-need/" in manifest["health_paths"]


def test_validate_release_preserves_legacy_research_requirement(
    tmp_path: Path,
) -> None:
    release = make_release(
        tmp_path,
        site_mode=None,
        publications=[],
    )

    with pytest.raises(DeployError, match="no publication provenance"):
        validate_release(release)

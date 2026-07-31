from __future__ import annotations

from pathlib import Path

import pytest

from ops.nulspec_install_release import DeployError, prepare_release_directory


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

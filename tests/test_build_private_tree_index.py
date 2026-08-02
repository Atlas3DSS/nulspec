import hashlib
import importlib.util
from pathlib import Path

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "build_private_tree_index.py"
SPEC = importlib.util.spec_from_file_location("build_private_tree_index", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_index_is_path_private_and_content_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "private-host-path" / "attempt-01"
    root.mkdir(parents=True)
    (root / "z.txt").write_bytes(b"z")
    (root / "nested").mkdir()
    (root / "nested" / "a.bin").write_bytes(b"abc")

    index = MODULE.build_index(root, created_at_utc="2026-08-02T00:00:00Z")

    expected_records = (
        "nested/a.bin\t3\t"
        + hashlib.sha256(b"abc").hexdigest()
        + "\n"
        + "z.txt\t1\t"
        + hashlib.sha256(b"z").hexdigest()
        + "\n"
    ).encode()
    assert index["root_basename"] == "attempt-01"
    assert str(tmp_path) not in str(index)
    assert index["content_index"] == {
        "algorithm": "sha256-utf8-relative-path-tab-bytes-tab-file-sha256-newline-v1",
        "file_count": 2,
        "total_bytes": 4,
        "records_sha256": hashlib.sha256(expected_records).hexdigest(),
    }
    assert [record["relative_path"] for record in index["files"]] == [
        "nested/a.bin",
        "z.txt",
    ]


def test_build_index_rejects_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "attempt"
    root.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    (root / "linked.txt").symlink_to(target)

    with pytest.raises(MODULE.IndexError, match="contains a symlink"):
        MODULE.build_index(root)


def test_write_new_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "index.json"
    MODULE.write_new(output, b"first")

    with pytest.raises(MODULE.IndexError, match="refusing to overwrite"):
        MODULE.write_new(output, b"second")


def test_main_rejects_output_inside_root(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "attempt"
    root.mkdir()
    output = root / "index.json"
    monkeypatch.setattr(
        "sys.argv",
        [str(SCRIPT), "--root", str(root), "--output", str(output)],
    )

    with pytest.raises(SystemExit, match="output must be outside"):
        MODULE.main()

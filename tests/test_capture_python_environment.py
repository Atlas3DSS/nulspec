from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "capture_python_environment.py"


def test_environment_capture_is_self_hashing_and_append_only(tmp_path: Path) -> None:
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("version = 1\n", encoding="utf-8")
    output = tmp_path / "python-environment.json"
    first = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output",
            str(output),
            "--lockfile",
            str(lockfile),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    packages_payload = (
        json.dumps(payload["packages"], indent=2, sort_keys=True) + "\n"
    ).encode()
    assert payload["capture_method"] == "importlib.metadata"
    assert payload["package_count"] == len(payload["packages"])
    assert payload["package_count"] > 0
    assert payload["packages_sha256"] == hashlib.sha256(packages_payload).hexdigest()
    assert (
        payload["lockfile"]["sha256"]
        == hashlib.sha256(lockfile.read_bytes()).hexdigest()
    )

    second = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert second.returncode != 0
    assert "refusing to overwrite" in second.stderr

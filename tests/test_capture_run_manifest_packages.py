from __future__ import annotations

import importlib.util
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "capture_run_manifest.py"
SPEC = importlib.util.spec_from_file_location("capture_run_manifest", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


class FakeDistribution:
    def __init__(self, name: str, version: str) -> None:
        self.metadata = {"Name": name}
        self.version = version


def test_package_capture_falls_back_when_pip_is_absent(monkeypatch) -> None:
    monkeypatch.setattr(
        CAPTURE,
        "run",
        lambda command: {
            "command": command,
            "exit_code": 1,
            "stdout": "",
            "stderr": "No module named pip",
        },
    )
    monkeypatch.setattr(
        CAPTURE,
        "distributions",
        lambda: [
            FakeDistribution("Example-Package", "2.0"),
            FakeDistribution("a", "1"),
        ],
    )
    result = CAPTURE.capture_packages()
    assert result["exit_code"] == 0
    assert result["method"] == "importlib-metadata-fallback"
    assert result["pip_freeze_exit_code"] == 1
    assert result["packages"] == ["a==1", "Example-Package==2.0"]


def test_package_capture_prefers_successful_pip_freeze(monkeypatch) -> None:
    monkeypatch.setattr(
        CAPTURE,
        "run",
        lambda command: {
            "command": command,
            "exit_code": 0,
            "stdout": "a==1\nb==2\n",
            "stderr": "",
        },
    )
    result = CAPTURE.capture_packages()
    assert result["exit_code"] == 0
    assert result["method"] == "pip-freeze-all"
    assert result["packages"] == ["a==1", "b==2"]

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts/run_2607_17674_qwen_citation_audit.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("run_qwen_citation_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_executable_record_binds_file_and_version(tmp_path: Path) -> None:
    executable = tmp_path / "version-tool"
    executable.write_text("#!/bin/sh\nprintf 'version 1\\n'\n")
    executable.chmod(0o755)
    record = RUNNER.executable_record(executable)
    assert record["basename"] == "version-tool"
    assert record["bytes"] == executable.stat().st_size
    assert record["sha256"] == RUNNER.sha256_file(executable)
    assert record["version"]["exit_code"] == 0
    assert record["version"]["stdout"] == "version 1\n"

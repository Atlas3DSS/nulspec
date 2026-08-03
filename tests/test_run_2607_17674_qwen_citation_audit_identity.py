from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


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


def test_source_file_record_binds_workspace_relative_code() -> None:
    record = RUNNER.source_file_record(SCRIPT)
    assert record["relative_path"] == ("scripts/run_2607_17674_qwen_citation_audit.py")
    assert record["bytes"] == SCRIPT.stat().st_size
    assert record["sha256"] == RUNNER.sha256_file(SCRIPT)


def test_v107_resume_identity_ignores_only_media_marker() -> None:
    config = json.loads(
        (
            WORKSPACE / "protocols/2607.17674/citation_audit_config.v1.0.7.json"
        ).read_text()
    )
    existing = {
        "routes": [
            {
                "label": "workstation",
                "model_alias": "qwen-test",
                "props": {"media_marker": "first", "n_ctx": 50176},
            }
        ],
        "config_sha256": "same",
    }
    candidate = {
        "routes": [
            {
                "label": "workstation",
                "model_alias": "qwen-test",
                "props": {"media_marker": "second", "n_ctx": 50176},
            }
        ],
        "config_sha256": "same",
    }
    assert RUNNER.run_inputs_match(existing, candidate, config)

    candidate["routes"][0]["props"]["n_ctx"] = 4096
    assert not RUNNER.run_inputs_match(existing, candidate, config)


def test_v108_continuation_retains_the_same_narrow_resume_policy() -> None:
    config = json.loads(
        (
            WORKSPACE / "protocols/2607.17674/citation_audit_config.v1.0.8.json"
        ).read_text()
    )
    existing = {
        "routes": [{"props": {"media_marker": "first", "n_ctx": 50176}}],
        "continuation": {"manifest_sha256": "same"},
    }
    candidate = {
        "routes": [{"props": {"media_marker": "second", "n_ctx": 50176}}],
        "continuation": {"manifest_sha256": "same"},
    }
    assert RUNNER.run_inputs_match(existing, candidate, config)
    candidate["continuation"]["manifest_sha256"] = "changed"
    assert not RUNNER.run_inputs_match(existing, candidate, config)


def test_v106_resume_identity_remains_strict() -> None:
    config = json.loads(
        (
            WORKSPACE / "protocols/2607.17674/citation_audit_config.v1.0.6.json"
        ).read_text()
    )
    existing = {"routes": [{"props": {"media_marker": "first"}}]}
    candidate = {"routes": [{"props": {"media_marker": "second"}}]}
    assert not RUNNER.run_inputs_match(existing, candidate, config)


def test_phase_resume_keeps_one_unmatched_start(tmp_path: Path) -> None:
    event_log = tmp_path / "events.jsonl"
    RUNNER.append_event(event_log, "qwen_phase_started", phase="remaining")
    assert RUNNER.phase_is_open(event_log, "remaining")
    RUNNER.append_event(event_log, "qwen_phase_resumed", phase="remaining")
    assert RUNNER.phase_is_open(event_log, "remaining")
    RUNNER.append_event(event_log, "qwen_phase_completed", phase="remaining")
    assert not RUNNER.phase_is_open(event_log, "remaining")


def test_phase_resume_without_start_fails_closed(tmp_path: Path) -> None:
    event_log = tmp_path / "events.jsonl"
    RUNNER.append_event(event_log, "qwen_phase_resumed", phase="remaining")
    with pytest.raises(RUNNER.AuditError, match="resume lacks an unmatched start"):
        RUNNER.phase_is_open(event_log, "remaining")

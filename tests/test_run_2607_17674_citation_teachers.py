from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "run_2607_17674_citation_teachers.py"
SPEC = importlib.util.spec_from_file_location("run_citation_teachers", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_frozen_bindings_match_runner_dependencies() -> None:
    config = RUNNER.load_object(RUNNER.DEFAULT_CONFIG)
    RUNNER.verify_bindings(config)


def test_event_log_is_one_json_object_per_line(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    RUNNER.append_event(path, "first", value=1)
    RUNNER.append_event(path, "second", value=2)
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["event"] for line in lines] == ["first", "second"]


def test_spend_gate_reserves_settles_and_blocks_unknown_cost_repair() -> None:
    gate = RUNNER.SpendGate(per_teacher=20.0, total=25.0)
    gate.reserve("glm:01", "glm", 2.0)
    settled = gate.settle("glm:01", 0.5)
    assert settled["accounted_cost_usd"] == 0.5
    assert settled["budget_exceeded"] is False

    gate.reserve("kimi:01", "kimi", 10.0)
    unknown = gate.settle("kimi:01", None)
    assert unknown["accounting_basis"] == "conservative_upper_bound_due_to_missing_usage"
    with pytest.raises(RUNNER.TeacherRunError, match="prior unknown cost"):
        gate.reserve("kimi:02", "kimi", 1.0)


def test_spend_gate_rejects_total_conservative_overcommit() -> None:
    gate = RUNNER.SpendGate(per_teacher=20.0, total=25.0)
    gate.reserve("glm:01", "glm", 10.0)
    with pytest.raises(RUNNER.TeacherRunError, match="total conservative"):
        gate.reserve("kimi:01", "kimi", 16.0)


def test_cost_ceiling_includes_schema_instruction() -> None:
    route = RUNNER.PROVIDER_ROUTES["z-ai/glm-5.2"][0]
    schema = {"type": "object", "additionalProperties": False}
    system = "teacher"
    user = "packet"
    effective = system + RUNNER.schema_instruction(schema)
    maximum, _ = RUNNER.available_completion_tokens(route, effective, user)
    upper, input_tokens = RUNNER.conservative_upper_cost(
        route, effective, user, maximum
    )
    assert input_tokens == (len((effective + user).encode()) + 1) // 2
    assert upper > 0


def test_usage_basis_requires_numeric_usage_not_booleans() -> None:
    assert RUNNER.usage_has_cost_basis(
        {"prompt_tokens": 12, "completion_tokens": 4}
    )
    assert RUNNER.usage_has_cost_basis({"estimated_cost": 0.01})
    assert not RUNNER.usage_has_cost_basis({"prompt_tokens": True, "completion_tokens": 4})
    assert not RUNNER.usage_has_cost_basis({})

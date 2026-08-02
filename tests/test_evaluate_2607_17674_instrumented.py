from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "evaluate_2607_17674_instrumented.py"
SPEC = importlib.util.spec_from_file_location(
    "evaluate_2607_17674_instrumented",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_generation_seed_modes_match_registered_behavior() -> None:
    assert (
        MODULE.generation_seed(
            "released-reseed",
            base_seed=314159,
            batch_start=128,
            phase="fidelity",
        )
        == 314159
    )
    assert (
        MODULE.generation_seed(
            "released-reseed",
            base_seed=314159,
            batch_start=128,
            phase="analogical",
        )
        == 314288
    )
    assert (
        MODULE.generation_seed(
            "advancing",
            base_seed=314159,
            batch_start=128,
            phase="fidelity",
        )
        is None
    )


def test_fidelity_metrics_use_strategy_compatible_outcomes() -> None:
    metrics = MODULE.fidelity_metrics(
        [
            "unique_strategy",
            "ambiguous_strategy",
            "off_strategy",
            "parse_failure",
        ]
    )
    assert metrics["distributional_fidelity"] == 0.5
    assert metrics["num_examples"] == 4


def test_analogical_conventions_separate_ambiguity() -> None:
    first = MODULE.analogical_decisions({"a", "b"}, {"b", "c"})
    second = MODULE.analogical_decisions({"a"}, {"a"})
    third = MODULE.analogical_decisions(set(), set())
    assert first == {
        "released_overlap": True,
        "nonempty_set_equality": False,
        "unique_only": False,
    }
    assert second == {
        "released_overlap": True,
        "nonempty_set_equality": True,
        "unique_only": True,
    }
    assert not any(third.values())


def test_analogical_metrics_report_all_registered_conventions() -> None:
    rows = [
        {
            "source_strategies": ["a", "b"],
            "target_strategies": ["b", "c"],
            "decisions": MODULE.analogical_decisions({"a", "b"}, {"b", "c"}),
        },
        {
            "source_strategies": ["a"],
            "target_strategies": ["a"],
            "decisions": MODULE.analogical_decisions({"a"}, {"a"}),
        },
    ]
    metrics = MODULE.analogical_metrics(rows)
    assert metrics["analogical_consistency"] == 1.0
    assert metrics["analogical_consistency_nonempty_set_equality"] == 0.5
    assert metrics["analogical_consistency_unique_only"] == 0.5
    assert metrics["ambiguous_pair_rate"] == 0.5


def test_instrumentation_refuses_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        MODULE.require_new_output_dir(output)

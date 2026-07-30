from __future__ import annotations

import json
from pathlib import Path

from extension.analyze_judgments import summarize
from extension.external_judge import extract_decision, mapped_winner
from extension.matrixctl import arms
from extension.outer_teacher import build_packet


def test_extract_decision_handles_fenced_reasoning() -> None:
    result = extract_decision(
        'analysis first\n```json\n{"winner":"B","reason":"More coherent"}\n```'
    )
    assert result == {"winner": "B", "reason": "More coherent"}


def test_mapping_is_position_invariant() -> None:
    assert mapped_winner("B", "sft_first") == "ppo"
    assert mapped_winner("A", "ppo_first") == "ppo"
    assert mapped_winner("TIE", "ppo_first") == "tie"


def test_summary_excludes_position_inconsistent_pair() -> None:
    records = [
        {
            "pair_id": "good",
            "orientation": "sft_first",
            "winner": "B",
            "mapped_winner": "ppo",
        },
        {
            "pair_id": "good",
            "orientation": "ppo_first",
            "winner": "A",
            "mapped_winner": "ppo",
        },
        {
            "pair_id": "bad",
            "orientation": "sft_first",
            "winner": "A",
            "mapped_winner": "sft",
        },
        {
            "pair_id": "bad",
            "orientation": "ppo_first",
            "winner": "A",
            "mapped_winner": "ppo",
        },
    ]
    result = summarize(records)
    assert result["position_consistent_pairs"] == 1
    assert result["position_inconsistent_pairs"] == 1
    assert result["ppo_win_rate_ties_half"] == 1.0


def test_matrix_has_unique_dependency_ordered_arms() -> None:
    plan = arms()
    assert len(plan) == 18
    ids = [arm["arm_id"] for arm in plan]
    assert len(ids) == len(set(ids))
    for arm in plan:
        if arm["protocol"] == "paper-faithful":
            assert arm["depends_on"] in ids


def test_outer_teacher_packet_excludes_policy_content(tmp_path: Path) -> None:
    path = tmp_path / "judgments.jsonl"
    records = [
        {
            "label": "arm",
            "pair_id": "pair-1",
            "orientation": "sft_first",
            "winner": "A",
            "mapped_winner": "sft",
            "reason": "A is more coherent.",
            "model": "qwen-27b",
            "raw_response": "must not cross boundary",
            "expected_winner": "ppo",
        },
        {
            "label": "arm",
            "pair_id": "pair-1",
            "orientation": "ppo_first",
            "winner": "B",
            "mapped_winner": "sft",
            "reason": "B is more coherent.",
            "model": "qwen-27b",
            "raw_response": "must not cross boundary",
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records))
    packet = build_packet([("arm", path)], 1)
    encoded = json.dumps(packet)
    assert "raw_response" not in encoded
    assert "expected_winner" not in encoded
    assert "must not cross boundary" not in encoded

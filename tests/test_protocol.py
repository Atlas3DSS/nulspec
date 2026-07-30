from __future__ import annotations

import json
from pathlib import Path

from reprolab.protocol import (
    DATA_MANIFEST_PATH,
    PROTOCOL_DIR,
    extract_prompt_reference,
    load_arms,
    load_config,
    validate_matrix,
)
from scripts.audit_reported_statistics import audit, holm_adjust


def test_primary_matrix_is_complete_and_unique() -> None:
    config = load_config()
    assert config["protocol_version"] == "1.0.0"
    arms = load_arms()
    assert len(arms) == 30
    assert validate_matrix(config, arms) == []
    assert len({arm.arm_id for arm in arms}) == 30


def test_every_track_has_all_fifteen_configurations() -> None:
    arms = load_arms()
    assert sum(arm.track == "R" for arm in arms) == 15
    assert sum(arm.track == "M" for arm in arms) == 15


def test_data_manifest_has_three_complete_corpora_and_results() -> None:
    manifest = json.loads(DATA_MANIFEST_PATH.read_text())
    files = set(manifest["files"])
    for dataset in ("tinystories", "cnn_dailymail", "wikitext"):
        for split in (
            "sft_train.json",
            "sft_eval.json",
            "preference_train.json",
            "preference_eval.json",
        ):
            assert f"datasets/{dataset}/{split}" in files
    assert "results/all_results.json" in files


def test_prompt_extraction_matches_release_for_plain_text() -> None:
    prompt, reference = extract_prompt_reference({"text": "x" * 250})
    assert prompt == "x" * 200
    assert reference == "x" * 50


def test_prompt_extraction_handles_instruction_and_prompt_rows() -> None:
    assert extract_prompt_reference(
        {"text": "User: hello\nAssistant: world"}
    ) == ("hello", "world")
    assert extract_prompt_reference(
        {"prompt": "question", "chosen": "answer"}
    ) == ("question", "answer")


def test_citation_and_license_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "CITATION.cff").is_file()
    assert (root / "LICENSE").is_file()


def test_holm_adjustment_preserves_input_order_and_monotonicity() -> None:
    assert holm_adjust([0.04, 0.001, 0.02]) == [0.04, 0.003, 0.04]


def test_released_statistics_are_exactly_reconstructable() -> None:
    root = Path(__file__).resolve().parents[1]
    result = audit(
        root / "paper_repro" / "SLM-RL-Agents" / "results"
        / "all_results.json",
        200,
    )
    assert len(result["rows"]) == 15
    assert all(row["delta_matches"] for row in result["rows"])
    significant = {
        (row["model"], row["dataset"])
        for row in result["rows"]
        if row["significant_uncorrected_0_05"]
    }
    assert significant == {
        ("pythia-410m", "tinystories"),
        ("pythia-410m", "wikitext"),
        ("smollm2-360m", "tinystories"),
        ("smollm2-360m", "wikitext"),
    }
    holm_significant = {
        (row["model"], row["dataset"])
        for row in result["rows"]
        if row["significant_holm_0_05"]
    }
    assert holm_significant == {
        ("pythia-410m", "tinystories"),
        ("pythia-410m", "wikitext"),
        ("smollm2-360m", "tinystories"),
    }


def test_released_checkpoint_manifest_covers_primary_matrix() -> None:
    manifest = json.loads(
        (PROTOCOL_DIR / "released_model_manifest.json").read_text()
    )
    primary = [
        row for row in manifest["checkpoints"] if row["role"] != "orphan"
    ]
    assert len(primary) == 30
    assert sum(row["role"] == "sft_adapter" for row in primary) == 15
    assert sum(row["role"] == "ppo_merged" for row in primary) == 15
    assert all(len(row["lfs_sha256"]) == 64 for row in primary)


def test_protocol_binds_upstream_patch_and_results() -> None:
    config = load_config()
    upstream = config["upstream"]
    assert len(upstream["revision"]) == 40
    assert len(upstream["results_sha256"]) == 64
    assert len(upstream["patch_sha256"]) == 64

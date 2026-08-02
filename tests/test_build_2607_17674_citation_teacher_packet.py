from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "build_2607_17674_citation_teacher_packet.py"
SPEC = importlib.util.spec_from_file_location("citation_teacher_packet", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def synthetic_sources() -> list[dict]:
    sources = []
    for source_index in range(41):
        key = f"source-{source_index:02d}"
        occurrence_count = 2 if source_index < 33 else 1
        chunk_count = 3 if source_index < 30 else 2
        occurrence_ids = [
            f"{key}:occurrence-{index:03d}"
            for index in range(1, occurrence_count + 1)
        ]
        chunk_reviews = []
        for chunk_index in range(1, chunk_count + 1):
            chunk_reviews.append(
                {
                    "chunk_id": f"{key}:chunk-{chunk_index:04d}",
                    "occurrence_findings": [
                        {
                            "occurrence_id": occurrence_id,
                            "evidence_candidates": [],
                        }
                        for occurrence_id in occurrence_ids
                    ],
                }
            )
        sources.append(
            {
                "citation_key": key,
                "citation_review": {
                    "source_identity": {"status": "match"},
                    "occurrence_assessments": [
                        {
                            "occurrence_id": occurrence_id,
                            "support_class": "supports",
                            "citation_appropriateness_score": 8,
                            "confidence": 0.9,
                        }
                        for occurrence_id in occurrence_ids
                    ],
                },
                "evidence_chunk_reviews": chunk_reviews,
                "execution_summary": {
                    "attempts": chunk_count + 1,
                    "invalid_attempts": 0,
                },
            }
        )
    return sources


def test_population_summary_requires_and_counts_complete_qwen_audit() -> None:
    summary = BUILDER.population_summary(synthetic_sources())
    assert summary["source_reviews"] == 41
    assert summary["citation_occurrences"] == 74
    assert summary["evidence_chunks"] == 112
    assert summary["logical_qwen_calls"] == 153
    assert summary["qwen_attempts"] == 153
    assert summary["citation_score_histogram"]["8"] == 74


def test_duplicate_occurrence_is_rejected() -> None:
    sources = synthetic_sources()
    sources[1]["citation_review"]["occurrence_assessments"][0]["occurrence_id"] = (
        sources[0]["citation_review"]["occurrence_assessments"][0]["occurrence_id"]
    )
    with pytest.raises(BUILDER.ProjectionError, match="duplicate occurrence"):
        BUILDER.population_summary(sources)


def test_local_qwen_provenance_uses_a_python_boolean() -> None:
    record = BUILDER.qwen_model_record(
        {"gguf": {"basename": "reviewer.gguf", "sha256": "a" * 64}}
    )

    assert record["official_upstream_release"] is False

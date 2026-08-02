from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "prepare_2607_17674_citation_review.py"
SPEC = importlib.util.spec_from_file_location("citation_packets", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PACKETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKETS)


def test_chunk_partition_is_exact_bounded_and_line_aware() -> None:
    text = "first line\n" + "é" * 20 + "\nlast line\fpage two\n"
    chunks = PACKETS.split_contiguous_text(text, 24)
    assert "".join(value for _, _, value in chunks) == text
    assert chunks[0][0] == 0
    assert chunks[-1][1] == len(text)
    assert all(end == next_start for (_, end, _), (next_start, _, _) in zip(chunks, chunks[1:]))
    assert all(len(value.encode("utf-8")) <= 24 for _, _, value in chunks)


def test_newline_immediately_beyond_byte_ceiling_is_not_included() -> None:
    text = "a" * 24 + "\nnext"
    chunks = PACKETS.split_contiguous_text(text, 24)
    assert chunks[0] == (0, 24, "a" * 24)
    assert "".join(value for _, _, value in chunks) == text


def test_page_spans_track_form_feed_across_chunk_boundaries() -> None:
    text = "page one\fpage two line\nrest\fpage three"
    start = text.index("two")
    end = text.index("three") + len("three")
    assert PACKETS.page_spans(text, start, end) == [
        {
            "page_number": 2,
            "chunk_character_start": 0,
            "chunk_character_end": len("two line\nrest"),
        },
        {
            "page_number": 3,
            "chunk_character_start": len("two line\nrest") + 1,
            "chunk_character_end": end - start,
        },
    ]


def test_empty_text_and_impossible_ceiling_fail_closed() -> None:
    with pytest.raises(PACKETS.PacketError):
        PACKETS.split_contiguous_text("", 10)
    with pytest.raises(PACKETS.PacketError):
        PACKETS.split_contiguous_text("é", 1)


def test_occurrence_ids_are_stable_and_one_indexed() -> None:
    record = {
        "key": "example2026",
        "occurrences": [
            {"file": "one.tex", "line": 4, "context": "claim one"},
            {"file": "two.tex", "line": 7, "context": "claim two"},
        ],
    }
    assert [
        item["occurrence_id"] for item in PACKETS.occurrence_records(record)
    ] == ["example2026:occurrence-001", "example2026:occurrence-002"]

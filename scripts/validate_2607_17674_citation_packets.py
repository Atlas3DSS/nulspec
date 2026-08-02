#!/usr/bin/env python3
"""Validate exact coverage and bindings of citation-review packet trees."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]


class PacketValidationError(RuntimeError):
    """Raised when packet evidence is missing, reordered, or changed."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PacketValidationError(f"expected JSON object: {path}")
    return value


def validate_packet_tree(review_plan_path: Path, packet_root: Path) -> dict[str, Any]:
    review_plan = load_object(review_plan_path)
    if review_plan.get("paper_id") != "2607.17674":
        raise PacketValidationError("review plan paper identity differs")
    if review_plan.get("protocol_version") != "1.0.1":
        raise PacketValidationError("review plan protocol version differs")
    summary = review_plan.get("summary")
    if not isinstance(summary, dict):
        raise PacketValidationError("review plan lacks a summary")
    expected_summary = {
        "source_count": 41,
        "occurrence_count": 74,
        "chunk_count": int(summary.get("chunk_count", -1)),
        "source_text_bytes": int(summary.get("source_text_bytes", -1)),
    }
    if expected_summary["chunk_count"] < 41 or expected_summary["source_text_bytes"] < 1:
        raise PacketValidationError("review plan summary is implausible")
    for label, binding in review_plan["bindings"].items():
        if label == "acquisition_manifest":
            continue
        relative_path = binding.get("relative_path")
        if not isinstance(relative_path, str):
            raise PacketValidationError(f"binding has no path: {label}")
        bound_path = WORKSPACE / relative_path
        if sha256_file(bound_path) != binding["sha256"]:
            raise PacketValidationError(f"protocol binding differs: {label}")

    sources = review_plan.get("sources")
    if not isinstance(sources, list) or len(sources) != 41:
        raise PacketValidationError("review plan must contain 41 sources")
    keys: set[str] = set()
    occurrence_count = 0
    chunk_count = 0
    text_bytes = 0
    source_validations: list[dict[str, Any]] = []
    for source in sources:
        key = str(source["citation_key"])
        if key in keys:
            raise PacketValidationError(f"duplicate citation key: {key}")
        keys.add(key)
        plan_path = packet_root / str(source["source_plan_relative_path"])
        if sha256_file(plan_path) != source["source_plan_sha256"]:
            raise PacketValidationError(f"source plan hash differs: {key}")
        source_plan = load_object(plan_path)
        if source_plan.get("citation_key") != key:
            raise PacketValidationError(f"source plan identity differs: {key}")
        occurrences = source_plan.get("target_occurrences")
        chunks = source_plan.get("chunks")
        if not isinstance(occurrences, list) or not isinstance(chunks, list) or not chunks:
            raise PacketValidationError(f"source plan is incomplete: {key}")
        expected_occurrence_ids = [str(item["occurrence_id"]) for item in occurrences]
        if len(expected_occurrence_ids) != len(set(expected_occurrence_ids)):
            raise PacketValidationError(f"duplicate occurrence identity: {key}")
        reconstructed: list[str] = []
        expected_start = 0
        for chunk in chunks:
            packet_path = packet_root / str(chunk["relative_path"])
            if sha256_file(packet_path) != chunk["packet_sha256"]:
                raise PacketValidationError(f"chunk packet hash differs: {chunk['chunk_id']}")
            packet = load_object(packet_path)
            source_chunk = packet.get("source_chunk")
            if not isinstance(source_chunk, dict):
                raise PacketValidationError(f"chunk packet lacks source text: {chunk['chunk_id']}")
            if source_chunk.get("chunk_id") != chunk["chunk_id"]:
                raise PacketValidationError(f"chunk identity differs: {chunk['chunk_id']}")
            actual_occurrence_ids = [
                str(item["occurrence_id"]) for item in packet["target_occurrences"]
            ]
            if actual_occurrence_ids != expected_occurrence_ids:
                raise PacketValidationError(
                    f"chunk occurrence coverage differs: {chunk['chunk_id']}"
                )
            start = int(source_chunk["character_start"])
            end = int(source_chunk["character_end"])
            value = str(source_chunk["text"])
            if start != expected_start or end != start + len(value):
                raise PacketValidationError(f"chunk gap, overlap, or range error: {chunk['chunk_id']}")
            payload = value.encode("utf-8")
            if len(payload) != int(source_chunk["utf8_bytes"]):
                raise PacketValidationError(f"chunk byte count differs: {chunk['chunk_id']}")
            if sha256_bytes(payload) != source_chunk["sha256"]:
                raise PacketValidationError(f"chunk text hash differs: {chunk['chunk_id']}")
            if len(payload) > 48000:
                raise PacketValidationError(f"chunk exceeds protocol ceiling: {chunk['chunk_id']}")
            reconstructed.append(value)
            expected_start = end
        source_text = "".join(reconstructed)
        bindings = source_plan["source_bindings"]
        if len(source_text) != int(bindings["text_characters"]):
            raise PacketValidationError(f"source character coverage differs: {key}")
        if len(source_text.encode("utf-8")) != int(bindings["text_bytes"]):
            raise PacketValidationError(f"source byte coverage differs: {key}")
        if sha256_bytes(source_text.encode("utf-8")) != bindings["text_sha256"]:
            raise PacketValidationError(f"reconstructed source hash differs: {key}")
        coverage = source_plan["coverage"]
        if coverage != {
            "character_start": 0,
            "character_end": len(source_text),
            "characters_covered": len(source_text),
            "utf8_bytes_covered": len(source_text.encode("utf-8")),
            "overlap_characters": 0,
            "gap_characters": 0,
        }:
            raise PacketValidationError(f"declared source coverage differs: {key}")
        occurrence_count += len(occurrences)
        chunk_count += len(chunks)
        text_bytes += len(source_text.encode("utf-8"))
        source_validations.append(
            {
                "citation_key": key,
                "occurrence_count": len(occurrences),
                "chunk_count": len(chunks),
                "source_text_sha256": bindings["text_sha256"],
            }
        )
    actual_summary = {
        "source_count": len(sources),
        "occurrence_count": occurrence_count,
        "chunk_count": chunk_count,
        "source_text_bytes": text_bytes,
    }
    if actual_summary != expected_summary:
        raise PacketValidationError(
            f"review plan summary differs: expected={expected_summary} actual={actual_summary}"
        )
    calibration = review_plan.get("calibration_keys")
    if not isinstance(calibration, list) or len(calibration) != 6:
        raise PacketValidationError("calibration key set differs")
    if not set(str(key) for key in calibration).issubset(keys):
        raise PacketValidationError("calibration key is absent from source plans")
    return {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "protocol_version": "1.0.1",
        "valid": True,
        "review_plan_sha256": sha256_file(review_plan_path),
        "summary": actual_summary,
        "sources": source_validations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    review_plan_path = args.review_plan.expanduser().resolve()
    packet_root = args.packet_root.expanduser().resolve()
    result = validate_packet_tree(review_plan_path, packet_root)
    if args.output is not None:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()

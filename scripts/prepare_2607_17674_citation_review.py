#!/usr/bin/env python3
"""Build immutable, source-complete Qwen citation-review packets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = WORKSPACE / "protocols" / "2607.17674"
STUDY_WORK_ROOT = WORKSPACE / "research" / "replications" / "2607.17674" / "work"
DEFAULT_INVENTORY = PROTOCOL_ROOT / "citation_inventory.json"
DEFAULT_CONFIG = PROTOCOL_ROOT / "citation_audit_config.v1.0.1.json"
DEFAULT_EVIDENCE_SCHEMA = PROTOCOL_ROOT / "citation_evidence_chunk.schema.json"
DEFAULT_REVIEW_SCHEMA = PROTOCOL_ROOT / "citation_review.schema.json"
DEFAULT_EVIDENCE_PROMPT = PROTOCOL_ROOT / "prompts" / "citation_evidence_system.txt"
DEFAULT_SYNTHESIS_PROMPT = PROTOCOL_ROOT / "prompts" / "citation_synthesis_system.txt"
EXPECTED_INVENTORY_SHA256 = (
    "471117efcde4eb55e8a6742dc00ffc0c291f30c821e071f56834c433cdabe43a"
)


class PacketError(RuntimeError):
    """Raised when a source or packet violates the frozen audit contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def encoded_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encoded_json(value))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PacketError(f"expected JSON object: {path}")
    return value


def maximum_prefix_end(text: str, start: int, maximum_bytes: int) -> int:
    """Return the largest Unicode boundary fitting the byte ceiling."""

    low = start + 1
    high = len(text)
    best = start
    while low <= high:
        midpoint = (low + high) // 2
        size = len(text[start:midpoint].encode("utf-8"))
        if size <= maximum_bytes:
            best = midpoint
            low = midpoint + 1
        else:
            high = midpoint - 1
    if best == start:
        raise PacketError("maximum chunk size cannot hold the next Unicode character")
    return best


def split_contiguous_text(text: str, maximum_bytes: int) -> list[tuple[int, int, str]]:
    """Partition text exactly once, preferring line boundaries."""

    if maximum_bytes < 1:
        raise PacketError("maximum chunk bytes must be positive")
    if not text:
        raise PacketError("source text is empty")
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = maximum_prefix_end(text, start, maximum_bytes)
        if end < len(text):
            line_end = text.rfind("\n", start + 1, end)
            if line_end >= start:
                candidate = line_end + 1
                if len(text[start:candidate].encode("utf-8")) >= maximum_bytes // 2:
                    end = candidate
        value = text[start:end]
        if not value or len(value.encode("utf-8")) > maximum_bytes:
            raise PacketError("internal chunk partition error")
        chunks.append((start, end, value))
        start = end
    if "".join(chunk for _, _, chunk in chunks) != text:
        raise PacketError("chunk partition does not reconstruct the source")
    return chunks


def page_spans(source_text: str, start: int, end: int) -> list[dict[str, int]]:
    """Map an exact character interval to extracted-PDF page spans."""

    value = source_text[start:end]
    page = 1 + source_text[:start].count("\f")
    local_start = 0
    spans: list[dict[str, int]] = []
    while True:
        delimiter = value.find("\f", local_start)
        local_end = len(value) if delimiter < 0 else delimiter
        if local_end > local_start:
            spans.append(
                {
                    "page_number": page,
                    "chunk_character_start": local_start,
                    "chunk_character_end": local_end,
                }
            )
        if delimiter < 0:
            break
        page += 1
        local_start = delimiter + 1
    return spans


def safe_acquired_path(source_root: Path, relative_name: str) -> Path:
    candidate_name = Path(relative_name)
    if candidate_name.name != relative_name or relative_name in {"", ".", ".."}:
        raise PacketError(f"unsafe acquired source path: {relative_name!r}")
    candidate = (source_root / relative_name).resolve()
    try:
        candidate.relative_to(source_root.resolve())
    except ValueError as error:
        raise PacketError(f"acquired source escaped its root: {relative_name}") from error
    if not candidate.is_file():
        raise PacketError(f"acquired source is missing: {candidate}")
    return candidate


def occurrence_records(record: dict[str, Any]) -> list[dict[str, Any]]:
    key = str(record["key"])
    occurrences = record.get("occurrences")
    if not isinstance(occurrences, list) or not occurrences:
        raise PacketError(f"cited record has no occurrences: {key}")
    return [
        {
            "occurrence_id": f"{key}:occurrence-{index:03d}",
            "source_file": str(occurrence["file"]),
            "source_line": int(occurrence["line"]),
            "manuscript_context": str(occurrence["context"]),
        }
        for index, occurrence in enumerate(occurrences, start=1)
    ]


def prepare_source(
    record: dict[str, Any],
    acquisition: dict[str, Any],
    source_root: Path,
    output_root: Path,
    maximum_bytes: int,
    evidence_schema_sha256: str,
    evidence_prompt_sha256: str,
) -> dict[str, Any]:
    key = str(record["key"])
    if acquisition.get("key") != key or acquisition.get("state") != "ready":
        raise PacketError(f"source acquisition is not ready for {key}")
    text_record = acquisition.get("text")
    pdf_record = acquisition.get("pdf")
    if not isinstance(text_record, dict) or not isinstance(pdf_record, dict):
        raise PacketError(f"source acquisition metadata is incomplete for {key}")
    text_path = safe_acquired_path(source_root, str(text_record["relative_path"]))
    pdf_path = safe_acquired_path(source_root, str(pdf_record["relative_path"]))
    if text_path.stat().st_size != int(text_record["bytes"]):
        raise PacketError(f"text byte count differs from acquisition manifest: {key}")
    if pdf_path.stat().st_size != int(pdf_record["bytes"]):
        raise PacketError(f"PDF byte count differs from acquisition manifest: {key}")
    if sha256_file(text_path) != text_record["sha256"]:
        raise PacketError(f"text hash differs from acquisition manifest: {key}")
    if sha256_file(pdf_path) != pdf_record["sha256"]:
        raise PacketError(f"PDF hash differs from acquisition manifest: {key}")

    source_text = text_path.read_text(encoding="utf-8")
    occurrences = occurrence_records(record)
    source_identity = {
        "citation_key": key,
        "title": str(record["title"]),
        "authors": str(record["author"]),
        "year": str(record["year"]),
        "doi": record.get("doi"),
        "eprint": record.get("eprint"),
        "bibliographic_source_url": acquisition.get("bibliographic_source_url"),
        "selected_source_url": acquisition.get("selected_url"),
    }
    chunk_records: list[dict[str, Any]] = []
    for index, (start, end, chunk_text) in enumerate(
        split_contiguous_text(source_text, maximum_bytes), start=1
    ):
        chunk_id = f"{key}:chunk-{index:04d}"
        spans = page_spans(source_text, start, end)
        packet = {
            "schema_version": 1,
            "packet_type": "citation_evidence_chunk",
            "paper_id": "2607.17674",
            "paper_version": "v1",
            "protocol_version": "1.0.1",
            "source_identity": source_identity,
            "source_bindings": {
                "pdf_sha256": str(pdf_record["sha256"]),
                "extracted_text_sha256": str(text_record["sha256"]),
                "selected_source_url": acquisition.get("selected_url"),
            },
            "target_occurrences": occurrences,
            "source_chunk": {
                "chunk_id": chunk_id,
                "chunk_number": index,
                "character_start": start,
                "character_end": end,
                "character_count": len(chunk_text),
                "utf8_bytes": len(chunk_text.encode("utf-8")),
                "sha256": sha256_bytes(chunk_text.encode("utf-8")),
                "page_spans": spans,
                "text": chunk_text,
            },
            "output_contract": {
                "schema_relative_path": (
                    "protocols/2607.17674/citation_evidence_chunk.schema.json"
                ),
                "schema_sha256": evidence_schema_sha256,
                "system_prompt_relative_path": (
                    "protocols/2607.17674/prompts/citation_evidence_system.txt"
                ),
                "system_prompt_sha256": evidence_prompt_sha256,
                "required_occurrence_ids": [
                    occurrence["occurrence_id"] for occurrence in occurrences
                ],
            },
        }
        relative_path = Path("packets") / key / "evidence" / f"chunk-{index:04d}.json"
        packet_path = output_root / relative_path
        write_new_json(packet_path, packet)
        chunk_records.append(
            {
                "chunk_id": chunk_id,
                "relative_path": relative_path.as_posix(),
                "packet_sha256": sha256_file(packet_path),
                "character_start": start,
                "character_end": end,
                "utf8_bytes": len(chunk_text.encode("utf-8")),
                "text_sha256": packet["source_chunk"]["sha256"],
                "page_numbers": [span["page_number"] for span in spans],
            }
        )

    source_plan = {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "protocol_version": "1.0.1",
        "citation_key": key,
        "source_identity": source_identity,
        "source_bindings": {
            "pdf_relative_path": str(pdf_record["relative_path"]),
            "pdf_bytes": int(pdf_record["bytes"]),
            "pdf_sha256": str(pdf_record["sha256"]),
            "text_relative_path": str(text_record["relative_path"]),
            "text_bytes": int(text_record["bytes"]),
            "text_characters": len(source_text),
            "text_sha256": str(text_record["sha256"]),
        },
        "target_occurrences": occurrences,
        "chunks": chunk_records,
        "coverage": {
            "character_start": 0,
            "character_end": len(source_text),
            "characters_covered": sum(
                chunk["character_end"] - chunk["character_start"]
                for chunk in chunk_records
            ),
            "utf8_bytes_covered": sum(chunk["utf8_bytes"] for chunk in chunk_records),
            "overlap_characters": 0,
            "gap_characters": 0,
        },
    }
    plan_relative_path = Path("packets") / key / "source-plan.json"
    plan_path = output_root / plan_relative_path
    write_new_json(plan_path, source_plan)
    return {
        "citation_key": key,
        "source_plan_relative_path": plan_relative_path.as_posix(),
        "source_plan_sha256": sha256_file(plan_path),
        "occurrence_count": len(occurrences),
        "chunk_count": len(chunk_records),
        "source_text_bytes": int(text_record["bytes"]),
        "source_text_sha256": str(text_record["sha256"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    inventory_path = args.inventory.expanduser().resolve()
    acquisition_manifest_path = args.acquisition_manifest.expanduser().resolve()
    source_root = args.source_root.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    config_path = args.config.expanduser().resolve()
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite packet root: {output_root}")
    if output_root == Path(output_root.anchor):
        raise SystemExit("refusing broad packet root")
    try:
        output_root.relative_to(STUDY_WORK_ROOT.resolve())
    except ValueError as error:
        raise SystemExit(f"packet root must be inside {STUDY_WORK_ROOT}") from error

    inventory_hash = sha256_file(inventory_path)
    if inventory_hash != EXPECTED_INVENTORY_SHA256:
        raise SystemExit("citation inventory hash does not match protocol")
    inventory = load_object(inventory_path)
    config = load_object(config_path)
    acquisition_manifest = load_object(acquisition_manifest_path)
    if config.get("protocol_version") != "1.0.1":
        raise SystemExit("citation-audit config is not protocol v1.0.1")
    if acquisition_manifest.get("paper_id") != "2607.17674":
        raise SystemExit("acquisition manifest paper identity differs")
    if acquisition_manifest.get("inventory", {}).get("sha256") != inventory_hash:
        raise SystemExit("acquisition manifest inventory hash differs")

    cited_records = [record for record in inventory["records"] if record["cited"]]
    source_records = acquisition_manifest.get("sources")
    if len(cited_records) != 41 or not isinstance(source_records, list):
        raise SystemExit("citation or source cardinality differs from protocol")
    source_by_key = {str(record.get("key")): record for record in source_records}
    if set(source_by_key) != {str(record["key"]) for record in cited_records}:
        raise SystemExit("acquired source keys differ from citation inventory")

    output_root.mkdir(parents=True)
    bindings = {
        "config": {
            "relative_path": "protocols/2607.17674/citation_audit_config.v1.0.1.json",
            "sha256": sha256_file(config_path),
        },
        "inventory": {
            "relative_path": "protocols/2607.17674/citation_inventory.json",
            "sha256": inventory_hash,
        },
        "acquisition_manifest": {
            "sha256": sha256_file(acquisition_manifest_path),
        },
        "evidence_schema": {
            "relative_path": "protocols/2607.17674/citation_evidence_chunk.schema.json",
            "sha256": sha256_file(DEFAULT_EVIDENCE_SCHEMA),
        },
        "review_schema": {
            "relative_path": "protocols/2607.17674/citation_review.schema.json",
            "sha256": sha256_file(DEFAULT_REVIEW_SCHEMA),
        },
        "evidence_prompt": {
            "relative_path": "protocols/2607.17674/prompts/citation_evidence_system.txt",
            "sha256": sha256_file(DEFAULT_EVIDENCE_PROMPT),
        },
        "synthesis_prompt": {
            "relative_path": "protocols/2607.17674/prompts/citation_synthesis_system.txt",
            "sha256": sha256_file(DEFAULT_SYNTHESIS_PROMPT),
        },
    }
    maximum_bytes = int(config["chunking"]["maximum_utf8_bytes"])
    source_plans = [
        prepare_source(
            record,
            source_by_key[str(record["key"])],
            source_root,
            output_root,
            maximum_bytes,
            bindings["evidence_schema"]["sha256"],
            bindings["evidence_prompt"]["sha256"],
        )
        for record in cited_records
    ]
    manifest = {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "paper_version": "v1",
        "protocol_version": "1.0.1",
        "created_at_utc": utc_now(),
        "bindings": bindings,
        "summary": {
            "source_count": len(source_plans),
            "occurrence_count": sum(
                source["occurrence_count"] for source in source_plans
            ),
            "chunk_count": sum(source["chunk_count"] for source in source_plans),
            "source_text_bytes": sum(
                source["source_text_bytes"] for source in source_plans
            ),
        },
        "calibration_keys": config["calibration_keys"],
        "sources": source_plans,
    }
    manifest_path = output_root / "review-plan.json"
    write_new_json(manifest_path, manifest)
    print(json.dumps({**manifest["summary"], "manifest_sha256": sha256_file(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path


ALLOWED_RECORD_FIELDS = {
    "label",
    "pair_id",
    "orientation",
    "winner",
    "mapped_winner",
    "reason",
    "model",
}


def parse_label_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, path = value.split("=", 1)
    return label, Path(path)


def load_qwen_records(label: str, path: Path) -> list[dict]:
    records = [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    for record in records:
        model = str(record.get("model", "")).lower()
        if "qwen" not in model:
            raise ValueError(
                f"{path} contains a non-Qwen reviewer record: {model!r}"
            )
        if record.get("label") != label:
            raise ValueError(
                f"{path} label mismatch: {record.get('label')!r} != {label!r}"
            )
    return records


def audit_priority(records: list[dict]) -> tuple[int, str]:
    orientations = {record["orientation"] for record in records}
    mapped = {record["mapped_winner"] for record in records}
    if orientations != {"sft_first", "ppo_first"}:
        return 0, "incomplete_orientation_pair"
    if len(mapped) != 1:
        return 1, "position_inconsistent"
    reasons = [str(record.get("reason", "")).strip() for record in records]
    if any(len(reason.split()) < 3 for reason in reasons):
        return 2, "weak_reason"
    return 3, "routine_consistent"


def stable_tiebreak(label: str, pair_id: str) -> str:
    value = f"{label}:{pair_id}:outer-teacher-v1".encode()
    return hashlib.sha256(value).hexdigest()


def build_packet(
    judgment_sources: list[tuple[str, Path]], sample_size: int
) -> dict:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    source_counts: dict[str, int] = {}
    population_summary: dict[str, dict] = {}
    for label, path in judgment_sources:
        records = load_qwen_records(label, path)
        source_counts[label] = len(records)
        for record in records:
            grouped[(label, record["pair_id"])].append(record)
        label_groups: dict[str, list[dict]] = defaultdict(list)
        for record in records:
            label_groups[record["pair_id"]].append(record)
        inconsistent = 0
        incomplete = 0
        for pair_records in label_groups.values():
            orientations = {
                record["orientation"] for record in pair_records
            }
            mapped = {
                record["mapped_winner"] for record in pair_records
            }
            incomplete += orientations != {"sft_first", "ppo_first"}
            inconsistent += (
                orientations == {"sft_first", "ppo_first"}
                and len(mapped) != 1
            )
        raw = [record["winner"] for record in records]
        population_summary[label] = {
            "pairs": len(label_groups),
            "records": len(records),
            "incomplete_pairs": incomplete,
            "position_inconsistent_pairs": inconsistent,
            "raw_a_choices": raw.count("A"),
            "raw_b_choices": raw.count("B"),
            "raw_ties": raw.count("TIE"),
        }

    candidates = []
    for (label, pair_id), records in grouped.items():
        priority, selection_reason = audit_priority(records)
        candidates.append(
            (
                priority,
                stable_tiebreak(label, pair_id),
                label,
                pair_id,
                selection_reason,
                records,
            )
        )
    candidates.sort(key=lambda value: (value[0], value[1]))
    per_label: dict[str, list[tuple]] = defaultdict(list)
    for candidate in candidates:
        per_label[candidate[2]].append(candidate)
    selected = []
    selected_keys: set[tuple[str, str]] = set()
    labels = sorted(per_label)
    stratified_target = min(sample_size, max(len(labels), sample_size // 2))
    offset = 0
    while len(selected) < stratified_target:
        made_progress = False
        for label in labels:
            if offset < len(per_label[label]):
                candidate = per_label[label][offset]
                selected.append(candidate)
                selected_keys.add((candidate[2], candidate[3]))
                made_progress = True
                if len(selected) == stratified_target:
                    break
        if not made_progress:
            break
        offset += 1
    for candidate in candidates:
        if len(selected) == sample_size:
            break
        key = (candidate[2], candidate[3])
        if key not in selected_keys:
            selected.append(candidate)
            selected_keys.add(key)

    pairs = []
    for _, _, label, pair_id, selection_reason, records in selected:
        sanitized = [
            {
                key: record[key]
                for key in ALLOWED_RECORD_FIELDS
                if key in record
            }
            for record in sorted(
                records, key=lambda value: value["orientation"]
            )
        ]
        pairs.append(
            {
                "label": label,
                "pair_id": pair_id,
                "selection_reason": selection_reason,
                "qwen_reviews": sanitized,
            }
        )

    return {
        "protocol": {
            "name": "qwen-reviewer-outer-audit-v1",
            "boundary": (
                "Contains only Qwen reviewer records. No story prompt, "
                "small-policy output, checkpoint, reward, or training state."
            ),
            "selection": (
                "Position-inconsistent and incomplete records first, then "
                "weak reasons, then a stable pseudorandom consistent sample."
            ),
            "sample_size_requested": sample_size,
            "sample_size_realized": len(pairs),
            "source_record_counts": source_counts,
            "population_summary": population_summary,
        },
        "pairs": pairs,
    }


def teacher_prompt(packet: dict) -> str:
    return """You are the final outer teacher in a three-layer evaluation.

HARD SCOPE BOUNDARY:
- You are reviewing Qwen-27B's reviewer records only.
- You must not infer or invent the underlying stories or small-model outputs.
- You cannot overturn the underlying SFT/PPO preference because those outputs
  are intentionally absent.
- Audit Qwen for A/B-order consistency, contradictions between winner and
  rationale, unsupported certainty, malformed or vacuous reasons, and systemic
  position bias visible in these records.
- Opposite raw A/B winners can be correct when mapped_winner agrees.
- Findings are audit flags only. They never become training reward and never
  alter the primary effect estimate automatically.

Return JSON matching the supplied schema. Set scope_confirmation exactly to
"qwen_records_only". Reliability is confidence in Qwen's review process from
these records, not confidence that its unseen content preference was correct.
Use concise findings and do not manufacture findings just to fill the list.
For every finding, copy `label` exactly from that packet pair; put the issue
category in `issue`, never in `label`.

QWEN REVIEW PACKET:
""" + json.dumps(packet, indent=2)


def run_codex(
    packet: dict,
    output: Path,
    schema: Path,
) -> None:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("CODEX_API_KEY", None)
    with tempfile.TemporaryDirectory(
        prefix="qwen-outer-teacher-"
    ) as isolated_directory:
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--ignore-rules",
            "--output-schema",
            str(schema.resolve()),
            "--output-last-message",
            str(output.resolve()),
            "--cd",
            isolated_directory,
            "-",
        ]
        result = subprocess.run(
            command,
            input=teacher_prompt(packet),
            text=True,
            check=False,
            env=environment,
        )
    if result.returncode:
        raise SystemExit(f"Codex outer teacher failed: {result.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Qwen reviewer records with Codex subscription auth."
    )
    parser.add_argument(
        "--judgments",
        action="append",
        type=parse_label_path,
        required=True,
    )
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument(
        "--packet",
        type=Path,
        default=Path("extension/artifacts/outer_teacher_packet.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("extension/artifacts/outer_teacher_audit.json"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("extension/outer_teacher_schema.json"),
    )
    parser.add_argument(
        "--packet-only",
        action="store_true",
        help="Build the sanitized packet without invoking Codex.",
    )
    args = parser.parse_args()
    if args.sample_size < 1:
        parser.error("--sample-size must be positive")

    packet = build_packet(args.judgments, args.sample_size)
    args.packet.parent.mkdir(parents=True, exist_ok=True)
    args.packet.write_text(json.dumps(packet, indent=2) + "\n")
    print(f"Wrote Qwen-only audit packet to {args.packet}")
    if args.packet_only:
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    run_codex(packet, args.output, args.schema)
    audit = json.loads(args.output.read_text())
    if audit.get("scope_confirmation") != "qwen_records_only":
        raise RuntimeError("outer teacher failed its scope confirmation")
    pair_labels = {
        pair["pair_id"]: pair["label"] for pair in packet["pairs"]
    }
    for finding in audit["findings"]:
        expected_label = pair_labels.get(finding["pair_id"])
        if expected_label is None or finding["label"] != expected_label:
            raise RuntimeError(
                "outer teacher returned a finding with an invalid pair label"
            )
    print(f"Wrote Codex outer-teacher audit to {args.output}")


if __name__ == "__main__":
    main()

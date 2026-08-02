from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


ENTRY_START = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
CITATION = re.compile(r"\\cite[a-zA-Z]*\{([^}]+)\}")


def balanced_entries(text: str) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    cursor = 0
    while match := ENTRY_START.search(text, cursor):
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        if depth:
            raise ValueError(f"unterminated BibTeX entry: {match.group(2)}")
        entries.append((match.group(1), match.group(2).strip(), text[match.end() : index - 1]))
        cursor = index
    return entries


def split_fields(body: str) -> list[str]:
    fields: list[str] = []
    start = 0
    brace_depth = 0
    in_quote = False
    escaped = False
    for index, char in enumerate(body):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and brace_depth == 0:
            in_quote = not in_quote
        elif not in_quote:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            elif char == "," and brace_depth == 0:
                fields.append(body[start:index])
                start = index + 1
    fields.append(body[start:])
    return fields


def unwrap(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if len(value) >= 2 and (
        (value[0] == "{" and value[-1] == "}")
        or (value[0] == '"' and value[-1] == '"')
    ):
        value = value[1:-1]
    return " ".join(value.split())


def parse_bibliography(path: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for entry_type, key, body in balanced_entries(path.read_text()):
        fields: dict[str, str] = {"entry_type": entry_type.lower()}
        for field in split_fields(body):
            if "=" not in field:
                continue
            name, value = field.split("=", maxsplit=1)
            fields[name.strip().lower()] = unwrap(value)
        entries[key] = fields
    return entries


def citation_occurrences(source_root: Path) -> dict[str, list[dict[str, object]]]:
    occurrences: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in sorted(source_root.rglob("*.tex")):
        relative = path.relative_to(source_root).as_posix()
        lines = path.read_text(errors="replace").splitlines()
        for line_number, line in enumerate(lines, start=1):
            for match in CITATION.finditer(line):
                for key in (item.strip() for item in match.group(1).split(",")):
                    if key:
                        occurrences[key].append(
                            {
                                "file": relative,
                                "line": line_number,
                                "context": " ".join(line.strip().split()),
                            }
                        )
    return occurrences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source_root = args.source_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite inventory: {output}")

    bibliography = parse_bibliography(source_root / "references.bib")
    occurrences = citation_occurrences(source_root)
    missing_entries = sorted(set(occurrences) - set(bibliography))
    if missing_entries:
        raise SystemExit(f"cited keys missing from bibliography: {missing_entries}")

    records = []
    for key, fields in sorted(bibliography.items()):
        source_url = fields.get("url")
        if not source_url and fields.get("doi"):
            source_url = f"https://doi.org/{fields['doi']}"
        records.append(
            {
                "key": key,
                "cited": key in occurrences,
                "citation_count": len(occurrences.get(key, [])),
                "entry_type": fields.get("entry_type"),
                "title": fields.get("title"),
                "author": fields.get("author"),
                "year": fields.get("year"),
                "url": fields.get("url"),
                "doi": fields.get("doi"),
                "eprint": fields.get("eprint"),
                "source_url": source_url,
                "source_acquisition": "pending" if key in occurrences else "not-required",
                "review_state": "pending" if key in occurrences else "not-cited",
                "occurrences": occurrences.get(key, []),
            }
        )

    payload = {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "bibliography_entries": len(bibliography),
        "cited_entries": len(occurrences),
        "citation_occurrences": sum(len(items) for items in occurrences.values()),
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({key: payload[key] for key in payload if key != "records"}, indent=2))


if __name__ == "__main__":
    main()

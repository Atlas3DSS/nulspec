#!/usr/bin/env python3
"""Reject tracked private paths and network addresses before publication."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "REPOSITORY_SCOPE_POLICY.md"

PROHIBITED = {
    "POSIX user-home path": re.compile(r"(?<![A-Za-z0-9_])/" + r"home/[^/\s]+/"),
    "Windows user-home path": re.compile(
        r"(?i)(?<![A-Za-z0-9_])[A-Z]:\\Users\\[^\\\r\n]+\\"
    ),
    "RFC1918 IPv4 address": re.compile(
        r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])"
    ),
}

PINNED_DEPENDENCY = re.compile(
    r"^[A-Za-z0-9_.-]+(?:\[[^\]]+\])?==(?P<version>[A-Za-z0-9_.+-]+)"
    r"(?:\s*\\)?(?:\s*(?:;|#).*)?$"
)


def tracked_paths() -> list[Path]:
    raw = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    )
    return [ROOT / value.decode() for value in raw.split(b"\0") if value]


def is_pinned_dependency_version(text: str, start: int, end: int) -> bool:
    """Return true when an IP-shaped match is only a pinned package version."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    match = PINNED_DEPENDENCY.fullmatch(line)
    return bool(match and match.group("version") == text[start:end])


def main() -> int:
    if not POLICY.is_file():
        print(f"missing repository hygiene policy: {POLICY.relative_to(ROOT)}")
        return 1

    violations: list[str] = []
    for path in tracked_paths():
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            continue
        if b"\0" in data:
            continue

        text = data.decode("utf-8", errors="replace")
        for label, pattern in PROHIBITED.items():
            for match in pattern.finditer(text):
                if label == "RFC1918 IPv4 address" and is_pinned_dependency_version(
                    text, match.start(), match.end()
                ):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(ROOT)}:{line}: {label}")

    if violations:
        print("repository hygiene check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print(
        "repository hygiene check passed: no tracked private user-home paths "
        "or RFC1918 addresses"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

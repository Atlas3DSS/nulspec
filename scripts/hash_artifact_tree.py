from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--exclude-prefix",
        action="append",
        default=[],
        help="Relative POSIX path prefix to omit; may be repeated.",
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"artifact root is not a directory: {root}")
    if output.exists():
        raise SystemExit(f"refusing to overwrite manifest: {output}")
    if output == root or root in output.parents:
        excluded = output
    else:
        excluded = None

    files = []
    total_bytes = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        resolved = path.resolve()
        if excluded is not None and resolved == excluded:
            continue
        relative = path.relative_to(root).as_posix()
        if any(
            relative == prefix.rstrip("/")
            or relative.startswith(prefix.rstrip("/") + "/")
            for prefix in args.exclude_prefix
        ):
            continue
        size = path.stat().st_size
        total_bytes += size
        files.append(
            {
                "path": relative,
                "bytes": size,
                "sha256": sha256_file(path),
            }
        )

    payload = {
        "schema_version": 1,
        "root_label": root.name,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()

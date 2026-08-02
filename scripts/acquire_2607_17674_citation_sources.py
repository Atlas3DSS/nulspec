#!/usr/bin/env python3
"""Acquire cited PDFs into a new ignored, append-only audit directory."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = WORKSPACE / "protocols" / "2607.17674" / "citation_inventory.json"
STUDY_WORK_ROOT = WORKSPACE / "research" / "replications" / "2607.17674" / "work"
EXPECTED_INVENTORY_SHA256 = (
    "471117efcde4eb55e8a6742dc00ffc0c291f30c821e071f56834c433cdabe43a"
)
MAX_PDF_BYTES = 64 * 1024 * 1024
MAX_HTML_BYTES = 4 * 1024 * 1024
USER_AGENT = "NULSPEC-citation-audit/1.0 (+https://nulspec.com)"
SAFE_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> Request | None:
        resolved_url = validated_redirect_url(request.full_url, new_url)
        return super().redirect_request(
            request, file_pointer, code, message, headers, resolved_url
        )


HTTP_OPENER = build_opener(SafeRedirectHandler())


class PdfLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {name.lower(): value for name, value in attrs if value is not None}
        if tag.lower() == "meta":
            label = (values.get("name") or values.get("property") or "").lower()
            if label in {"citation_pdf_url", "dc.identifier.pdf", "og:pdf"}:
                if values.get("content"):
                    self.links.append(str(values["content"]))
        elif tag.lower() == "link":
            if "pdf" in str(values.get("type", "")).lower() and values.get("href"):
                self.links.append(str(values["href"]))
        elif tag.lower() == "a" and values.get("href"):
            href = str(values["href"])
            lowered = href.lower()
            if ".pdf" in lowered or "pdf" in str(values.get("type", "")).lower():
                self.links.append(href)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_https_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("source URL must use HTTPS with a hostname")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("local source hosts are forbidden")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("non-public source IP addresses are forbidden")
    return urlunparse(parsed._replace(fragment=""))


def validated_redirect_url(request_url: str, new_url: str) -> str:
    return safe_https_url(urljoin(request_url, new_url))


def direct_pdf_candidates(source_url: str) -> list[str]:
    parsed = urlparse(safe_https_url(source_url))
    host = parsed.hostname.lower() if parsed.hostname else ""
    path = parsed.path
    candidates: list[str] = []
    if path.lower().endswith(".pdf"):
        candidates.append(source_url)
    elif host in {"arxiv.org", "www.arxiv.org"} and "/abs/" in path:
        identifier = path.split("/abs/", maxsplit=1)[1].rstrip("/")
        candidates.append(f"https://arxiv.org/pdf/{identifier}")
    elif host == "aclanthology.org":
        candidates.append(f"https://aclanthology.org{path.rstrip('/')}.pdf")
    elif host == "openreview.net" and path.rstrip("/") == "/forum":
        identifier = parse_qs(parsed.query).get("id", [])
        if identifier:
            candidates.append(
                "https://openreview.net/pdf?" + urlencode({"id": identifier[0]})
            )
    elif host == "proceedings.mlr.press" and path.lower().endswith(".html"):
        stem = Path(path).stem
        parent = str(Path(path).parent).rstrip("/")
        candidates.append(
            f"https://proceedings.mlr.press{parent}/{stem}/{stem}.pdf"
        )
    return list(dict.fromkeys(safe_https_url(url) for url in candidates))


def discover_pdf_candidates(html: bytes, base_url: str) -> list[str]:
    parser = PdfLinkParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    candidates: list[str] = []
    for raw_link in parser.links:
        try:
            candidate = safe_https_url(urljoin(base_url, raw_link))
        except ValueError:
            continue
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def fetch(url: str, *, max_bytes: int, accept: str) -> tuple[bytes, dict[str, Any]]:
    requested = safe_https_url(url)
    request = Request(
        requested,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
        method="GET",
    )
    started = time.monotonic()
    with HTTP_OPENER.open(request, timeout=30) as response:
        final_url = safe_https_url(response.geturl())
        status = int(getattr(response, "status", 200))
        content_type = str(response.headers.get("Content-Type", ""))
        effective_max_bytes = (
            min(max_bytes, MAX_HTML_BYTES)
            if "html" in content_type.lower()
            else max_bytes
        )
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > effective_max_bytes:
            raise ValueError(f"response exceeds {effective_max_bytes} bytes")
        chunks: list[bytes] = []
        total = 0
        while chunk := response.read(
            min(1024 * 1024, effective_max_bytes + 1 - total)
        ):
            chunks.append(chunk)
            total += len(chunk)
            if total > effective_max_bytes:
                raise ValueError(f"response exceeds {effective_max_bytes} bytes")
    payload = b"".join(chunks)
    return payload, {
        "requested_url": requested,
        "final_url": final_url,
        "status_code": status,
        "content_type": content_type,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def attempt_fetch(
    url: str, *, max_bytes: int, accept: str, role: str
) -> tuple[bytes | None, dict[str, Any]]:
    started = time.monotonic()
    try:
        payload, record = fetch(url, max_bytes=max_bytes, accept=accept)
        return payload, {"role": role, "state": "fetched", **record}
    except HTTPError as error:
        return None, {
            "role": role,
            "state": "http_error",
            "requested_url": url,
            "status_code": error.code,
            "error": str(error.reason),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except (URLError, TimeoutError, OSError, ValueError) as error:
        return None, {
            "role": role,
            "state": "acquisition_error",
            "requested_url": url,
            "error_type": type(error).__name__,
            "error": str(error),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def is_pdf(payload: bytes, content_type: str) -> bool:
    del content_type
    return payload.lstrip().startswith(b"%PDF-")


def extract_text(pdf_path: Path, text_path: Path) -> dict[str, Any]:
    executable = shutil.which("pdftotext")
    if executable is None:
        return {"state": "not_extracted", "reason": "pdftotext_not_found"}
    try:
        result = subprocess.run(
            [executable, "-layout", str(pdf_path), str(text_path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "state": "extraction_failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
    if result.returncode != 0 or not text_path.is_file():
        return {
            "state": "extraction_failed",
            "exit_code": result.returncode,
            "stderr": result.stderr[-2000:],
        }
    if text_path.stat().st_size == 0:
        return {"state": "extraction_failed", "reason": "empty_text_output"}
    return {
        "state": "extracted",
        "relative_path": text_path.name,
        "bytes": text_path.stat().st_size,
        "sha256": sha256_file(text_path),
        "stderr": result.stderr[-2000:],
    }


def acquire_record(
    record: dict[str, Any],
    *,
    output_root: Path,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    key = str(record["key"])
    if not SAFE_KEY.fullmatch(key):
        raise ValueError(f"unsafe citation key: {key!r}")
    source_url = str((override or {}).get("url") or record["source_url"])
    safe_https_url(source_url)
    attempts: list[dict[str, Any]] = []
    candidate_urls = direct_pdf_candidates(source_url)
    pdf_payload: bytes | None = None
    selected: dict[str, Any] | None = None

    for candidate in candidate_urls:
        payload, attempt = attempt_fetch(
            candidate,
            max_bytes=MAX_PDF_BYTES,
            accept="application/pdf",
            role="direct_pdf_candidate",
        )
        attempts.append(attempt)
        if payload is not None and is_pdf(
            payload, str(attempt.get("content_type", ""))
        ):
            pdf_payload = payload
            selected = attempt
            break
        if payload is not None:
            attempt["state"] = "rejected_non_pdf"

    if pdf_payload is None:
        landing, landing_attempt = attempt_fetch(
            source_url,
            max_bytes=MAX_PDF_BYTES,
            accept="text/html,application/pdf;q=0.9",
            role="source_landing",
        )
        attempts.append(landing_attempt)
        if landing is not None and is_pdf(
            landing, str(landing_attempt.get("content_type", ""))
        ):
            pdf_payload = landing
            selected = landing_attempt
        elif landing is not None:
            landing_attempt["state"] = "landing_html"
            discovered = discover_pdf_candidates(
                landing, str(landing_attempt.get("final_url", source_url))
            )
            for candidate in discovered[:8]:
                if candidate in candidate_urls:
                    continue
                payload, attempt = attempt_fetch(
                    candidate,
                    max_bytes=MAX_PDF_BYTES,
                    accept="application/pdf",
                    role="discovered_pdf_candidate",
                )
                attempts.append(attempt)
                if payload is not None and is_pdf(
                    payload, str(attempt.get("content_type", ""))
                ):
                    pdf_payload = payload
                    selected = attempt
                    break
                if payload is not None:
                    attempt["state"] = "rejected_non_pdf"

    result: dict[str, Any] = {
        "key": key,
        "title": record.get("title"),
        "bibliographic_source_url": record.get("source_url"),
        "acquisition_source_url": source_url,
        "override": override,
        "license": "not verified; local audit copy only",
        "redistribution": "disabled",
        "attempts": attempts,
    }
    if pdf_payload is None or selected is None:
        result["state"] = "not_acquired"
        return result

    pdf_path = output_root / f"{key}.pdf"
    text_path = output_root / f"{key}.txt"
    pdf_path.write_bytes(pdf_payload)
    text_record = extract_text(pdf_path, text_path)
    result.update(
        {
            "state": (
                "ready"
                if text_record["state"] == "extracted"
                else "pdf_acquired_text_failed"
            ),
            "selected_url": selected.get("final_url"),
            "pdf": {
                "relative_path": pdf_path.name,
                "bytes": len(pdf_payload),
                "sha256": sha256_bytes(pdf_payload),
            },
            "text": text_record,
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    args = parser.parse_args()

    inventory_path = args.inventory.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite acquisition root: {output_root}")
    if output_root == Path(output_root.anchor):
        raise SystemExit("refusing broad acquisition root")
    try:
        output_root.relative_to(STUDY_WORK_ROOT.resolve())
    except ValueError as error:
        raise SystemExit(
            f"acquisition root must be inside {STUDY_WORK_ROOT}"
        ) from error
    if args.delay_seconds < 0:
        raise SystemExit("delay must be nonnegative")

    inventory_hash = sha256_file(inventory_path)
    if inventory_hash != EXPECTED_INVENTORY_SHA256:
        raise SystemExit(
            "citation inventory hash does not match audit protocol v1.0.0"
        )
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    records = [record for record in inventory["records"] if record["cited"]]
    if len(records) != 41 or int(inventory["citation_occurrences"]) != 74:
        raise SystemExit("citation inventory cardinality does not match protocol")
    overrides: dict[str, Any] = {}
    if args.overrides is not None:
        overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
        unknown = sorted(set(overrides) - {str(record["key"]) for record in records})
        if unknown:
            raise SystemExit(f"overrides contain unknown citation keys: {unknown}")
        malformed = sorted(
            key
            for key, value in overrides.items()
            if not isinstance(value, dict) or not isinstance(value.get("url"), str)
        )
        if malformed:
            raise SystemExit(f"malformed citation overrides: {malformed}")

    output_root.mkdir(parents=True)
    started_at = utc_now()
    results: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        print(f"[{index + 1}/{len(records)}] {record['key']}", flush=True)
        results.append(
            acquire_record(
                record,
                output_root=output_root,
                override=overrides.get(str(record["key"])),
            )
        )
        if index + 1 < len(records):
            time.sleep(args.delay_seconds)

    summary = {
        state: sum(result["state"] == state for result in results)
        for state in ("ready", "pdf_acquired_text_failed", "not_acquired")
    }
    manifest = {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "protocol_version": "1.0.0",
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "inventory": {
            "relative_path": "protocols/2607.17674/citation_inventory.json",
            "sha256": inventory_hash,
            "cited_entries": len(records),
        },
        "retrieval": {
            "user_agent": USER_AGENT,
            "maximum_pdf_bytes": MAX_PDF_BYTES,
            "maximum_html_bytes": MAX_HTML_BYTES,
            "delay_seconds": args.delay_seconds,
            "command": (
                "python scripts/acquire_2607_17674_citation_sources.py "
                "--output-root <new-ignored-run-directory>"
            ),
        },
        "summary": summary,
        "sources": results,
    }
    manifest_path = output_root / "acquisition-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["not_acquired"] or summary["pdf_acquired_text_failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run independent GLM and Kimi reviews after a technical Fable refusal.

Every model receives the exact packet and user prompt used for Fable. Raw
OpenRouter responses remain in the caller-supplied ignored output directory.
The generated summary excludes credentials and provider request identifiers.
Existing attempt markers are never overwritten, so this command cannot retry a
completed or failed model invocation silently.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


SCHEMA_VERSION = "nulspec-openrouter-supplemental-review-v4"
SUMMARY_SCHEMA = "nulspec-openrouter-supplemental-review-set-v4"
DEFAULT_MODELS = ("z-ai/glm-5.2", "moonshotai/kimi-k3")
OPENROUTER = "https://openrouter.ai/api/v1"


class FallbackReviewError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise FallbackReviewError(f"expected JSON object: {path}")
    return value


def load_fable_contract(study_root: Path) -> Any:
    path = study_root / "scripts" / "fable_final_review.py"
    spec = importlib.util.spec_from_file_location("nulspec_fable_contract", path)
    if spec is None or spec.loader is None:
        raise FallbackReviewError("cannot load the Fable review contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request_json(
    url: str,
    key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 1800,
) -> tuple[int, bytes]:
    body = None
    method = "GET"
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "HTTP-Referer": "https://nulspec.com",
        "X-Title": "NULSPEC",
    }
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        method = "POST"
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def model_catalog_entry(model_id: str, key: str) -> tuple[dict[str, Any], str]:
    author, slug = model_id.split("/", 1)
    url = f"{OPENROUTER}/model/{urllib.parse.quote(author)}/{urllib.parse.quote(slug)}"
    status, raw = request_json(url, key, timeout=60)
    if status != 200:
        raise FallbackReviewError(f"model catalog returned HTTP {status} for {model_id}")
    payload = json.loads(raw)
    entry = payload.get("data")
    if not isinstance(entry, dict) or entry.get("id") != model_id:
        raise FallbackReviewError(f"model catalog did not resolve {model_id}")
    canonical = entry.get("canonical_slug")
    parameters = entry.get("supported_parameters")
    if (
        not isinstance(canonical, str)
        or canonical == model_id
        or not isinstance(parameters, list)
        or "structured_outputs" not in parameters
        or int(entry.get("context_length") or 0) < 1_000_000
    ):
        raise FallbackReviewError(f"model is not a pinned large-context reviewer: {model_id}")
    return entry, sha256_bytes(
        json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()
    )


def model_directory(model_id: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", model_id.lower()).strip("-")
    if not value:
        raise FallbackReviewError("model ID cannot form an output directory")
    return value


def parse_content(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise FallbackReviewError("OpenRouter response must contain one choice")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise FallbackReviewError("OpenRouter response has no assistant message")
    refusal = message.get("refusal")
    if refusal:
        raise FallbackReviewError("supplemental reviewer refused the packet")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise FallbackReviewError("supplemental reviewer returned no content")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise FallbackReviewError("supplemental review is not a JSON object")
    return value


def supplemental_schema(contract: Any) -> dict[str, Any]:
    schema = deepcopy(contract.OUTPUT_SCHEMA)
    for field in ("human_review_required", "next_step"):
        schema["required"].remove(field)
        schema["properties"].pop(field)
    schema["properties"]["summary"]["description"] = (
        "Complete overall peer-review finding supported by the supplied packet."
    )
    check_properties = schema["properties"]["checks"]["items"]["properties"]
    check_properties["finding"]["description"] = (
        "Substantive finding for this review area."
    )
    check_properties["evidence"]["description"] = (
        "Specific packet fields, document sections, values, or hashes supporting the finding."
    )
    return schema


def review_harness(model_id: str, prompt: str, contract: Any) -> dict[str, Any]:
    """Return a documented model-family-specific review harness."""
    schema = supplemental_schema(contract)
    profile = "generic-high-depth-structured-review-v2"
    system_prompt = (
        "You are an independent supplemental peer reviewer for a small "
        "scientific replication team. Anthropic's Fable reviewer refused the "
        "same packet before substantive review. Judge only the committed "
        "evidence supplied by the user. Do not use tools, invent evidence, "
        "rewrite results, or optimize for agreement. Return only the requested "
        "structured output. Your review informs a human publication decision "
        "and cannot authorize an author email."
    )
    user_prompt = prompt
    request_parameters: dict[str, Any] = {
        "temperature": 1.0,
        "max_tokens": 131072,
        "reasoning": {"effort": "high"},
        "provider": {"require_parameters": True},
    }

    if model_id.startswith("z-ai/glm-"):
        if "<review_request>" in prompt or "</review_request>" in prompt:
            raise FallbackReviewError("review prompt collides with GLM delimiters")
        profile = "glm-high-depth-structured-review-v1"
        system_prompt = (
            "You are an independent scientific peer reviewer. The user message "
            "contains one immutable review request inside <review_request> tags. "
            "Use only that reference text and examine it in full. Think deeply "
            "before deciding. Evaluate each required review area independently, "
            "check prose against machine evidence, and cite precise packet fields, "
            "documents, values, or hashes. Do not use tools, invent evidence, "
            "rewrite results, or optimize for agreement. Return exactly one JSON "
            "object matching the response schema, with no Markdown or surrounding "
            "text. Use as much detail as the evidence requires. The review informs "
            "a human publication decision and cannot authorize publication or an "
            "author email."
        )
        user_prompt = f"<review_request>\n{prompt}\n</review_request>"
        request_parameters = {
            "temperature": 1.0,
            "max_tokens": 131072,
            "reasoning": {"effort": "high"},
            "provider": {
                "order": ["deepinfra", "streamlake", "decart", "alibaba"],
                "allow_fallbacks": True,
                "require_parameters": True,
            },
        }
    elif model_id.startswith("moonshotai/kimi-"):
        if "<review_request>" in prompt or "</review_request>" in prompt:
            raise FallbackReviewError("review prompt collides with Kimi delimiters")
        profile = "kimi-high-depth-structured-review-v2"
        system_prompt = (
            "You are Kimi acting as an independent scientific peer reviewer. "
            "The user message contains one immutable review request inside "
            "<review_request> tags. Use only that reference text.\n\n"
            "Complete these steps internally before responding:\n"
            "1. Verify the packet digest and evaluate all eight required areas.\n"
            "2. Choose exactly one verdict under the supplied PASS, FAIL, and "
            "HARD_FAIL contract.\n"
            "3. Check that every claim cites a specific packet field or document.\n"
            "4. Return exactly one JSON object matching the response schema.\n\n"
            "Return no Markdown, preface, or text outside the JSON object. Include "
            "each of the eight check areas exactly once. Use as much detail as the "
            "evidence requires; do not compress a finding merely to shorten the "
            "response. PASS requires eight PASS checks, an empty action_items "
            "array, and an empty hard_fail_reason. The review informs a human "
            "publication decision and cannot authorize publication or an author "
            "email."
        )
        user_prompt = f"<review_request>\n{prompt}\n</review_request>"
        request_parameters = {
            "temperature": 1.0,
            # The selected endpoints expose a 1,048,576-token context and output
            # ceiling. This packet uses about 169,700 input tokens, so 870,000 is
            # the largest safe request allowance across small tokenizer variance.
            "max_tokens": 870000,
            "reasoning": {"effort": "high"},
            "provider": {
                "order": ["modal", "together", "morph", "moonshotai"],
                "ignore": ["fireworks"],
                "allow_fallbacks": True,
                "require_parameters": True,
            },
        }

    return {
        "profile": profile,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response_schema": schema,
        "request_parameters": request_parameters,
    }


def validate_supplemental_decision(
    decision: dict[str, Any], packet_sha256: str, contract: Any
) -> None:
    if decision.get("reviewed_packet_sha256") != packet_sha256:
        raise FallbackReviewError("reviewer returned a different packet digest")
    verdict = decision.get("verdict")
    if verdict not in {"PASS", "FAIL", "HARD_FAIL"}:
        raise FallbackReviewError("reviewer returned an invalid verdict")
    checks = decision.get("checks")
    if not isinstance(checks, list) or len(checks) != len(contract.EXPECTED_AREAS):
        raise FallbackReviewError("reviewer did not return eight checks")
    areas = [row.get("area") for row in checks if isinstance(row, dict)]
    statuses = [row.get("status") for row in checks if isinstance(row, dict)]
    if set(areas) != contract.EXPECTED_AREAS or len(areas) != len(set(areas)):
        raise FallbackReviewError("review check areas are incomplete or duplicated")
    if not all(status in {"PASS", "FAIL"} for status in statuses):
        raise FallbackReviewError("review contains an invalid check status")
    actions = decision.get("action_items")
    if not isinstance(actions, list):
        raise FallbackReviewError("review action_items is not an array")
    action_ids = [row.get("id") for row in actions if isinstance(row, dict)]
    hard_reason = str(decision.get("hard_fail_reason") or "").strip()
    if verdict == "PASS":
        if actions or hard_reason or any(status != "PASS" for status in statuses):
            raise FallbackReviewError("PASS violates the substantive review contract")
    elif verdict == "FAIL":
        if action_ids != ["F1", "F2", "F3"] or hard_reason or "FAIL" not in statuses:
            raise FallbackReviewError("FAIL violates the three-action contract")
    elif actions or not hard_reason or "FAIL" not in statuses:
        raise FallbackReviewError("HARD_FAIL violates the human-escalation contract")
    for field in (
        "single_review_acknowledged",
        "no_resubmission_acknowledged",
        "human_email_approval_acknowledged",
    ):
        if decision.get(field) is not True:
            raise FallbackReviewError(f"reviewer did not acknowledge {field}")


def public_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return {}
    allowed = (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost",
        "is_byok",
        "prompt_tokens_details",
        "completion_tokens_details",
    )
    return {key: usage[key] for key in allowed if key in usage}


def review_one(
    model_id: str,
    key: str,
    output_root: Path,
    packet_sha256: str,
    prompt: str,
    contract: Any,
    attempt_id: str | None,
    recovery_of: str | None,
    comparison_group: str | None,
    comparison_label: str | None,
) -> dict[str, Any]:
    directory = output_root / model_directory(model_id)
    attempt_path = directory / "attempt.json"
    raw_path = directory / "raw.json"
    if attempt_path.exists():
        raise FallbackReviewError(
            f"attempt already exists for {model_id}; automatic retry is forbidden"
        )

    catalog, catalog_sha256 = model_catalog_entry(model_id, key)
    canonical_slug = catalog["canonical_slug"]
    harness = review_harness(model_id, prompt, contract)
    system_prompt = harness["system_prompt"]
    user_prompt = harness["user_prompt"]
    request_parameters = harness["request_parameters"]
    started_at = now()
    attempt = {
        "schema_version": SCHEMA_VERSION,
        "status": "started",
        "started_at_utc": started_at,
        "model_id": model_id,
        "canonical_slug": canonical_slug,
        "catalog_entry_sha256": catalog_sha256,
        "packet_sha256": packet_sha256,
        "prompt_sha256": sha256_bytes(prompt.encode()),
        "submitted_user_prompt_sha256": sha256_bytes(user_prompt.encode()),
        "system_prompt_sha256": sha256_bytes(system_prompt.encode()),
        "harness_profile": harness["profile"],
        "request_parameters": request_parameters,
        "attempt_id": attempt_id,
        "recovery_of": recovery_of,
        "comparison_group": comparison_group,
        "comparison_label": comparison_label,
        "invocation_count": 1,
        "retry_allowed": False,
    }
    atomic_json(attempt_path, attempt)

    payload = {
        "model": canonical_slug,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "nulspec_supplemental_peer_review",
                "strict": True,
                "schema": harness["response_schema"],
            },
        },
        **request_parameters,
    }
    start = time.monotonic()
    status, raw = request_json(f"{OPENROUTER}/chat/completions", key, payload)
    elapsed = round(time.monotonic() - start, 6)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    completed_at = now()

    public: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed_invalid",
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "elapsed_seconds": elapsed,
        "model": {
            "requested_id": model_id,
            "canonical_slug": canonical_slug,
            "catalog_entry_sha256": catalog_sha256,
            "context_length": catalog["context_length"],
        },
        "packet_sha256": packet_sha256,
        "prompt_sha256": sha256_bytes(prompt.encode()),
        "submitted_user_prompt_sha256": sha256_bytes(user_prompt.encode()),
        "system_prompt_sha256": sha256_bytes(system_prompt.encode()),
        "harness": {
            "profile": harness["profile"],
            "request_parameters": request_parameters,
            "user_prompt_wrapped": user_prompt != prompt,
        },
        "attempt_id": attempt_id,
        "recovery_of": recovery_of,
        "comparison_group": comparison_group,
        "comparison_label": comparison_label,
        "http_status": status,
        "raw_response_byte_count": len(raw),
        "raw_response_sha256": sha256_bytes(raw),
        "raw_response_public": False,
        "invocation_count": 1,
        "retry_allowed": False,
    }
    failure = None
    try:
        response = json.loads(raw)
        if not isinstance(response, dict):
            raise FallbackReviewError("OpenRouter response is not an object")
        public["usage"] = public_usage(response)
        provider_error = response.get("error")
        if isinstance(provider_error, dict):
            public["status"] = "provider_failed_before_model_output"
            public["provider_error"] = {
                "code": provider_error.get("code"),
                "message": provider_error.get("message"),
            }
            public["model_output_returned"] = False
            public["reported_charge_usd"] = public["usage"].get("cost", 0)
            raise FallbackReviewError(
                "OpenRouter provider error "
                f"{provider_error.get('code')}: "
                f"{provider_error.get('message') or 'request failed'}"
            )
        if status != 200:
            error = response.get("error")
            message = error.get("message") if isinstance(error, dict) else None
            raise FallbackReviewError(
                f"OpenRouter returned HTTP {status}: {message or 'request failed'}"
            )
        decision = parse_content(response)
        validate_supplemental_decision(decision, packet_sha256, contract)
        public["status"] = "completed_valid"
        public["decision"] = decision
        public["release_control"] = {
            "publication_authorized": False,
            "human_disposition_required": True,
            "author_email_dispatch_authorized": False,
        }
    except Exception as error:  # The attempt must be retained for every failure.
        failure = f"{type(error).__name__}: {error}"
        public["failure"] = failure

    attempt.update(
        {
            "status": public["status"],
            "completed_at_utc": completed_at,
            "elapsed_seconds": elapsed,
            "http_status": status,
            "raw_response_byte_count": len(raw),
            "raw_response_sha256": sha256_bytes(raw),
            "failure": failure,
        }
    )
    atomic_json(attempt_path, attempt)
    atomic_json(directory / "public-result.json", public)
    return public


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--attempt-id")
    parser.add_argument("--recovery-of")
    parser.add_argument("--comparison-group")
    parser.add_argument("--comparison-label")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {"'", '"'}:
        key = key[1:-1]
    if not key:
        print("OPENROUTER_FALLBACK_FAILED: OPENROUTER_API_KEY is unset", file=sys.stderr)
        return 2
    if not key.startswith("sk-or-v1-"):
        print(
            "OPENROUTER_FALLBACK_FAILED: OPENROUTER_API_KEY has an unexpected format",
            file=sys.stderr,
        )
        return 2
    study_root = args.study_root.resolve()
    output_root = args.output_root.resolve()
    models = tuple(args.models or DEFAULT_MODELS)
    if len(models) != len(set(models)) or not models:
        print("OPENROUTER_FALLBACK_FAILED: models must be unique", file=sys.stderr)
        return 2
    if (
        args.attempt_id
        or args.recovery_of
        or args.comparison_group
        or args.comparison_label
    ) and len(models) != 1:
        print(
            "OPENROUTER_FALLBACK_FAILED: recovery metadata requires one model",
            file=sys.stderr,
        )
        return 2
    if bool(args.comparison_group) != bool(args.comparison_label):
        print(
            "OPENROUTER_FALLBACK_FAILED: comparison group and label are paired",
            file=sys.stderr,
        )
        return 2

    try:
        contract = load_fable_contract(study_root)
        packet_path = study_root / "results" / "fable_final_review_packet.json"
        review_path = study_root / "results" / "fable_final_peer_review.json"
        packet = packet_path.read_bytes()
        review = load_object(review_path)
        packet_sha256 = sha256_bytes(packet)
        if review.get("decision", {}).get("verdict") != "HARD_FAIL":
            raise FallbackReviewError("fallback review requires a Fable HARD_FAIL")
        metadata = review.get("invocation", {}).get("wrapper_metadata", {})
        if metadata.get("stop_reason") != "refusal":
            raise FallbackReviewError("Fable result is not a recorded refusal")
        if review.get("packet", {}).get("sha256") != packet_sha256:
            raise FallbackReviewError("Fable packet digest does not match retained bytes")
        prompt = contract.prompt_for_packet(packet.decode(), packet_sha256)
        if review.get("invocation", {}).get("prompt_sha256") != sha256_bytes(
            prompt.encode()
        ):
            raise FallbackReviewError("fallback prompt differs from the Fable prompt")

        results = []
        for model_id in models:
            try:
                result = review_one(
                    model_id,
                    key,
                    output_root,
                    packet_sha256,
                    prompt,
                    contract,
                    args.attempt_id,
                    args.recovery_of,
                    args.comparison_group,
                    args.comparison_label,
                )
            except Exception as error:
                result = {
                    "schema_version": SCHEMA_VERSION,
                    "status": "setup_failed",
                    "model": {"requested_id": model_id},
                    "failure": f"{type(error).__name__}: {error}",
                }
            results.append(result)
            print(
                f"OPENROUTER_FALLBACK_RESULT model={model_id} status={result['status']}",
                flush=True,
            )

        summary = {
            "schema_version": SUMMARY_SCHEMA,
            "generated_at_utc": now(),
            "source_fable_result_sha256": sha256_bytes(review_path.read_bytes()),
            "packet_sha256": packet_sha256,
            "prompt_sha256": sha256_bytes(prompt.encode()),
            "minimum_successful_reviews": 1,
            "preferred_successful_reviews": 2,
            "human_disposition_required": True,
            "attempt_id": args.attempt_id,
            "recovery_of": args.recovery_of,
            "comparison_group": args.comparison_group,
            "comparison_label": args.comparison_label,
            "results": results,
        }
        atomic_json(output_root / "summary.json", summary)
        successful = sum(result.get("status") == "completed_valid" for result in results)
        print(
            f"OPENROUTER_FALLBACK_COMPLETE successful={successful} attempted={len(results)}",
            flush=True,
        )
        return 0 if successful >= 1 else 4
    except Exception as error:
        print(f"OPENROUTER_FALLBACK_FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

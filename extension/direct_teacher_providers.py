#!/usr/bin/env python3
"""Direct, streamed provider routes for NULSPEC's GLM and Kimi teachers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import http.client
import json
from pathlib import Path
import socket
import time
from typing import Any
import urllib.parse


FIRST_EVENT_TIMEOUT_SECONDS = 60
STREAM_IDLE_TIMEOUT_SECONDS = 60
TOTAL_RESPONSE_TIMEOUT_SECONDS = 240
MAX_ERROR_BODY_BYTES = 1_048_576


@dataclass(frozen=True)
class ProviderRoute:
    """One exact provider/model route, excluding its secret API key."""

    route_id: str
    provider_name: str
    endpoint: str
    provider_model_id: str
    key_env: str
    context_length: int
    max_completion_tokens: int
    max_tokens_field: str
    schema_mode: str
    reasoning_parameters: dict[str, Any]
    request_parameters: dict[str, Any]
    input_usd_per_million: float
    cached_input_usd_per_million: float
    output_usd_per_million: float
    pricing_observed_at: str = "2026-08-01"

    def public_record(self) -> dict[str, Any]:
        record = asdict(self)
        record.pop("key_env")
        return record


PROVIDER_ROUTES: dict[str, tuple[ProviderRoute, ...]] = {
    "z-ai/glm-5.2": (
        ProviderRoute(
            route_id="openrouter-latency-routed",
            provider_name="OpenRouter",
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            provider_model_id="z-ai/glm-5.2",
            key_env="OPENROUTER_API_KEY",
            context_length=1_048_576,
            max_completion_tokens=131_072,
            max_tokens_field="max_tokens",
            schema_mode="json_schema",
            reasoning_parameters={"reasoning": {"effort": "high"}},
            request_parameters={
                "provider": {
                    "sort": "latency",
                    "allow_fallbacks": True,
                    "require_parameters": True,
                    "data_collection": "deny",
                }
            },
            input_usd_per_million=1.40,
            cached_input_usd_per_million=0.26,
            output_usd_per_million=4.40,
        ),
        ProviderRoute(
            route_id="openrouter-explicit-provider-reroute",
            provider_name="OpenRouter",
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            provider_model_id="z-ai/glm-5.2",
            key_env="OPENROUTER_API_KEY",
            context_length=1_048_576,
            max_completion_tokens=131_072,
            max_tokens_field="max_tokens",
            schema_mode="json_schema",
            reasoning_parameters={"reasoning": {"effort": "high"}},
            request_parameters={
                "provider": {
                    "order": [
                        "decart",
                        "novita",
                        "deepinfra",
                        "fireworks",
                        "friendli",
                    ],
                    "allow_fallbacks": True,
                    "require_parameters": True,
                    "data_collection": "deny",
                }
            },
            input_usd_per_million=1.40,
            cached_input_usd_per_million=0.26,
            output_usd_per_million=4.40,
        ),
    ),
    "moonshotai/kimi-k3": (
        ProviderRoute(
            route_id="moonshot-first-party",
            provider_name="Moonshot AI",
            endpoint="https://api.moonshot.ai/v1/chat/completions",
            provider_model_id="kimi-k3",
            key_env="MOONSHOT_API_KEY",
            context_length=1_048_576,
            max_completion_tokens=1_048_576,
            max_tokens_field="max_completion_tokens",
            schema_mode="json_schema",
            reasoning_parameters={"reasoning_effort": "high"},
            request_parameters={},
            input_usd_per_million=3.00,
            cached_input_usd_per_million=0.30,
            output_usd_per_million=15.00,
        ),
        ProviderRoute(
            route_id="fireworks-direct-fallback",
            provider_name="Fireworks AI",
            endpoint="https://api.fireworks.ai/inference/v1/chat/completions",
            provider_model_id="accounts/fireworks/models/kimi-k3",
            key_env="FIREWORKS_API_KEY",
            context_length=1_048_576,
            max_completion_tokens=1_048_576,
            max_tokens_field="max_tokens",
            schema_mode="prompt_schema",
            reasoning_parameters={"reasoning_effort": "high"},
            request_parameters={"perf_metrics_in_response": True},
            input_usd_per_million=3.00,
            cached_input_usd_per_million=0.30,
            output_usd_per_million=15.00,
        ),
    ),
}


class ProviderStreamError(RuntimeError):
    """A streamed request failed, with partial non-secret trace metadata."""

    def __init__(self, message: str, metadata: dict[str, Any] | None = None):
        super().__init__(message)
        self.metadata = metadata or {}


def route_for(model_id: str, route_index: int) -> ProviderRoute:
    routes = PROVIDER_ROUTES.get(model_id)
    if not routes:
        raise ProviderStreamError(f"no direct provider routes for {model_id}")
    if not 0 <= route_index < len(routes):
        raise ProviderStreamError(
            f"provider route index {route_index} is invalid for {model_id}"
        )
    return routes[route_index]


def route_count(model_id: str) -> int:
    return len(PROVIDER_ROUTES.get(model_id, ()))


def available_completion_tokens(
    route: ProviderRoute, system_prompt: str, user_prompt: str
) -> tuple[int, str]:
    """Use the provider maximum without exceeding the model context window."""

    conservative_input_tokens = (len((system_prompt + user_prompt).encode()) + 1) // 2
    context_available = route.context_length - conservative_input_tokens - 8192
    maximum = min(route.max_completion_tokens, context_available)
    if maximum < 16_384:
        raise ProviderStreamError(
            "packet leaves insufficient direct-provider completion capacity"
        )
    if maximum == route.max_completion_tokens:
        basis = "provider_documented_maximum_output_tokens"
    else:
        basis = "provider_context_minus_conservative_input_and_safety"
    return maximum, basis


def build_stream_payload(
    route: ProviderRoute,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    max_completion_tokens: int,
) -> dict[str, Any]:
    """Build one provider-native high/max-reasoning streaming request."""

    schema_text = json.dumps(schema, indent=2, sort_keys=True)
    schema_instruction = (
        "\n\nThe final content must be exactly one JSON object matching this "
        "schema. Do not put the JSON in a Markdown fence:\n"
        f"<output_schema>\n{schema_text}\n</output_schema>"
    )
    payload: dict[str, Any] = {
        "model": route.provider_model_id,
        "messages": [
            {"role": "system", "content": system_prompt + schema_instruction},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 1.0,
        "stream": True,
        "stream_options": {"include_usage": True},
        route.max_tokens_field: max_completion_tokens,
        **route.reasoning_parameters,
        **route.request_parameters,
    }
    if route.schema_mode == "json_schema":
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "nulspec_qwen_outer_teacher_audit",
                "strict": True,
                "schema": schema,
            },
        }
    elif route.schema_mode == "json_object":
        payload["response_format"] = {"type": "json_object"}
    elif route.schema_mode != "prompt_schema":
        raise ProviderStreamError(
            f"unsupported schema mode for {route.route_id}: {route.schema_mode}"
        )
    return payload


def _set_socket_timeout(
    connection: http.client.HTTPSConnection, seconds: float
) -> None:
    if connection.sock is None:
        raise ProviderStreamError("provider connection has no active socket")
    connection.sock.settimeout(max(0.05, seconds))


def _response_metadata(
    *,
    started: float,
    status: int | None,
    raw_count: int,
    raw_hash: Any,
    event_count: int,
    first_event_at: float | None,
    last_event_at: float | None,
    response_headers: dict[str, str],
) -> dict[str, Any]:
    completed = time.monotonic()
    return {
        "http_status": status,
        "elapsed_seconds": round(completed - started, 6),
        "raw_response_byte_count": raw_count,
        "raw_response_sha256": raw_hash.hexdigest(),
        "stream_event_count": event_count,
        "time_to_first_event_seconds": (
            round(first_event_at - started, 6) if first_event_at is not None else None
        ),
        "last_event_elapsed_seconds": (
            round(last_event_at - started, 6) if last_event_at is not None else None
        ),
        "response_headers": response_headers,
        "first_event_timeout_seconds": FIRST_EVENT_TIMEOUT_SECONDS,
        "stream_idle_timeout_seconds": STREAM_IDLE_TIMEOUT_SECONDS,
        "total_response_timeout_seconds": TOTAL_RESPONSE_TIMEOUT_SECONDS,
    }


def _content_from_event(
    event: dict[str, Any], content: list[str], reasoning: list[str]
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    choices = event.get("choices")
    finish_reason = None
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            finish_reason = choice.get("finish_reason")
            delta = choice.get("delta")
            if isinstance(delta, dict):
                value = delta.get("content")
                if isinstance(value, str):
                    content.append(value)
                for key in ("reasoning_content", "reasoning"):
                    value = delta.get(key)
                    if isinstance(value, str):
                        reasoning.append(value)
    usage = event.get("usage")
    if not isinstance(usage, dict):
        usage = None
    model = event.get("model")
    return finish_reason, usage, model if isinstance(model, str) else None


def stream_chat_completion(
    route: ProviderRoute,
    key: str,
    payload: dict[str, Any],
    raw_path: Path,
    events_path: Path,
) -> dict[str, Any]:
    """Stream one request while enforcing first-event, idle, and total limits."""

    parsed = urllib.parse.urlsplit(route.endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ProviderStreamError(f"invalid HTTPS endpoint for {route.route_id}")
    request_path = parsed.path or "/"
    if parsed.query:
        request_path += "?" + parsed.query
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "NULSPEC-review-hierarchy/1",
    }
    if route.provider_name == "OpenRouter":
        headers["HTTP-Referer"] = "https://nulspec.com"
        headers["X-Title"] = "NULSPEC review hierarchy"
    connection = http.client.HTTPSConnection(
        parsed.hostname,
        parsed.port or 443,
        timeout=FIRST_EVENT_TIMEOUT_SECONDS,
    )
    started = time.monotonic()
    status: int | None = None
    raw_count = 0
    raw_hash = hashlib.sha256()
    event_count = 0
    first_event_at: float | None = None
    last_event_at: float | None = None
    response_headers: dict[str, str] = {}
    content: list[str] = []
    reasoning: list[str] = []
    final_usage: dict[str, Any] = {}
    finish_reason: str | None = None
    response_model: str | None = None
    done = False
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection.request("POST", request_path, body=body, headers=headers)
        response = connection.getresponse()
        status = response.status
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        with raw_path.open("xb") as raw_handle, events_path.open("xb") as events:
            if status != 200:
                remaining = max(
                    0.05,
                    TOTAL_RESPONSE_TIMEOUT_SECONDS - (time.monotonic() - started),
                )
                _set_socket_timeout(
                    connection, min(STREAM_IDLE_TIMEOUT_SECONDS, remaining)
                )
                error_body = response.read(MAX_ERROR_BODY_BYTES)
                raw_handle.write(error_body)
                raw_handle.flush()
                raw_count += len(error_body)
                raw_hash.update(error_body)
                message = error_body.decode(errors="replace")
                raise ProviderStreamError(
                    f"{route.provider_name} returned HTTP {status}: {message}"
                )

            while True:
                current = time.monotonic()
                total_remaining = TOTAL_RESPONSE_TIMEOUT_SECONDS - (current - started)
                if total_remaining <= 0:
                    raise ProviderStreamError(
                        "provider stream exceeded the total response deadline"
                    )
                if first_event_at is None:
                    phase_remaining = FIRST_EVENT_TIMEOUT_SECONDS - (current - started)
                    phase = "first provider event"
                else:
                    assert last_event_at is not None
                    phase_remaining = STREAM_IDLE_TIMEOUT_SECONDS - (
                        current - last_event_at
                    )
                    phase = "next provider event"
                if phase_remaining <= 0:
                    raise ProviderStreamError(f"timed out waiting for {phase}")
                _set_socket_timeout(connection, min(total_remaining, phase_remaining))
                try:
                    line = response.readline()
                except (TimeoutError, socket.timeout) as error:
                    raise ProviderStreamError(
                        f"timed out waiting for {phase}"
                    ) from error
                if not line:
                    break
                raw_handle.write(line)
                raw_handle.flush()
                raw_count += len(line)
                raw_hash.update(line)
                if not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                observed = time.monotonic()
                if first_event_at is None:
                    first_event_at = observed
                last_event_at = observed
                if data == b"[DONE]":
                    done = True
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError as error:
                    raise ProviderStreamError(
                        "provider emitted a malformed SSE JSON event"
                    ) from error
                if not isinstance(event, dict):
                    raise ProviderStreamError("provider emitted a non-object SSE event")
                if isinstance(event.get("error"), dict):
                    provider_error = event["error"]
                    raise ProviderStreamError(
                        "provider stream error "
                        f"{provider_error.get('code')}: "
                        f"{provider_error.get('message') or 'request failed'}"
                    )
                events.write(json.dumps(event, sort_keys=True).encode() + b"\n")
                events.flush()
                event_count += 1
                event_finish, usage, model = _content_from_event(
                    event, content, reasoning
                )
                if event_finish is not None:
                    finish_reason = event_finish
                if usage is not None:
                    final_usage = usage
                if model is not None:
                    response_model = model

        metadata = _response_metadata(
            started=started,
            status=status,
            raw_count=raw_count,
            raw_hash=raw_hash,
            event_count=event_count,
            first_event_at=first_event_at,
            last_event_at=last_event_at,
            response_headers=response_headers,
        )
        if first_event_at is None:
            raise ProviderStreamError(
                "provider stream ended before its first event", metadata
            )
        if not done:
            raise ProviderStreamError("provider stream ended without [DONE]", metadata)
        if finish_reason not in {"stop", "end_turn"}:
            raise ProviderStreamError(
                f"provider stream ended with finish_reason={finish_reason!r}", metadata
            )
        return {
            **metadata,
            "content": "".join(content),
            "reasoning_content": "".join(reasoning),
            "usage": final_usage,
            "finish_reason": finish_reason,
            "response_model": response_model,
        }
    except ProviderStreamError as error:
        if not error.metadata:
            error.metadata.update(
                _response_metadata(
                    started=started,
                    status=status,
                    raw_count=raw_count,
                    raw_hash=raw_hash,
                    event_count=event_count,
                    first_event_at=first_event_at,
                    last_event_at=last_event_at,
                    response_headers=response_headers,
                )
            )
        raise
    except Exception as error:
        metadata = _response_metadata(
            started=started,
            status=status,
            raw_count=raw_count,
            raw_hash=raw_hash,
            event_count=event_count,
            first_event_at=first_event_at,
            last_event_at=last_event_at,
            response_headers=response_headers,
        )
        raise ProviderStreamError(
            f"{type(error).__name__}: {error}", metadata
        ) from error
    finally:
        connection.close()


def normalized_usage(route: ProviderRoute, usage: dict[str, Any]) -> dict[str, Any]:
    """Project provider usage and record a rate-card cost estimate."""

    projected = {
        key: usage[key]
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "prompt_tokens_details",
            "completion_tokens_details",
            "cached_tokens",
            "estimated_cost",
            "cost",
            "is_byok",
        )
        if key in usage
    }
    provider_cost = usage.get("estimated_cost")
    if not isinstance(provider_cost, (int, float)):
        provider_cost = usage.get("cost")
    if isinstance(provider_cost, (int, float)):
        projected["cost"] = float(provider_cost)
        projected["cost_source"] = "provider_reported_estimated_cost"
        return projected
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    cached = int(usage.get("cached_tokens") or 0)
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = int(details.get("cached_tokens") or cached)
    cached = min(max(0, cached), prompt)
    uncached = prompt - cached
    cost = (
        uncached * route.input_usd_per_million
        + cached * route.cached_input_usd_per_million
        + completion * route.output_usd_per_million
    ) / 1_000_000
    projected["cost"] = round(cost, 12)
    projected["cost_source"] = (
        f"calculated_from_{route.provider_name}_rate_card_{route.pricing_observed_at}"
    )
    return projected

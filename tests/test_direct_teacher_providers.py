from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "extension" / "direct_teacher_providers.py"
SPEC = importlib.util.spec_from_file_location("direct_teacher_providers", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PROVIDERS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROVIDERS
SPEC.loader.exec_module(PROVIDERS)


def test_public_routes_do_not_expose_secret_environment_names() -> None:
    assert PROVIDERS.route_count("z-ai/glm-5.2") == 2
    assert PROVIDERS.route_count("moonshotai/kimi-k3") == 2
    for routes in PROVIDERS.PROVIDER_ROUTES.values():
        for route in routes:
            public = route.public_record()
            assert "key_env" not in public
            assert public["endpoint"].startswith("https://")
            assert public["pricing_observed_at"] == "2026-08-01"


def test_glm_payload_binds_high_reasoning_stream_and_strict_schema() -> None:
    route = PROVIDERS.route_for("z-ai/glm-5.2", 0)
    maximum, basis = PROVIDERS.available_completion_tokens(route, "system", "packet")
    payload = PROVIDERS.build_stream_payload(
        route,
        "system",
        "packet",
        {"type": "object", "additionalProperties": False},
        maximum,
    )

    assert maximum == 131_072
    assert basis == "provider_documented_maximum_output_tokens"
    assert payload["reasoning"] == {"effort": "high"}
    assert payload["stream"] is True
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["provider"]["data_collection"] == "deny"


def test_rate_card_fallback_and_provider_reported_cost_are_distinct() -> None:
    route = PROVIDERS.route_for("moonshotai/kimi-k3", 0)
    calculated = PROVIDERS.normalized_usage(
        route,
        {
            "prompt_tokens": 1_000_000,
            "completion_tokens": 100_000,
            "prompt_tokens_details": {"cached_tokens": 500_000},
        },
    )
    assert calculated["cost"] == 3.15
    assert calculated["cost_source"].startswith("calculated_from_Moonshot AI")

    reported = PROVIDERS.normalized_usage(
        route,
        {"prompt_tokens": 5, "completion_tokens": 7, "cost": 0.123},
    )
    assert reported["cost"] == 0.123
    assert reported["cost_source"] == "provider_reported_estimated_cost"


def test_route_and_context_fail_closed() -> None:
    with pytest.raises(PROVIDERS.ProviderStreamError):
        PROVIDERS.route_for("missing", 0)
    route = PROVIDERS.route_for("moonshotai/kimi-k3", 0)
    with pytest.raises(PROVIDERS.ProviderStreamError):
        PROVIDERS.available_completion_tokens(route, "x" * 2_100_000, "")

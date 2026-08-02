from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPTS = WORKSPACE / "scripts"
SCRIPT = SCRIPTS / "run_2607_17674_qwen_citation_audit.py"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("citation_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class StreamHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        assert self.path == "/v1/chat/completions"
        content_length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(content_length))
        assert request["stream"] is True
        events = [
            {
                "model": "qwen-test",
                "choices": [{"delta": {"reasoning_content": "checked"}}],
            },
            {
                "model": "qwen-test",
                "choices": [
                    {"delta": {"content": '{"ok":true}'}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        ]
        body = (
            b"".join(
                b"data: " + json.dumps(event).encode("utf-8") + b"\n\n"
                for event in events
            )
            + b"data: [DONE]\n\n"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def test_stream_completion_preserves_and_assembles_events(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = RUNNER.stream_completion(
            f"http://127.0.0.1:{server.server_port}",
            {"stream": True},
            tmp_path / "raw.sse",
            tmp_path / "events.jsonl",
            2,
            2,
            5,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
    assert result["content"] == '{"ok":true}'
    assert result["reasoning_content"] == "checked"
    assert result["event_count"] == 2
    assert result["usage"] == {"prompt_tokens": 10, "completion_tokens": 3}
    assert result["raw_response_sha256"] == RUNNER.sha256_file(tmp_path / "raw.sse")
    assert len((tmp_path / "events.jsonl").read_text().splitlines()) == 2


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8080",
        "http://example.com:8080",
        "http://127.0.0.1:8080/private",
    ],
)
def test_nonlocal_or_nonplain_routes_fail_closed(url: str) -> None:
    with pytest.raises(RUNNER.AuditError):
        RUNNER.safe_loopback_base_url(url)


def test_experiment_lock_fails_closed_on_contention(tmp_path: Path) -> None:
    lock_path = tmp_path / "nulspec-experiment.lock"
    first = RUNNER.acquire_experiment_lock(lock_path)
    try:
        with pytest.raises(
            RUNNER.AuditError,
            match="another NULSPEC experiment holds the host concurrency lock",
        ):
            RUNNER.acquire_experiment_lock(lock_path)
    finally:
        first.close()


def test_experiment_lock_is_reusable_after_release(tmp_path: Path) -> None:
    lock_path = tmp_path / "nulspec-experiment.lock"
    first = RUNNER.acquire_experiment_lock(lock_path)
    first.close()
    second = RUNNER.acquire_experiment_lock(lock_path)
    second.close()


def test_request_binds_schema_and_thinking_configuration() -> None:
    request, prompt = RUNNER.build_request(
        "qwen-test",
        "system",
        {"source": "evidence"},
        {"type": "object"},
        {
            "temperature": 0,
            "top_p": 1,
            "top_k": 0,
            "maximum_output_tokens": 128,
        },
        {"enable_thinking": True},
        None,
    )
    assert request["response_format"]["json_schema"]["schema"] == {"type": "object"}
    assert request["chat_template_kwargs"] == {"enable_thinking": True}
    assert '"evidence"' in prompt


def test_structure_only_transport_retains_shape_but_removes_bounds() -> None:
    canonical = {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 16,
                "items": {
                    "type": "object",
                    "required": ["excerpt", "page"],
                    "properties": {
                        "excerpt": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 800,
                        },
                        "page": {"type": "integer", "minimum": 1},
                    },
                },
            }
        },
    }
    generation = {
        "temperature": 0,
        "top_p": 1,
        "top_k": 0,
        "maximum_output_tokens": 8192,
        "response_format_mode": "structure_only_json_schema",
    }
    request, _ = RUNNER.build_request(
        "qwen-test",
        "system",
        {"source": "evidence"},
        canonical,
        generation,
        {"enable_thinking": True},
        None,
    )
    transported = request["response_format"]["json_schema"]["schema"]
    assert transported["type"] == "object"
    assert transported["required"] == ["items"]
    assert transported["properties"]["items"]["items"]["required"] == [
        "excerpt",
        "page",
    ]
    assert "maxItems" not in json.dumps(transported)
    assert "minLength" not in json.dumps(transported)
    assert "minimum" not in json.dumps(transported)
    assert canonical["properties"]["items"]["maxItems"] == 16


def test_unknown_response_format_mode_fails_closed() -> None:
    with pytest.raises(RUNNER.AuditError, match="unsupported response-format mode"):
        RUNNER.build_request(
            "qwen-test",
            "system",
            {"source": "evidence"},
            {"type": "object"},
            {
                "temperature": 0,
                "top_p": 1,
                "top_k": 0,
                "maximum_output_tokens": 128,
                "response_format_mode": "unregistered",
            },
            {"enable_thinking": True},
            None,
        )


def test_runtime_amendment_preserves_thinking_and_expands_budgets() -> None:
    config = json.loads(
        (
            WORKSPACE / "protocols/2607.17674/citation_audit_config.v1.0.2.json"
        ).read_text()
    )
    reviewer = config["primary_reviewer"]
    assert config["protocol_version"] == "1.0.2"
    assert reviewer["chat_template_kwargs"] == {"enable_thinking": True}
    assert reviewer["evidence_generation"] == {
        "temperature": 0,
        "top_p": 1,
        "top_k": 0,
        "maximum_output_tokens": 8192,
        "response_format_mode": "structure_only_json_schema",
    }
    assert reviewer["synthesis_generation"]["maximum_output_tokens"] == 12288
    assert (
        reviewer["synthesis_generation"]["response_format_mode"]
        == "structure_only_json_schema"
    )


def test_v103_page_labeled_presentation_preserves_exact_page_text() -> None:
    text = "first identi-\nfiability\fsecond page\n"
    packet = {
        "source_chunk": {
            "sha256": RUNNER.sha256_bytes(text.encode("utf-8")),
            "text": text,
            "page_spans": [
                {
                    "page_number": 7,
                    "chunk_character_start": 0,
                    "chunk_character_end": text.index("\f"),
                },
                {
                    "page_number": 8,
                    "chunk_character_start": text.index("\f") + 1,
                    "chunk_character_end": len(text),
                },
            ],
        }
    }
    original = json.loads(json.dumps(packet))
    presented = RUNNER.model_facing_evidence_packet(
        packet, {"mode": "page_labeled_exact_text_v1"}
    )
    assert packet == original
    assert "text" not in presented["source_chunk"]
    assert presented["source_chunk"]["extracted_pages"] == [
        {
            "page_number": 7,
            "text": "first identi-\nfiability",
            "text_sha256": RUNNER.sha256_bytes(b"first identi-\nfiability"),
        },
        {
            "page_number": 8,
            "text": "second page\n",
            "text_sha256": RUNNER.sha256_bytes(b"second page\n"),
        },
    ]
    presentation = presented["source_chunk"]["model_facing_presentation"]
    assert presentation["covered_characters"] == len(text) - 1
    assert presentation["omitted_form_feed_delimiters"] == 1


def test_v103_page_labeled_presentation_rejects_text_gaps() -> None:
    text = "page one\fpage two"
    packet = {
        "source_chunk": {
            "sha256": RUNNER.sha256_bytes(text.encode("utf-8")),
            "text": text,
            "page_spans": [
                {
                    "page_number": 1,
                    "chunk_character_start": 0,
                    "chunk_character_end": 4,
                }
            ],
        }
    }
    with pytest.raises(RUNNER.AuditError, match="omits non-delimiter text"):
        RUNNER.model_facing_evidence_packet(
            packet, {"mode": "page_labeled_exact_text_v1"}
        )


def test_v103_binds_prompt_and_preserves_generation_contract() -> None:
    config = json.loads(
        (
            WORKSPACE / "protocols/2607.17674/citation_audit_config.v1.0.3.json"
        ).read_text()
    )
    prompt, binding = RUNNER.effective_evidence_prompt(config)
    reviewer = config["primary_reviewer"]
    assert config["protocol_version"] == "1.0.3"
    assert binding["mode"] == "page_labeled_exact_text_v1"
    assert (
        binding["supplemental"]["sha256"]
        == reviewer["evidence_packet_presentation"]["supplemental_prompt_sha256"]
    )
    assert "never infer a page" in prompt
    assert "Do not silently dehyphenate" in prompt
    assert reviewer["evidence_generation"] == {
        "temperature": 0,
        "top_p": 1,
        "top_k": 0,
        "maximum_output_tokens": 8192,
        "response_format_mode": "structure_only_json_schema",
    }
    assert reviewer["synthesis_generation"]["maximum_output_tokens"] == 12288


@pytest.mark.parametrize(
    "schema_name",
    ["citation_evidence_chunk.schema.json", "citation_review.schema.json"],
)
def test_registered_transport_schemas_remove_only_quantitative_bounds(
    schema_name: str,
) -> None:
    canonical = json.loads(
        (WORKSPACE / "protocols/2607.17674" / schema_name).read_text()
    )
    transported = RUNNER.transport_schema(canonical, "structure_only_json_schema")
    transported_text = json.dumps(transported, sort_keys=True)
    assert transported["type"] == canonical["type"]
    assert transported["required"] == canonical["required"]
    for omitted in RUNNER.GRAMMAR_ONLY_OMITTED_SCHEMA_KEYS:
        assert f'"{omitted}"' not in transported_text
    assert any(
        f'"{omitted}"' in json.dumps(canonical, sort_keys=True)
        for omitted in RUNNER.GRAMMAR_ONLY_OMITTED_SCHEMA_KEYS
    )

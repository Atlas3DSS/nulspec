from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sys
import threading

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
                    {"delta": {"content": "{\"ok\":true}"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        ]
        body = b"".join(
            b"data: " + json.dumps(event).encode("utf-8") + b"\n\n"
            for event in events
        ) + b"data: [DONE]\n\n"
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
    assert request["response_format"]["json_schema"]["schema"] == {
        "type": "object"
    }
    assert request["chat_template_kwargs"] == {"enable_thinking": True}
    assert '"evidence"' in prompt

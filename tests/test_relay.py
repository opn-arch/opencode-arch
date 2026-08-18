"""Tests for the copilot-relay LLM client."""

from __future__ import annotations

import asyncio
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from opencode_arch.llm.relay import _chat_sync, is_relay_available, relay_llm_callback


def _make_sse_response(*events: dict) -> io.BytesIO:
    """Build a fake SSE response body."""
    lines = []
    for ev in events:
        lines.append(f"data: {json.dumps(ev)}\n".encode())
    return io.BytesIO(b"".join(lines))


class TestChatSync:
    def test_basic_chunks(self):
        resp = _make_sse_response(
            {"type": "chunk", "content": "Hello"},
            {"type": "chunk", "content": " World"},
            {"type": "done"},
        )
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            result = _chat_sync("test prompt")
        assert result == "Hello World"

    def test_done_stops_reading(self):
        resp = _make_sse_response(
            {"type": "chunk", "content": "A"},
            {"type": "done"},
            {"type": "chunk", "content": "B"},  # should not be read
        )
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            result = _chat_sync("test")
        assert result == "A"

    def test_malformed_json_skipped(self):
        body = (
            b"data: {bad json}\ndata: "
            + json.dumps({"type": "chunk", "content": "ok"}).encode()
            + b"\n"
        )
        resp = io.BytesIO(body)
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            result = _chat_sync("test")
        assert result == "ok"

    def test_non_data_lines_skipped(self):
        body = (
            b"event: ping\ndata: " + json.dumps({"type": "chunk", "content": "hi"}).encode() + b"\n"
        )
        resp = io.BytesIO(body)
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            result = _chat_sync("test")
        assert result == "hi"

    def test_network_error_returns_empty(self):
        from urllib.error import URLError

        with patch("opencode_arch.llm.relay.urlopen", side_effect=URLError("fail")):
            result = _chat_sync("test")
        assert result == ""

    def test_timeout_returns_empty(self):
        with patch("opencode_arch.llm.relay.urlopen", side_effect=TimeoutError()):
            result = _chat_sync("test")
        assert result == ""

    def test_system_prompt_included_in_body(self):
        resp = _make_sse_response({"type": "done"})
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp) as mock_open:
            _chat_sync("prompt", system_prompt="sys")
            req = mock_open.call_args[0][0]
            body = json.loads(req.data)
            assert body["system_prompt"] == "sys"
            assert body["content"] == "prompt"


class TestRelayCallback:
    def test_returns_stripped_result(self):
        resp = _make_sse_response(
            {"type": "chunk", "content": "  Component Manager  "},
            {"type": "done"},
        )
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            result = asyncio.run(relay_llm_callback("infer", "name this"))
        assert result == "Component Manager"

    def test_returns_none_on_empty(self):
        from urllib.error import URLError

        with patch("opencode_arch.llm.relay.urlopen", side_effect=URLError("fail")):
            result = asyncio.run(relay_llm_callback("infer", "name this"))
        assert result is None


class TestIsRelayAvailable:
    def test_healthy(self):
        resp = io.BytesIO(json.dumps({"status": "ok"}).encode())
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            assert is_relay_available() is True

    def test_unhealthy_status(self):
        resp = io.BytesIO(json.dumps({"status": "error"}).encode())
        resp.status = 200
        with patch("opencode_arch.llm.relay.urlopen", return_value=resp):
            assert is_relay_available() is False

    def test_connection_error(self):
        with patch("opencode_arch.llm.relay.urlopen", side_effect=ConnectionError()):
            assert is_relay_available() is False

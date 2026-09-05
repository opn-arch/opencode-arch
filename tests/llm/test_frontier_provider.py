"""Tests for FrontierProvider (Anthropic/OpenAI)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


def test_frontier_provider_selects_anthropic_when_only_anthropic_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    from opencode_arch.llm.providers.frontier import FrontierProvider
    p = FrontierProvider()
    assert p.backend == "anthropic"


def test_frontier_provider_raises_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from opencode_arch.llm.providers.frontier import FrontierProvider
    with pytest.raises(RuntimeError, match="no.*API key"):
        FrontierProvider()


def test_frontier_provider_complete_anthropic_end_to_end(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from opencode_arch.llm.providers.frontier import FrontierProvider

    fake_body = json.dumps({
        "content": [{"text": "hello world"}],
        "usage": {"input_tokens": 5, "output_tokens": 2},
        "stop_reason": "end_turn",
        "model": "claude-3-5-sonnet-latest",
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        p = FrontierProvider()
        c = p.complete("hi")

    assert set(c.keys()) == {"text", "tokens_prompt", "tokens_completion", "model", "finish_reason"}
    assert c["text"] == "hello world"
    assert c["tokens_prompt"] == 5
    assert c["tokens_completion"] == 2
    assert c["finish_reason"] == "stop"
    assert c["model"] == "claude-3-5-sonnet-latest"

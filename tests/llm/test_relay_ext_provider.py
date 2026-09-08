"""Tests for RelayExtProvider."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def test_relay_ext_provider_url_from_env(monkeypatch):
    monkeypatch.setenv("OPENCODE_RELAY_URL", "http://relay.local:8400")
    from opencode_arch.llm.providers.relay_ext import RelayExtProvider
    assert RelayExtProvider().base_url == "http://relay.local:8400"


def test_relay_ext_provider_completion_via_urlopen_mock(monkeypatch):
    # Plan test uses pytest-httpserver; we substitute urllib.request.urlopen
    # mock to avoid adding a new dev dep.
    monkeypatch.delenv("OPENCODE_RELAY_URL", raising=False)
    from opencode_arch.llm.providers.relay_ext import RelayExtProvider

    fake_body = json.dumps({
        "text": "ok",
        "tokens_prompt": 3,
        "tokens_completion": 1,
        "model": "relay",
        "finish_reason": "stop",
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        p = RelayExtProvider(base_url="http://stub")
        c = p.complete("hi")

    assert c["text"] == "ok"
    assert c["tokens_prompt"] == 3
    assert c["tokens_completion"] == 1
    assert c["model"] == "relay"
    assert c["finish_reason"] == "stop"

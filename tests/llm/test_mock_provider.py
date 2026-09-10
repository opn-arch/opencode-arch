"""Task 22 — MockProvider for write-back projector tests.

MockProvider matches prompts by SHA-256 hash and returns canned
responses. Any unregistered prompt raises ``KeyError`` — this makes
tests explicit about which prompts they intend to send.
"""
from __future__ import annotations

import pytest

from opencode_arch.llm.providers.mock import MockProvider


def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_name_is_mock():
    p = MockProvider(responses={})
    assert p.name == "mock"


def test_complete_returns_canned_response_by_prompt_hash():
    prompt = "hello world"
    responses = {
        _sha(prompt): {
            "text": "canned reply",
            "tokens_prompt": 2,
            "tokens_completion": 3,
            "model": "mock-v1",
            "finish_reason": "stop",
        }
    }
    p = MockProvider(responses=responses)
    out = p.complete(prompt)
    assert out["text"] == "canned reply"
    assert out["tokens_prompt"] == 2
    assert out["finish_reason"] == "stop"


def test_complete_raises_for_unregistered_prompt():
    p = MockProvider(responses={})
    with pytest.raises(KeyError):
        p.complete("unknown prompt")


def test_structured_returns_canned_dict():
    prompt = "author mission"
    key = _sha(prompt) + ":structured"
    responses = {key: {"authored": [{"entity_id": "CAP-1", "intent": "x"}]}}
    p = MockProvider(responses=responses)
    out = p.structured(prompt, schema={})
    assert out == {"authored": [{"entity_id": "CAP-1", "intent": "x"}]}


def test_structured_raises_for_unregistered_prompt():
    p = MockProvider(responses={})
    with pytest.raises(KeyError):
        p.structured("unknown", schema={})


def test_stream_yields_text_chunks():
    prompt = "stream me"
    key = _sha(prompt) + ":stream"
    responses = {key: ["chunk1 ", "chunk2"]}
    p = MockProvider(responses=responses)
    chunks = list(p.stream(prompt))
    assert chunks == ["chunk1 ", "chunk2"]


def test_tokenize_counts_whitespace_split():
    p = MockProvider(responses={})
    assert p.tokenize("one two three") == 3
    assert p.tokenize("") == 0

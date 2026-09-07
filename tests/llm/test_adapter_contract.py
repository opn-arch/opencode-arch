"""Recorded-fixture harness for LLMProvider adapter contracts (B1.2.1).

Each adapter, when fed the fixture prompt, must return a Completion
byte-identical to the fixture record (minus the "prompt" field, which is
input not output). Adapters land in B1.2.2 (mcp), B1.2.3 (frontier), and
B1.2.4 (relay-ext); until then, tests are skipped.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "completion_stop.json").read_text()
)


@pytest.mark.parametrize("adapter_name", ["mcp", "frontier", "relay-ext"])
@pytest.mark.skip(reason="adapters land in B1.2.2/3/4")
def test_adapter_returns_fixture(adapter_name: str) -> None:
    # Would import adapter by name, monkeypatch its transport to return
    # FIXTURE, feed FIXTURE["prompt"], and assert the returned Completion
    # equals FIXTURE minus the "prompt" key.
    raise NotImplementedError

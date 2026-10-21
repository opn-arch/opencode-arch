"""Tests for the arch_observe B-ROUND context-read MCP tool.

A pure-read tool returning raw, filtered observation records from the repo's
journal for live proprioception. Unlike arch_health/arch_flags, it does NOT
load the openAG model/graph — observations are model-independent.

NOTE: arch_observe is itself instrumented (wrapped in ``observe_tool_call``),
so each invocation appends its own ``oca:arch_observe`` ``tool_call`` record
to the journal. Tests therefore use membership/subset assertions rather than
exact counts so the self-entry never breaks an assertion.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from opencode_arch.mcp.tools.arch_observe import arch_observe


def _run(coro):
    return asyncio.run(coro)


def _seeded_records():
    return [
        {"component_id": "COMP-A", "io_kind": "tool_call", "direction": "in",  "name": "do",   "payload_digest": "", "ts": "2026-01-01T00:00:00+00:00"},
        {"component_id": "COMP-A", "io_kind": "llm_call",  "direction": "out", "name": "ask",  "payload_digest": "", "ts": "2026-02-01T00:00:00+00:00"},
        {"component_id": "COMP-B", "io_kind": "artifact",  "direction": "out", "name": "file", "payload_digest": "", "ts": "2026-03-01T00:00:00+00:00"},
    ]


@pytest.fixture
def seeded_repo(tmp_path):
    arch = tmp_path / ".architecture"
    arch.mkdir(parents=True)
    (arch / "observations.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in _seeded_records())
    )
    return tmp_path


def test_arch_observe_unfiltered_includes_all_seeded(seeded_repo):
    out = _run(arch_observe(repo_path=str(seeded_repo)))
    assert out["ok"] is True
    assert isinstance(out["observations"], list)
    for seeded in _seeded_records():
        assert seeded in out["observations"]


def test_arch_observe_filter_component_id(seeded_repo):
    out = _run(arch_observe(repo_path=str(seeded_repo), component_id="COMP-A"))
    assert out["ok"] is True
    for r in out["observations"]:
        assert r["component_id"] == "COMP-A"
    seeded = _seeded_records()
    assert seeded[0] in out["observations"]
    assert seeded[1] in out["observations"]


def test_arch_observe_filter_io_kind(seeded_repo):
    out = _run(arch_observe(repo_path=str(seeded_repo), io_kind="llm_call"))
    assert out["ok"] is True
    for r in out["observations"]:
        assert r["io_kind"] == "llm_call"
    assert _seeded_records()[1] in out["observations"]


def test_arch_observe_filter_since(seeded_repo):
    since = "2026-02-15T00:00:00+00:00"
    out = _run(arch_observe(repo_path=str(seeded_repo), since=since))
    assert out["ok"] is True
    for r in out["observations"]:
        assert r.get("ts", "") >= since
    seeded = _seeded_records()
    assert seeded[2] in out["observations"]
    assert seeded[0] not in out["observations"]


def test_arch_observe_combined_component_and_io_kind(seeded_repo):
    out = _run(
        arch_observe(repo_path=str(seeded_repo), component_id="COMP-A", io_kind="tool_call")
    )
    assert out["ok"] is True
    for r in out["observations"]:
        assert r["component_id"] == "COMP-A"
        assert r["io_kind"] == "tool_call"
    assert _seeded_records()[0] in out["observations"]


def test_arch_observe_missing_repo_returns_not_found():
    out = _run(arch_observe(repo_path="/nonexistent/repo/path"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_observe_no_journal_returns_empty_list(tmp_path):
    out = _run(arch_observe(repo_path=str(tmp_path)))
    assert out["ok"] is True
    assert isinstance(out["observations"], list)
    # No seeded data exists; the only record present is arch_observe's own
    # self-instrumentation tool_call entry.
    for r in out["observations"]:
        assert isinstance(r, dict)
        assert r.get("io_kind") == "tool_call"

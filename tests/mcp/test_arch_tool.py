"""Tests for the ``@arch_tool`` decorator (spans + mining telemetry + envelope)."""
from __future__ import annotations

import asyncio

from openag.mining.reservoir import load_records
from openag.observe.journal import read as read_journal

from opencode_arch.mcp._arch_tool import arch_tool


def _reservoir_path(repo):
    return str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")


def test_success_returns_envelope_and_emits_in_and_out_spans(tmp_path):
    (tmp_path / ".architecture").mkdir()

    @arch_tool
    async def my_handler(repo_path):
        return {"x": 1}

    result = asyncio.run(my_handler(str(tmp_path)))
    assert result == {"ok": True, "x": 1}

    records = read_journal(tmp_path)
    spans = [r for r in records if r.get("io_kind") == "tool_call"]
    directions = {r["direction"] for r in spans}
    assert "in" in directions
    assert "out" in directions
    assert all(r["component_id"] == "tool:my_handler" for r in spans)


def test_value_error_maps_to_invalid_argument_with_out_span_and_telemetry(tmp_path):
    (tmp_path / ".architecture").mkdir()

    @arch_tool
    async def bad_handler(repo_path):
        raise ValueError("bad")

    result = asyncio.run(bad_handler(str(tmp_path)))
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ARGUMENT"

    spans = [r for r in read_journal(tmp_path) if r.get("io_kind") == "tool_call"]
    assert any(r["direction"] == "out" for r in spans)

    records = load_records(_reservoir_path(tmp_path))
    assert len(records) == 1
    assert records[0]["outcome"] == "INVALID_ARGUMENT"


def test_success_appends_exactly_one_telemetry_record(tmp_path):
    (tmp_path / ".architecture").mkdir()

    @arch_tool
    async def ok_handler(repo_path):
        return {"y": 2}

    asyncio.run(ok_handler(str(tmp_path)))
    records = load_records(_reservoir_path(tmp_path))
    assert len(records) == 1
    assert records[0]["outcome"] == "ok"
    assert records[0]["tool"] == "ok_handler"


def test_repeated_calls_each_append_unique_telemetry_record(tmp_path):
    (tmp_path / ".architecture").mkdir()

    @arch_tool
    async def rep_handler(repo_path):
        return {"z": 3}

    asyncio.run(rep_handler(str(tmp_path)))
    asyncio.run(rep_handler(str(tmp_path)))
    records = load_records(_reservoir_path(tmp_path))
    assert len(records) == 2


def test_unresolvable_repo_yields_error_envelope_no_telemetry(tmp_path):
    missing = tmp_path / "does_not_exist"

    @arch_tool
    async def h(repo_path):
        from opencode_arch.mcp.envelope import resolve_repo

        resolve_repo(repo_path)
        return {"x": 1}

    result = asyncio.run(h(str(missing)))
    assert result["ok"] is False

    records = load_records(_reservoir_path(tmp_path))
    assert records == []

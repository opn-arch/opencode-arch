"""Tests for architect_component_health MCP tool."""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.component_health import component_health_tool
from opencode_arch.sil.store import SILStore


def _run(coro):
    return asyncio.run(coro)


def test_component_health_returns_record_and_trend(tmp_path):
    # Seed a SILStore at the conventional path.
    sil_dir = tmp_path / ".architecture"
    sil_dir.mkdir()
    db_path = sil_dir / "sil.sqlite"
    store = SILStore(db_path)
    store.emit("COMP-1", "invocation", "ok", 10)
    store.emit("COMP-1", "invocation", "error", 25, ref="ValueError")
    store.emit("COMP-1", "invocation", "ok", 15)

    result = _run(component_health_tool(repo_path=str(tmp_path), component_id="COMP-1"))

    assert result["ok"] is True
    record = result["record"]
    assert record["component_id"] == "COMP-1"
    assert record["kind"] == "runtime-component"
    assert "metrics" in record
    assert "recent_events" in record
    assert len(record["recent_events"]) == 3

    trend = result["trend"]
    assert trend["invocations_7d"] == 3
    assert 0.0 < trend["failure_rate_7d"] <= 1.0
    assert trend["avg_duration_ms"] > 0


def test_component_health_unknown_component_returns_not_found(tmp_path):
    sil_dir = tmp_path / ".architecture"
    sil_dir.mkdir()
    db_path = sil_dir / "sil.sqlite"
    SILStore(db_path)  # create empty DB

    result = _run(
        component_health_tool(repo_path=str(tmp_path), component_id="COMP-MISSING")
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "NOT_FOUND"


def test_component_health_missing_store_returns_not_found(tmp_path):
    result = _run(
        component_health_tool(repo_path=str(tmp_path), component_id="COMP-1")
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "NOT_FOUND"

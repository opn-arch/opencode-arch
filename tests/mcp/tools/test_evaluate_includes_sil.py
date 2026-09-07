"""B2.2.5 — architect_evaluate envelope includes sil_summary."""

from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.evaluate import evaluate_workspace
from opencode_arch.sil.store import SILStore


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def test_evaluate_envelope_includes_sil_summary(tmp_path):
    arch_dir = tmp_path / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    store = SILStore(arch_dir / "sil.sqlite")
    for _ in range(3):
        store.emit("stage:observe", "invocation", "ok", 12)
    store.emit("stage:observe", "invocation", "error", 20, ref="ValueError")
    store.emit("mcp_tool:pipeline", "invocation", "ok", 55)

    result = _run(evaluate_workspace(str(tmp_path), force_refresh=True))

    assert result.get("timestamp")  # envelope came back
    assert "sil_summary" in result
    summary = result["sil_summary"]
    assert isinstance(summary, dict)
    assert "stage:observe" in summary
    assert "mcp_tool:pipeline" in summary
    obs = summary["stage:observe"]
    assert obs["invocations_7d"] >= 4
    assert 0.0 <= obs["failure_rate_7d"] <= 1.0
    assert obs["avg_duration_ms"] > 0


def test_evaluate_without_sil_store_still_returns_ok(tmp_path):
    # No sil.sqlite present — evaluate should still return envelope with empty summary.
    result = _run(evaluate_workspace(str(tmp_path), force_refresh=True))
    assert result.get("timestamp")
    assert result.get("sil_summary") == {}

"""Behavioral-parity coverage for the ``arch_stats`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
aggregated telemetry, observation spans (in + out), mining telemetry (exactly
one self-record), self-telemetry-aware determinism, and the error taxonomy
(missing repo -> NOT_FOUND / INVALID_ARGUMENT). This is behavioral coverage,
NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import append_records, load_records

from opencode_arch.mcp.tools.arch_stats import arch_stats


def _telemetry_path(repo: Path) -> str:
    return str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")


def _seed_repo(root: Path) -> Path:
    (root / ".architecture" / "reservoir").mkdir(parents=True)
    return root


def _seed_scan(repo: Path) -> None:
    append_records(_telemetry_path(repo), [
        {"tool": "arch_scan", "outcome": "ok", "content_hash": "scan-ok"},
        {"tool": "arch_scan", "outcome": "error", "content_hash": "scan-err"},
    ])


def test_parity_stats_decorator_contract():
    assert getattr(arch_stats, "__wrapped__", None) is not None


def test_parity_stats_happy_path(tmp_path):
    repo = _seed_repo(tmp_path / "happy")
    _seed_scan(repo)

    out = asyncio.run(arch_stats(repo_path=str(repo)))
    assert out["ok"] is True
    scan = [t for t in out["tools"] if t["tool"] == "arch_scan"]
    assert scan and scan[0]["calls"] == 2
    assert scan[0]["ok"] == 1
    assert scan[0]["error"] == 1
    assert "total_calls" in out
    assert "model" in out

    # Spans: one "in" and one "out" tool_call for tool:arch_stats.
    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_stats"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_stats"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_stats self-record, outcome ok.
    telemetry = load_records(_telemetry_path(repo))
    drecords = [r for r in telemetry if r.get("tool") == "arch_stats"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_stats_determinism(tmp_path):
    repo = _seed_repo(tmp_path / "det")
    _seed_scan(repo)

    # The @arch_tool decorator appends an arch_stats self-telemetry record on
    # EVERY call, so two unfiltered aggregates would differ (the 2nd sees the
    # 1st's record). Filtering on a pre-seeded tool ("arch_scan") excludes
    # arch_stats's own self-telemetry, so the filtered aggregate is byte-stable.
    first = asyncio.run(arch_stats(repo_path=str(repo), tool_filter="arch_scan"))
    second = asyncio.run(arch_stats(repo_path=str(repo), tool_filter="arch_scan"))
    assert first == second


def test_parity_stats_error_taxonomy(tmp_path):
    bad = asyncio.run(arch_stats(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

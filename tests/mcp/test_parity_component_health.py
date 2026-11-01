"""Behavioral-parity coverage for the ``arch_health`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope (graph-wide and
node-scoped), observation spans (in + out), mining telemetry (exactly one
``ok`` record), and the error taxonomy (``ValueError`` ->
``INVALID_ARGUMENT``). This is behavioral coverage, NOT legacy output-shape
equivalence.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_health import arch_health

_EXEMPLAR_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    model_dir.mkdir(parents=True)
    for frag in sorted(_EXEMPLAR_DIR.glob("*.v3.yaml")):
        shutil.copy(frag, model_dir / frag.name)
    return root


def test_parity_component_health(tmp_path):
    # Three separate fresh repos so telemetry/span counts are unambiguous.
    repoA = _seed_repo(tmp_path / "graph")
    repoB = _seed_repo(tmp_path / "node")
    repoC = _seed_repo(tmp_path / "bad")

    # --- repo A: graph-wide health --------------------------------------
    out = asyncio.run(arch_health(repo_path=str(repoA)))
    assert out["ok"] is True

    # Spans: one "in" and one "out" tool_call for tool:arch_health.
    records = read_journal(repoA)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_health"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_health"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_health record, outcome ok.
    telemetry = load_records(
        str(repoA / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    health_records = [r for r in telemetry if r.get("tool") == "arch_health"]
    assert len(health_records) == 1, f"expected 1 telemetry record, got {health_records!r}"
    assert health_records[0]["outcome"] == "ok"

    # --- repo B: node-scoped health -------------------------------------
    outB = asyncio.run(arch_health(repo_path=str(repoB), node_id="CAP-DOSE"))
    assert outB["ok"] is True
    assert isinstance(outB, dict)

    # --- repo C: bad arg (empty node_id) -> INVALID_ARGUMENT -------------
    bad = asyncio.run(arch_health(repo_path=str(repoC), node_id=""))
    assert bad["ok"] is False
    assert bad["error"]["code"] == "INVALID_ARGUMENT"

"""Behavioral-parity coverage for the ``arch_export`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the graph
export manifest, observation spans (in + out), mining telemetry (exactly one
record), determinism (byte-identical graphml file across two runs), and the
error taxonomy (missing repo -> NOT_FOUND / INVALID_ARGUMENT). This is
behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_export import arch_export

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    return root


def test_parity_export_graph(tmp_path):
    repo = _seed_repo(tmp_path / "happy")
    out_dir = tmp_path / "out"

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_export, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_export(repo_path=str(repo), output_dir=str(out_dir)))
    assert out["ok"] is True
    assert out["format"] == "graphml"
    assert out["path"].endswith("model.graphml")
    assert Path(out["path"]).exists()
    assert out["node_count"] > 0

    # Spans: one "in" and one "out" tool_call for tool:arch_export.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_export"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_export"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_export record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_export"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_export_determinism(tmp_path):
    repo = _seed_repo(tmp_path / "determ")
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(arch_export(repo_path=str(repo), output_dir=str(out_a)))
        second = asyncio.run(arch_export(repo_path=str(repo), output_dir=str(out_b)))
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    b1 = Path(first["path"]).read_bytes()
    b2 = Path(second["path"]).read_bytes()
    assert b1 == b2


def test_parity_export_error_taxonomy(tmp_path):
    bad = asyncio.run(arch_export(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

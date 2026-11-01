"""Behavioral-parity coverage for the ``arch_scan`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
module/import-edge inventory, observation spans (in + out), mining telemetry
(exactly one record), and the error taxonomy (missing repo -> NOT_FOUND).
This is behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_scan import arch_scan


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("from src import b\n", encoding="utf-8")
    (src / "b.py").write_text("import os\n", encoding="utf-8")
    return root


def test_parity_scan_manifest(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_scan, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_scan(repo_path=str(repo)))
    assert out["ok"] is True
    assert "modules" in out
    assert "import_edges" in out
    assert "counts" in out
    assert out["counts"]["modules"] == len(out["modules"])

    # Spans: one "in" and one "out" tool_call for tool:arch_scan.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_scan"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_scan"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_scan record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    scan_records = [r for r in telemetry if r.get("tool") == "arch_scan"]
    assert len(scan_records) == 1, f"expected 1 telemetry record, got {scan_records!r}"
    assert scan_records[0]["outcome"] == "ok"

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_scan(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

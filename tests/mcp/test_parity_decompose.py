"""Behavioral-parity coverage for the ``arch_decompose`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
System-decomposition projection, observation spans (in + out), mining telemetry
(exactly one record), and the error taxonomy (missing repo -> NOT_FOUND).
This is behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_decompose import arch_decompose

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("import os\n")
    (src / "b.py").write_text("import sys\n")
    return root


def test_parity_decompose_subsystems(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_decompose, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_decompose(repo_path=str(repo)))
    assert out["ok"] is True
    assert isinstance(out["systems"], list)
    assert isinstance(out["candidates"], list)
    assert isinstance(out["total_systems"], int)
    assert out["total_systems"] == len(out["systems"])
    assert out["total_systems"] >= 1
    for sys_entry in out["systems"]:
        assert isinstance(sys_entry["id"], str)
        assert isinstance(sys_entry["name"], str)
        assert isinstance(sys_entry["children"], list)
        assert isinstance(sys_entry["child_count"], int)

    # Spans: one "in" and one "out" tool_call for tool:arch_decompose.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_decompose"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_decompose"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_decompose record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_decompose"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_decompose(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

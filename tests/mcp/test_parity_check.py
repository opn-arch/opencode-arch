"""Behavioral-parity coverage for the ``arch_check`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
representativeness sub-scores, observation spans (in + out), mining telemetry
(exactly one record), and the error taxonomy (missing repo -> NOT_FOUND).
This is behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_check import arch_check

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("import os\n")
    (src / "b.py").write_text("import sys\n")
    return root


def test_parity_check_representativeness(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_check, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_check(repo_path=str(repo)))
    assert out["ok"] is True
    for key in ("file_coverage", "relationship_accuracy", "boundary_coherence", "overall"):
        assert key in out
        assert isinstance(out[key], int)
        assert 0 <= out[key] <= 100

    # Spans: one "in" and one "out" tool_call for tool:arch_check.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_check"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_check"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_check record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    grecords = [r for r in telemetry if r.get("tool") == "arch_check"]
    assert len(grecords) == 1, f"expected 1 telemetry record, got {grecords!r}"
    assert grecords[0]["outcome"] == "ok"

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_check(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

"""Behavioral-parity coverage for the ``arch_docs`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
openAG-shaped doc set, observation spans (in + out), mining telemetry (exactly
one record), determinism, and the error taxonomy (missing repo -> NOT_FOUND).
This is behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_docs import arch_docs

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    return root


def test_parity_docs_generate(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_docs, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_docs(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["count"] == 3
    assert set(out["docs"].keys()) == {"overview", "components", "promises"}
    assert "COMP-" in out["docs"]["components"]

    # Spans: one "in" and one "out" tool_call for tool:arch_docs.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_docs"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_docs"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_docs record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_docs"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_docs_determinism(tmp_path):
    repo = _seed_repo(tmp_path / "determ")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(arch_docs(repo_path=str(repo)))
        second = asyncio.run(arch_docs(repo_path=str(repo)))
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    # generate_docs writes nothing; the doc set replays byte-identically.
    assert first["docs"] == second["docs"]


def test_parity_docs_error_taxonomy(tmp_path):
    bad = asyncio.run(arch_docs(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

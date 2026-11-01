"""Behavioral-parity coverage for the ``arch_require`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
requirement-capture summary, observation spans (in + out), mining telemetry
(exactly one record), determinism (byte-identical ledger across two fresh
repos), and the error taxonomy. This is behavioral coverage, NOT legacy AMS
output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_require import arch_require

_REQ = "The system shall log all calls"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    return root


def test_parity_require_capture(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_require, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_require(
            repo_path=str(repo),
            requirement=_REQ,
            component_id="COMP-1",
            priority="should",
            context="from discussion",
        )
    )
    assert out["ok"] is True
    assert out["requirement_id"] == "REQ-1"
    assert out["component"] == "COMP-1"
    assert out["total_requirements"] == 1
    assert (repo / ".architecture" / "requirements.yaml").exists()

    # Spans: one "in" and one "out" tool_call for tool:arch_require.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_require"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_require"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_require record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_require"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_require_determinism(tmp_path):
    repo_a = _seed_repo(tmp_path / "a")
    repo_b = _seed_repo(tmp_path / "b")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(
            arch_require(repo_path=str(repo_a), requirement=_REQ, component_id="COMP-1")
        )
        second = asyncio.run(
            arch_require(repo_path=str(repo_b), requirement=_REQ, component_id="COMP-1")
        )
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    b1 = (repo_a / ".architecture" / "requirements.yaml").read_bytes()
    b2 = (repo_b / ".architecture" / "requirements.yaml").read_bytes()
    assert b1 == b2


def test_parity_require_error_taxonomy(tmp_path):
    # (a) missing repo
    bad = asyncio.run(
        arch_require(repo_path=str(tmp_path / "does-not-exist"), requirement="x")
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    # (b) valid repo but invalid priority
    repo = _seed_repo(tmp_path / "valid")
    bad2 = asyncio.run(
        arch_require(repo_path=str(repo), requirement="x", priority="bogus")
    )
    assert bad2["ok"] is False
    assert bad2["error"]["code"] == "INVALID_ARGUMENT"

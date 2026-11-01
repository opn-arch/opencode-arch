"""Behavioral-parity coverage for the ``arch_correct`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
correction-store summary, observation spans (in + out), mining telemetry
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

from opencode_arch.mcp.tools.arch_correct import arch_correct


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    return root


def test_parity_correct_store(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_correct, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_correct(
            repo_path=str(repo),
            correction_type="rename",
            target="COMP-1",
            reason="clarity",
            suggestion={"new_name": "Core"},
        )
    )
    assert out["ok"] is True
    assert out["correction_id"] == "COR-1"
    assert out["total_corrections"] == 1
    assert (repo / ".architecture" / "corrections.yaml").exists()

    # Spans: one "in" and one "out" tool_call for tool:arch_correct.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_correct"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_correct"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_correct record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_correct"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_correct_determinism(tmp_path):
    repo_a = _seed_repo(tmp_path / "a")
    repo_b = _seed_repo(tmp_path / "b")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(
            arch_correct(
                repo_path=str(repo_a),
                correction_type="rename",
                target="COMP-1",
                reason="clarity",
            )
        )
        second = asyncio.run(
            arch_correct(
                repo_path=str(repo_b),
                correction_type="rename",
                target="COMP-1",
                reason="clarity",
            )
        )
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    b1 = (repo_a / ".architecture" / "corrections.yaml").read_bytes()
    b2 = (repo_b / ".architecture" / "corrections.yaml").read_bytes()
    assert b1 == b2


def test_parity_correct_error_taxonomy(tmp_path):
    # (a) missing repo
    bad = asyncio.run(
        arch_correct(
            repo_path=str(tmp_path / "does-not-exist"),
            correction_type="rename",
            target="COMP-1",
            reason="x",
        )
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    # (b) valid repo but invalid correction_type
    repo = _seed_repo(tmp_path / "valid")
    bad2 = asyncio.run(
        arch_correct(
            repo_path=str(repo),
            correction_type="bogus",
            target="COMP-1",
            reason="x",
        )
    )
    assert bad2["ok"] is False
    assert bad2["error"]["code"] == "INVALID_ARGUMENT"

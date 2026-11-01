"""Behavioral-parity coverage for the ``arch_feedback`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
feedback-ledger summary, observation spans (in + out), mining telemetry
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

from opencode_arch.mcp.tools.arch_feedback import arch_feedback


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    return root


def test_parity_feedback_record(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_feedback, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_feedback(
            repo_path=str(repo),
            feedback_type="rating",
            content="great tool",
            rating=5,
        )
    )
    assert out["ok"] is True
    assert out["feedback_id"] == "FB-1"
    assert out["total_feedback"] == 1
    assert (repo / ".architecture" / "feedback.jsonl").exists()

    # Spans: one "in" and one "out" tool_call for tool:arch_feedback.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_feedback"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_feedback"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_feedback record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_feedback"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_feedback_determinism(tmp_path):
    repo_a = _seed_repo(tmp_path / "a")
    repo_b = _seed_repo(tmp_path / "b")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(
            arch_feedback(
                repo_path=str(repo_a),
                feedback_type="rating",
                content="same",
                rating=5,
            )
        )
        second = asyncio.run(
            arch_feedback(
                repo_path=str(repo_b),
                feedback_type="rating",
                content="same",
                rating=5,
            )
        )
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    b1 = (repo_a / ".architecture" / "feedback.jsonl").read_bytes()
    b2 = (repo_b / ".architecture" / "feedback.jsonl").read_bytes()
    assert b1 == b2


def test_parity_feedback_error_taxonomy(tmp_path):
    # (a) missing repo
    bad = asyncio.run(
        arch_feedback(
            repo_path=str(tmp_path / "does-not-exist"),
            feedback_type="rating",
            content="x",
        )
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    # (b) valid repo but invalid feedback_type
    repo = _seed_repo(tmp_path / "valid")
    bad2 = asyncio.run(
        arch_feedback(
            repo_path=str(repo),
            feedback_type="bogus",
            content="x",
        )
    )
    assert bad2["ok"] is False
    assert bad2["error"]["code"] == "INVALID_ARGUMENT"

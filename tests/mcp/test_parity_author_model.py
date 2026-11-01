"""Behavioral-parity coverage for the ``arch_author`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the authored
generation summary, observation spans (in + out), mining telemetry (exactly one
record), determinism (byte-identical recorded generation across two fresh repos),
and the error taxonomy (missing repo -> NOT_FOUND / INVALID_ARGUMENT). This is
behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_author import arch_author

_REQS = "First requirement\nSecond requirement\nThird requirement"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    return root


def test_parity_author_model(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_author, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_author(repo_path=str(repo), requirements_text=_REQS))
    assert out["ok"] is True
    assert out["gen_id"] == "0000001"
    assert out["capabilities"] == 3
    assert out["lifecycle_phase"] == "concept"
    assert (repo / ".architecture" / "generations" / "0000001.json").exists()

    # Spans: one "in" and one "out" tool_call for tool:arch_author.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_author"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_author"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_author record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_author"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_author_determinism(tmp_path):
    repo_a = _seed_repo(tmp_path / "a")
    repo_b = _seed_repo(tmp_path / "b")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(arch_author(repo_path=str(repo_a), requirements_text=_REQS))
        second = asyncio.run(arch_author(repo_path=str(repo_b), requirements_text=_REQS))
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    b1 = (repo_a / ".architecture" / "generations" / "0000001.json").read_bytes()
    b2 = (repo_b / ".architecture" / "generations" / "0000001.json").read_bytes()
    assert b1 == b2


def test_parity_author_error_taxonomy(tmp_path):
    bad = asyncio.run(arch_author(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

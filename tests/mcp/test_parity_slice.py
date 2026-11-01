"""Behavioral-parity coverage for the ``arch_slice`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope, observation
spans (in + out), mining telemetry (exactly one ``ok`` record), and the
error taxonomy (``ValueError`` -> ``INVALID_ARGUMENT``). This is behavioral
coverage, NOT legacy output-shape equivalence.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_context import arch_slice

_EXEMPLAR_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    model_dir.mkdir(parents=True)
    for frag in sorted(_EXEMPLAR_DIR.glob("*.v3.yaml")):
        shutil.copy(frag, model_dir / frag.name)
    return root


def test_parity_slice_equivalence(tmp_path):
    # Two separate fresh repos so telemetry/span counts are unambiguous.
    repo = _seed_repo(tmp_path / "happy")
    repo2 = _seed_repo(tmp_path / "bad")

    # --- Happy path: slice CAP-DOSE --------------------------------------
    out = asyncio.run(arch_slice(repo_path=str(repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert "slice" in out

    # Spans: one "in" and one "out" tool_call for tool:arch_slice.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_slice"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_slice"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_slice record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    slice_records = [r for r in telemetry if r.get("tool") == "arch_slice"]
    assert len(slice_records) == 1, f"expected 1 telemetry record, got {slice_records!r}"
    assert slice_records[0]["outcome"] == "ok"

    # --- Bad arg: empty node_id -> INVALID_ARGUMENT ----------------------
    bad = asyncio.run(arch_slice(repo_path=str(repo2), node_id=""))
    assert bad["ok"] is False
    assert bad["error"]["code"] == "INVALID_ARGUMENT"

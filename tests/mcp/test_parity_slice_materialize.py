"""Behavioral-parity coverage for the ``arch_slice_materialize`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
materialized slice, observation spans (in + out), mining telemetry (exactly
one record), determinism (pure read), and the error taxonomy. Behavioral
coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_slice_materialize import (
    arch_slice_materialize,
)

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"
_REAL_ID = "SYS-INSULIN-PUMP"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_slice_materialize(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_slice_materialize, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_slice_materialize(repo_path=str(repo), entity_id=_REAL_ID)
    )
    assert out["ok"] is True
    assert out["slice_id"] == _REAL_ID
    assert out["in_scope_count"] >= 1
    assert isinstance(out["nodes"], list)

    # Spans: one "in" and one "out" tool_call.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_slice_materialize"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_slice_materialize"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_slice_materialize"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_slice_materialize_deterministic(tmp_path):
    repo = _seed_repo(tmp_path / "det")
    out_a = asyncio.run(
        arch_slice_materialize(repo_path=str(repo), entity_id=_REAL_ID)
    )
    out_b = asyncio.run(
        arch_slice_materialize(repo_path=str(repo), entity_id=_REAL_ID)
    )
    for field in ("slice_id", "in_scope_count", "nodes", "rollup"):
        assert out_a[field] == out_b[field]


def test_parity_slice_materialize_errors(tmp_path):
    # missing repo
    out = asyncio.run(
        arch_slice_materialize(
            repo_path=str(tmp_path / "nonexistent"), entity_id=_REAL_ID
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    # unknown entity on a valid repo
    repo = _seed_repo(tmp_path / "unknown")
    out2 = asyncio.run(
        arch_slice_materialize(repo_path=str(repo), entity_id="NOPE-999")
    )
    assert out2["ok"] is False
    assert out2["error"]["code"] == "INVALID_ARGUMENT"

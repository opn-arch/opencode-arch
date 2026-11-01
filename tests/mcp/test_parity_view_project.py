"""Behavioral-parity coverage for the ``arch_view_project`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
projected viewer payload, observation spans (in + out), mining telemetry
(exactly one record), determinism (pure read), and the error taxonomy.
Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_view_project import arch_view_project

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"
_REAL_ID = "SYS-INSULIN-PUMP"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_view_project(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    assert getattr(arch_view_project, "__wrapped__", None) is not None

    out = asyncio.run(arch_view_project(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["view_id"] == "full"
    assert isinstance(out["nodes"], list) and out["nodes"]
    assert out["node_count"] == len(out["nodes"])

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_view_project"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_view_project"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_view_project"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_view_project_scoped_and_deterministic(tmp_path):
    repo = _seed_repo(tmp_path / "det")
    a = asyncio.run(arch_view_project(repo_path=str(repo), entity_id=_REAL_ID))
    b = asyncio.run(arch_view_project(repo_path=str(repo), entity_id=_REAL_ID))
    assert a["ok"] is True
    assert a["view_id"] == _REAL_ID
    assert a["scope"]["id"] == _REAL_ID
    for field in ("view_id", "nodes", "edges", "node_count", "edge_count"):
        assert a[field] == b[field]


def test_parity_view_project_errors(tmp_path):
    out = asyncio.run(
        arch_view_project(repo_path=str(tmp_path / "nonexistent"))
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    repo = _seed_repo(tmp_path / "unknown")
    out2 = asyncio.run(
        arch_view_project(repo_path=str(repo), entity_id="NOPE-999")
    )
    assert out2["ok"] is False
    assert out2["error"]["code"] == "INVALID_ARGUMENT"

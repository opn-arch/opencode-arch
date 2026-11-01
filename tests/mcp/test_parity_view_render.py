"""Behavioral-parity coverage for the ``arch_view_render`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
rendered viewer HTML, observation spans (in + out), mining telemetry (exactly
one record), determinism (pure read), and the error taxonomy. Behavioral
coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_view_render import arch_view_render

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_view_render(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    assert getattr(arch_view_render, "__wrapped__", None) is not None

    out = asyncio.run(arch_view_render(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["artifact_id"] == "viewer-html"
    assert out["content_type"] == "text/html"
    assert out["body_utf8"].lstrip().lower().startswith("<!doctype")
    assert isinstance(out["digest"], str) and len(out["digest"]) == 64

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_view_render"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_view_render"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_view_render"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_view_render_deterministic(tmp_path):
    repo = _seed_repo(tmp_path / "det")
    a = asyncio.run(arch_view_render(repo_path=str(repo)))
    b = asyncio.run(arch_view_render(repo_path=str(repo)))
    assert a["digest"] == b["digest"]
    assert a["body_utf8"] == b["body_utf8"]


def test_parity_view_render_errors(tmp_path):
    out = asyncio.run(arch_view_render(repo_path=str(tmp_path / "nonexistent")))
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

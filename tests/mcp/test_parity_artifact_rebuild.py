"""Behavioral-parity coverage for the ``arch_artifact_rebuild`` tool.

Asserts the full ``@arch_tool`` contract: success envelope (built artifacts +
generation anchor), observation spans, mining telemetry, and the error
taxonomy. Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_artifact_rebuild import arch_artifact_rebuild

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_EXEMPLAR, repo / ".architecture" / "model")


def test_parity_artifact_rebuild(tmp_path):
    repo = tmp_path / "happy"
    _seed(repo)

    assert getattr(arch_artifact_rebuild, "__wrapped__", None) is not None

    out = asyncio.run(
        arch_artifact_rebuild(
            repo_path=str(repo),
            artifact_specs=[
                {"id": "viewer", "renderer": "html"},
                {"id": "ov", "renderer": "overview", "depends_on": ["viewer"]},
            ],
        )
    )
    assert out["ok"] is True
    assert out["order"] == ["viewer", "ov"]
    assert sorted(b["spec_id"] for b in out["built"]) == ["ov", "viewer"]
    assert out["failed"] == []
    assert (repo / ".architecture" / "artifacts" / "viewer.html").exists()
    assert (repo / ".architecture" / "artifacts" / "ov.md").exists()

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_artifact_rebuild"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_artifact_rebuild"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_artifact_rebuild"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_artifact_rebuild_idempotent_skip(tmp_path):
    repo = tmp_path / "skip"
    _seed(repo)
    specs = [{"id": "ov", "renderer": "overview"}]
    asyncio.run(arch_artifact_rebuild(repo_path=str(repo), artifact_specs=specs))
    out2 = asyncio.run(arch_artifact_rebuild(repo_path=str(repo), artifact_specs=specs))
    assert out2["ok"] is True
    assert out2["built"] == []
    assert [s["spec_id"] for s in out2["skipped"]] == ["ov"]


def test_parity_artifact_rebuild_unknown_renderer(tmp_path):
    repo = tmp_path / "badrenderer"
    _seed(repo)
    out = asyncio.run(
        arch_artifact_rebuild(
            repo_path=str(repo),
            artifact_specs=[{"id": "x", "renderer": "nope"}],
        )
    )
    assert out["ok"] is True
    assert out["built"] == []
    assert len(out["failed"]) == 1
    assert out["failed"][0]["spec_id"] == "x"


def test_parity_artifact_rebuild_cycle(tmp_path):
    repo = tmp_path / "cycle"
    _seed(repo)
    out = asyncio.run(
        arch_artifact_rebuild(
            repo_path=str(repo),
            artifact_specs=[
                {"id": "a", "renderer": "overview", "depends_on": ["b"]},
                {"id": "b", "renderer": "overview", "depends_on": ["a"]},
            ],
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"


def test_parity_artifact_rebuild_badarg(tmp_path):
    repo = tmp_path / "badarg"
    _seed(repo)
    out = asyncio.run(arch_artifact_rebuild(repo_path=str(repo), artifact_specs=[]))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_artifact_rebuild_repo_missing(tmp_path):
    out = asyncio.run(
        arch_artifact_rebuild(
            repo_path=str(tmp_path / "nope"),
            artifact_specs=[{"id": "a", "renderer": "overview"}],
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

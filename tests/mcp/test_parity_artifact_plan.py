"""Behavioral-parity coverage for the ``arch_artifact_plan`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
deterministic topological plan, observation spans (in + out), mining telemetry
(exactly one record), determinism (pure read), and the error taxonomy.
Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_artifact_plan import arch_artifact_plan


def test_parity_artifact_plan(tmp_path):
    repo = tmp_path / "happy"
    repo.mkdir()

    assert getattr(arch_artifact_plan, "__wrapped__", None) is not None

    out = asyncio.run(
        arch_artifact_plan(
            repo_path=str(repo),
            artifact_specs=[
                {"id": "a"},
                {"id": "b", "depends_on": ["a"]},
                {"id": "c", "depends_on": ["b"]},
            ],
        )
    )
    assert out["ok"] is True
    assert out["plan"]["order"] == ["a", "b", "c"]
    node_b = next(n for n in out["plan"]["nodes"] if n["spec_id"] == "b")
    assert node_b["depends_on"] == ["a"]

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_artifact_plan"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_artifact_plan"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_artifact_plan"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_artifact_plan_deterministic(tmp_path):
    repo = tmp_path / "det"
    repo.mkdir()
    specs = [{"id": "z"}, {"id": "a"}]
    a = asyncio.run(arch_artifact_plan(repo_path=str(repo), artifact_specs=specs))
    b = asyncio.run(arch_artifact_plan(repo_path=str(repo), artifact_specs=specs))
    assert a["plan"] == b["plan"]
    assert a["plan"]["order"] == ["a", "z"]


def test_parity_artifact_plan_cycle(tmp_path):
    repo = tmp_path / "cycle"
    repo.mkdir()
    out = asyncio.run(
        arch_artifact_plan(
            repo_path=str(repo),
            artifact_specs=[
                {"id": "a", "depends_on": ["b"]},
                {"id": "b", "depends_on": ["a"]},
            ],
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"


def test_parity_artifact_plan_unknown_ref(tmp_path):
    repo = tmp_path / "unknown"
    repo.mkdir()
    out = asyncio.run(
        arch_artifact_plan(
            repo_path=str(repo),
            artifact_specs=[{"id": "a", "depends_on": ["x"]}],
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"


def test_parity_artifact_plan_badarg(tmp_path):
    repo = tmp_path / "badarg"
    repo.mkdir()
    out = asyncio.run(arch_artifact_plan(repo_path=str(repo), artifact_specs=[]))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"

    out2 = asyncio.run(
        arch_artifact_plan(
            repo_path=str(repo),
            artifact_specs=[{"id": "a"}, {"id": "a"}],
        )
    )
    assert out2["ok"] is False
    assert out2["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_artifact_plan_repo_missing(tmp_path):
    out = asyncio.run(
        arch_artifact_plan(
            repo_path=str(tmp_path / "nope"),
            artifact_specs=[{"id": "a"}],
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

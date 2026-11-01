"""Behavioral-parity coverage for the ``arch_package_publish`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
publish summary, observation spans (in + out), mining telemetry (exactly one
record), determinism (byte-identical generation file across two fresh repos),
and the error taxonomy. Behavioral coverage, NOT legacy AMS output-shape
equivalence.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_package_publish import (
    arch_package_publish,
)

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_package_publish(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_package_publish, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_package_publish(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["published"] is True
    assert out["gen_id"] == "0000001"

    # Spans: one "in" and one "out" tool_call for tool:arch_package_publish.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_package_publish"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_package_publish"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_package_publish record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_package_publish"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_package_publish_determinism(tmp_path):
    repo_a = _seed_repo(tmp_path / "a")
    repo_b = _seed_repo(tmp_path / "b")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = "2026-10-31T00:00:00Z"
    try:
        first = asyncio.run(arch_package_publish(repo_path=str(repo_a)))
        second = asyncio.run(arch_package_publish(repo_path=str(repo_b)))
    finally:
        del os.environ["OPENAG_DETERMINISTIC_NOW"]
    assert first["ok"] is True
    assert second["ok"] is True
    b1 = (repo_a / ".architecture" / "generations" / "0000001.json").read_bytes()
    b2 = (repo_b / ".architecture" / "generations" / "0000001.json").read_bytes()
    assert b1 == b2


def test_parity_package_publish_error_taxonomy(tmp_path):
    # (a) missing repo
    bad = asyncio.run(
        arch_package_publish(repo_path=str(tmp_path / "nonexistent"))
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    # (b) repo exists but has no openAG model dir
    empty = tmp_path / "empty"
    (empty / ".architecture").mkdir(parents=True)
    bad2 = asyncio.run(arch_package_publish(repo_path=str(empty)))
    assert bad2["ok"] is False
    assert bad2["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

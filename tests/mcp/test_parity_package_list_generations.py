"""Behavioral-parity coverage for the ``arch_package_list_generations`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
generation summaries, observation spans (in + out), mining telemetry (exactly
one record), the empty-store success case, and the error taxonomy. Behavioral
coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_package_publish import (
    arch_package_publish,
)
from opencode_arch.mcp.tools.lifecycle.arch_package_list_generations import (
    arch_package_list_generations,
)

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_package_list_generations(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_package_list_generations, "__wrapped__", None) is not None

    # Publish two generations so there is something to list.
    assert asyncio.run(arch_package_publish(repo_path=str(repo)))["ok"] is True
    assert asyncio.run(arch_package_publish(repo_path=str(repo)))["ok"] is True

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_package_list_generations(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["count"] == 2
    assert out["generations"][0]["gen_id"] == "0000001"

    # Spans: one "in" and one "out" tool_call.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_package_list_generations"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_package_list_generations"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [
        r for r in telemetry if r.get("tool") == "arch_package_list_generations"
    ]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_package_list_generations_empty(tmp_path):
    repo = _seed_repo(tmp_path / "empty")
    out = asyncio.run(arch_package_list_generations(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["count"] == 0
    assert out["generations"] == []


def test_parity_package_list_generations_error_taxonomy(tmp_path):
    bad = asyncio.run(
        arch_package_list_generations(repo_path=str(tmp_path / "nonexistent"))
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

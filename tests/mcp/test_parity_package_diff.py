"""Behavioral-parity coverage for the ``arch_package_diff`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
generation diff, observation spans (in + out), mining telemetry (exactly one
record), and the error taxonomy. Behavioral coverage, NOT legacy AMS
output-shape equivalence.
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
from opencode_arch.mcp.tools.lifecycle.arch_package_diff import (
    arch_package_diff,
)

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"

_DIFF_KEYS = {
    "appeared",
    "disappeared",
    "verdict_transitions",
    "flag_delta",
    "verdict_count_delta",
}


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_package_diff(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_package_diff, "__wrapped__", None) is not None

    # Publish two generations so there is something to diff.
    assert asyncio.run(arch_package_publish(repo_path=str(repo)))["ok"] is True
    assert asyncio.run(arch_package_publish(repo_path=str(repo)))["ok"] is True

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_package_diff(repo_path=str(repo), gen_a="0000001", gen_b="0000002")
    )
    assert out["ok"] is True
    assert out["from_gen"] == "0000001"
    assert out["to_gen"] == "0000002"
    assert isinstance(out["diff"], dict)
    assert set(out["diff"].keys()) == _DIFF_KEYS

    # Spans: one "in" and one "out" tool_call.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_package_diff"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_package_diff"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_package_diff"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_package_diff_unknown_generation(tmp_path):
    repo = _seed_repo(tmp_path / "unknown")
    assert asyncio.run(arch_package_publish(repo_path=str(repo)))["ok"] is True

    out = asyncio.run(
        arch_package_diff(repo_path=str(repo), gen_a="0000001", gen_b="9999999")
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"INVALID_ARGUMENT", "NOT_FOUND"}


def test_parity_package_diff_error_taxonomy(tmp_path):
    bad = asyncio.run(
        arch_package_diff(
            repo_path=str(tmp_path / "nonexistent"),
            gen_a="0000001",
            gen_b="0000002",
        )
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

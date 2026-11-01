"""Behavioral-parity coverage for the ``arch_package_children_add`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
idempotent child-refs ledger result, observation spans (in + out), mining
telemetry, and the error taxonomy. Behavioral coverage, NOT legacy AMS
output-shape equivalence.
"""

from __future__ import annotations

import asyncio

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_package_children_add import (
    arch_package_children_add,
)


def test_parity_package_children_add(tmp_path):
    repo = tmp_path / "happy"
    repo.mkdir()

    assert getattr(arch_package_children_add, "__wrapped__", None) is not None

    out = asyncio.run(
        arch_package_children_add(
            repo_path=str(repo), child_ref="file://x@0000001"
        )
    )
    assert out["ok"] is True
    assert out["added"] is True
    assert out["count"] == 1
    assert out["child_ref"] == "file://x@0000001"

    out = asyncio.run(
        arch_package_children_add(
            repo_path=str(repo), child_ref="file://x@0000001"
        )
    )
    assert out["ok"] is True
    assert out["added"] is False
    assert out["count"] == 1

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_package_children_add"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_package_children_add"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_package_children_add"]
    assert len(drecords) == 2, f"expected 2 telemetry records, got {drecords!r}"
    assert all(r["outcome"] == "ok" for r in drecords)


def test_parity_package_children_add_errors_notfound(tmp_path):
    out = asyncio.run(
        arch_package_children_add(
            repo_path=str(tmp_path / "nonexistent"), child_ref="file://x@0"
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}


def test_parity_package_children_add_errors_badarg(tmp_path):
    repo = tmp_path / "bad"
    repo.mkdir()
    out = asyncio.run(
        arch_package_children_add(repo_path=str(repo), child_ref="")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"

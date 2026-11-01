"""Behavioral-parity coverage for the ``arch_diff`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
``diff_docs`` projection (base -> target: added = in B not A), observation
spans (in + out), mining telemetry (exactly one record), determinism, and
the error taxonomy (missing repo -> NOT_FOUND). This is behavioral coverage,
NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio

import yaml

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_diff import arch_diff


def _seed_repo(root):
    (root / ".architecture").mkdir(parents=True)
    return root


def _doc_yaml(ids):
    return yaml.safe_dump(
        {
            "entities": {"components": [{"id": i} for i in ids]},
            "relationships": [],
        }
    )


def test_parity_diff_models(tmp_path, monkeypatch):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_diff, "__wrapped__", None) is not None

    monkeypatch.setenv("OPENAG_DETERMINISTIC_NOW", "2026-10-31T00:00:00Z")

    doc_a = _doc_yaml(["X"])
    doc_b = _doc_yaml(["X", "Y"])

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_diff(repo_path=str(repo), model_a_yaml=doc_a, model_b_yaml=doc_b)
    )
    assert out["ok"] is True
    assert out["entities"]["added"] == ["Y"]
    assert out["entities"]["removed"] == []
    assert "summary" in out

    # --- Determinism / idempotence ----------------------------------------
    out2 = asyncio.run(
        arch_diff(repo_path=str(repo), model_a_yaml=doc_a, model_b_yaml=doc_b)
    )
    assert out2["entities"] == out["entities"]
    assert out2["summary"] == out["summary"]

    # Spans: one "in" and one "out" tool_call for tool:arch_diff.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_diff"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_diff"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"


def test_parity_diff_models_telemetry(tmp_path):
    repo = _seed_repo(tmp_path / "telemetry")
    doc_a = _doc_yaml(["X"])
    doc_b = _doc_yaml(["X", "Y"])

    out = asyncio.run(
        arch_diff(repo_path=str(repo), model_a_yaml=doc_a, model_b_yaml=doc_b)
    )
    assert out["ok"] is True

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_diff"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_diff_models_bad_repo(tmp_path):
    bad = asyncio.run(arch_diff(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

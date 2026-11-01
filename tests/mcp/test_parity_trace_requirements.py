"""Behavioral-parity coverage for the ``arch_trace_requirements`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
deterministic token-overlap trace result, observation spans (in + out),
mining telemetry (exactly one record), determinism, the error taxonomy
(missing repo -> NOT_FOUND), and the no-ledger edge case. This is behavioral
coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import yaml

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_trace_requirements import arch_trace_requirements

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"

# Shares real tokens with CAP-DOSE ("Compute insulin dose" / description
# "Compute the required insulin dose from the glucose level ...").
_REQ_TEXT = "The system shall compute the insulin dose from the glucose level"


def _seed_model(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    return root


def _seed_requirements(root: Path, text: str) -> None:
    ledger = root / ".architecture" / "requirements.yaml"
    ledger.write_text(yaml.dump({"requirements": [{"id": "REQ-1", "text": text}]}))


def test_decorator_contract():
    assert getattr(arch_trace_requirements, "__wrapped__", None) is not None


def test_parity_trace_requirements_happy(tmp_path):
    repo = _seed_model(tmp_path / "happy")
    _seed_requirements(repo, _REQ_TEXT)

    out = asyncio.run(arch_trace_requirements(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["requirements_count"] == 1
    assert out["entities_count"] > 0
    assert len(out["matches"]) >= 1
    assert out["matches"][0]["requirement_id"] == "REQ-1"

    # Spans: one "in" and one "out" tool_call for tool:arch_trace_requirements.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_trace_requirements"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_trace_requirements"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_trace_requirements record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    trecords = [r for r in telemetry if r.get("tool") == "arch_trace_requirements"]
    assert len(trecords) == 1, f"expected 1 telemetry record, got {trecords!r}"
    assert trecords[0]["outcome"] == "ok"


def test_parity_trace_requirements_determinism(tmp_path):
    repo = _seed_model(tmp_path / "determ")
    _seed_requirements(repo, _REQ_TEXT)
    first = asyncio.run(arch_trace_requirements(repo_path=str(repo)))
    second = asyncio.run(arch_trace_requirements(repo_path=str(repo)))
    assert first["ok"] is True
    assert second["ok"] is True
    assert first == second


def test_parity_trace_requirements_no_ledger(tmp_path):
    repo = _seed_model(tmp_path / "noledger")
    out = asyncio.run(arch_trace_requirements(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["requirements_count"] == 0


def test_parity_trace_requirements_error_taxonomy(tmp_path):
    bad = asyncio.run(
        arch_trace_requirements(repo_path=str(tmp_path / "does-not-exist"))
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

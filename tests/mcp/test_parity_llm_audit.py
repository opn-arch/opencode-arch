"""Behavioral-parity coverage for the ``arch_llm_audit`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
deterministic decomposition second-opinion audit, observation spans (in + out),
mining telemetry (exactly one record), determinism, and the error taxonomy
(missing repo -> NOT_FOUND). Behavioral coverage, NOT legacy AMS output-shape
equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_llm_audit import arch_llm_audit

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    return root


def test_parity_llm_audit_happy(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_llm_audit, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_llm_audit(repo_path=str(repo)))
    assert out["ok"] is True
    assert out["provider"] == "deterministic"
    assert isinstance(out["agreement"], float)
    assert isinstance(out["tool_blocks"], list)
    assert isinstance(out["audit_blocks"], list)
    assert isinstance(out["divergences"], list)
    assert isinstance(out["component_count"], int)

    # Spans: one "in" and one "out" tool_call for tool:arch_llm_audit.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_llm_audit"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_llm_audit"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_llm_audit record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_llm_audit"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_llm_audit_determinism(tmp_path):
    repo = _seed_repo(tmp_path / "determ")
    first = asyncio.run(arch_llm_audit(repo_path=str(repo)))
    second = asyncio.run(arch_llm_audit(repo_path=str(repo)))
    assert first["ok"] is True
    assert second["ok"] is True
    # Non-writer deterministic audit replays identically.
    first_body = {k: v for k, v in first.items() if k != "ok"}
    second_body = {k: v for k, v in second.items() if k != "ok"}
    assert first_body == second_body


def test_parity_llm_audit_error_taxonomy(tmp_path):
    bad = asyncio.run(arch_llm_audit(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

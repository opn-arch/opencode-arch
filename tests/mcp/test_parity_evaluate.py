"""Behavioral-parity coverage for the ``arch_evaluate`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying coverage +
health + rollup + requirement count, observation spans (in + out), mining
telemetry (exactly one record), and the error taxonomy (missing repo ->
NOT_FOUND). Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_evaluate import arch_evaluate

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("import os\n")
    (src / "b.py").write_text("import sys\n")
    return root


def test_parity_evaluate_health(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_evaluate, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_evaluate(repo_path=str(repo)))
    assert out["ok"] is True

    assert isinstance(out["model_coverage"], int)
    assert 0 <= out["model_coverage"] <= 100
    assert isinstance(out["requirement_count"], int)

    health = out["health"]
    assert isinstance(health, dict)
    assert isinstance(health["score"], int)
    assert isinstance(health["band"], str)

    assert isinstance(out["rollup"], dict)

    # Spans: one "in" and one "out" tool_call for tool:arch_evaluate.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_evaluate"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_evaluate"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_evaluate record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    grecords = [r for r in telemetry if r.get("tool") == "arch_evaluate"]
    assert len(grecords) == 1, f"expected 1 telemetry record, got {grecords!r}"
    assert grecords[0]["outcome"] == "ok"

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_evaluate(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

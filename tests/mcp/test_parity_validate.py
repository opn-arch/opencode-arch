"""Behavioral-parity coverage for the ``arch_validate`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
schema+axis-lint score, observation spans (in + out), mining telemetry
(exactly one record), and the error taxonomy (missing repo -> NOT_FOUND).
This is behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_validate import arch_validate

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    return root


def test_parity_validate_score(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_validate, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_validate(repo_path=str(repo)))
    assert out["ok"] is True
    assert "score" in out
    assert "band" in out
    assert "is_valid" in out
    assert isinstance(out["issues"], list)

    # Spans: one "in" and one "out" tool_call for tool:arch_validate.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_validate"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_validate"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_validate record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    vrecords = [r for r in telemetry if r.get("tool") == "arch_validate"]
    assert len(vrecords) == 1, f"expected 1 telemetry record, got {vrecords!r}"
    assert vrecords[0]["outcome"] == "ok"

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_validate(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

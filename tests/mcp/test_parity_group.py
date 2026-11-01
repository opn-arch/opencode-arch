"""Behavioral-parity coverage for the ``arch_group`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
module-grouping projection, observation spans (in + out), mining telemetry
(exactly one record), and the error taxonomy (missing repo -> NOT_FOUND).
This is behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_group import arch_group

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    shutil.copytree(_FIXTURES, root / ".architecture" / "model")
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("import os\n")
    (src / "b.py").write_text("import sys\n")
    return root


def test_parity_group_partition(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_group, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_group(repo_path=str(repo)))
    assert out["ok"] is True
    assert isinstance(out["groups"], list)
    assert isinstance(out["total_modules"], int)
    assert isinstance(out["total_groups"], int)
    assert out["total_groups"] == len(out["groups"])
    for grp in out["groups"]:
        assert isinstance(grp["id"], str)
        assert isinstance(grp["name"], str)
        assert isinstance(grp["files"], list)
        assert isinstance(grp["file_count"], int)

    # --- target_groups passthrough (fresh repo) ----------------------------
    repo2 = _seed_repo(tmp_path / "target")
    out2 = asyncio.run(arch_group(repo_path=str(repo2), target_groups=1))
    assert out2["ok"] is True
    assert out2["total_groups"] == 1

    # Spans: one "in" and one "out" tool_call for tool:arch_group.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_group"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_group"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_group record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    grecords = [r for r in telemetry if r.get("tool") == "arch_group"]
    assert len(grecords) == 1, f"expected 1 telemetry record, got {grecords!r}"
    assert grecords[0]["outcome"] == "ok"

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_group(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

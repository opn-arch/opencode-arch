"""Behavioral-parity coverage for the ``arch_package_stale`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
path-index staleness report, observation spans (in + out), mining telemetry
(exactly one record), determinism (pure read), and the error taxonomy.
Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_package_stale import arch_package_stale

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def test_parity_package_stale(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    assert getattr(arch_package_stale, "__wrapped__", None) is not None

    out = asyncio.run(
        arch_package_stale(repo_path=str(repo), changed_paths=["insulin_pump/alarm.py"])
    )
    assert out["ok"] is True
    assert out["changed_count"] == 1
    assert out["base_generation"] is None
    assert isinstance(out["stale"], list)
    assert any(r["entity_id"] == "COMP-ALARM" for r in out["stale"])

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_package_stale"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_package_stale"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_package_stale"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_package_stale_no_match(tmp_path):
    repo = _seed_repo(tmp_path / "nomatch")
    out = asyncio.run(
        arch_package_stale(repo_path=str(repo), changed_paths=["totally/unrelated.py"])
    )
    assert out["ok"] is True
    assert out["stale"] == []


def test_parity_package_stale_deterministic(tmp_path):
    repo = _seed_repo(tmp_path / "det")
    a = asyncio.run(
        arch_package_stale(repo_path=str(repo), changed_paths=["insulin_pump/alarm.py"])
    )
    b = asyncio.run(
        arch_package_stale(repo_path=str(repo), changed_paths=["insulin_pump/alarm.py"])
    )
    assert a["stale"] == b["stale"]


def test_parity_package_stale_errors_notfound(tmp_path):
    out = asyncio.run(
        arch_package_stale(repo_path=str(tmp_path / "nonexistent"), changed_paths=["x.py"])
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}


def test_parity_package_stale_errors_badarg(tmp_path):
    repo = _seed_repo(tmp_path / "badarg")
    out = asyncio.run(
        arch_package_stale(repo_path=str(repo), changed_paths=[123])
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"

"""Behavioral-parity coverage for the ``arch_proposal_validate`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
proposal validation result, observation spans (in + out), mining telemetry
(exactly one record), and the error taxonomy. Behavioral coverage, NOT legacy
AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_proposal_validate import (
    arch_proposal_validate,
)

_EXEMPLAR = Path(__file__).resolve().parents[1] / "fixtures" / "exemplars" / "insulin-pump"


def _seed_repo(root: Path) -> Path:
    model_dir = root / ".architecture" / "model"
    shutil.copytree(_EXEMPLAR, model_dir)
    return root


def _valid_proposal() -> dict:
    # add a fresh entity that doesn't collide with any exemplar id.
    return {
        "ops": [
            {
                "kind": "add",
                "target": "entity",
                "value": {"id": "COMP-NEW", "name": "New", "kind": "Component"},
                "entity_kind": "components",
            }
        ]
    }


def test_parity_proposal_validate(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_proposal_validate, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(
        arch_proposal_validate(repo_path=str(repo), proposal=_valid_proposal())
    )
    assert out["ok"] is True
    assert out["valid"] in (True, False)
    assert "errors" in out

    # Spans: one "in" and one "out" tool_call.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_proposal_validate"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_proposal_validate"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_proposal_validate"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_proposal_validate_missing_proposal(tmp_path):
    repo = _seed_repo(tmp_path / "missing")
    out = asyncio.run(arch_proposal_validate(repo_path=str(repo), proposal=None))
    assert out["ok"] is False
    assert out["error"]["code"] in {"INVALID_ARGUMENT", "SCHEMA_VIOLATION"}


def test_parity_proposal_validate_missing_repo(tmp_path):
    out = asyncio.run(
        arch_proposal_validate(
            repo_path=str(tmp_path / "nonexistent"), proposal=_valid_proposal()
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

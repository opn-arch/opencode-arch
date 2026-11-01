"""Behavioral-parity coverage for the ``arch_proposal_apply`` tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the
apply result, observation spans (in + out), mining telemetry (exactly one
record), dry_run semantics, and the error taxonomy. Behavioral coverage, NOT
legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import glob
import shutil
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.lifecycle.arch_proposal_apply import (
    arch_proposal_apply,
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


def _gen_files(repo: Path) -> list[str]:
    gen_dir = repo / ".architecture" / "generations"
    if not gen_dir.is_dir():
        return []
    return sorted(glob.glob(str(gen_dir / "*.json")))


def test_parity_proposal_apply(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_proposal_apply, "__wrapped__", None) is not None

    # --- Happy path (real apply) ------------------------------------------
    out = asyncio.run(
        arch_proposal_apply(repo_path=str(repo), proposal=_valid_proposal())
    )
    assert out["ok"] is True
    assert out["applied"] is True
    assert out["gen_id"] == "0000001"

    # Spans: one "in" and one "out" tool_call.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_proposal_apply"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_proposal_apply"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_proposal_apply"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_proposal_apply_dry_run(tmp_path):
    repo2 = _seed_repo(tmp_path / "dry")
    out = asyncio.run(
        arch_proposal_apply(
            repo_path=str(repo2), proposal=_valid_proposal(), dry_run=True
        )
    )
    assert out["ok"] is True
    assert out["applied"] is False
    assert out["dry_run"] is True
    assert _gen_files(repo2) == []


def test_parity_proposal_apply_errors(tmp_path):
    # missing repo
    out = asyncio.run(
        arch_proposal_apply(
            repo_path=str(tmp_path / "nonexistent"), proposal=_valid_proposal()
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    # missing proposal on a valid repo
    repo = _seed_repo(tmp_path / "noprop")
    out2 = asyncio.run(arch_proposal_apply(repo_path=str(repo), proposal=None))
    assert out2["ok"] is False
    assert out2["error"]["code"] in {"INVALID_ARGUMENT", "SCHEMA_VIOLATION"}

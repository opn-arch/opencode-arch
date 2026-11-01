"""Tests for the G3 cut tools: ``arch_propose_cut``, ``arch_score_cut``,
``arch_allocate_contract``.

``arch_propose_cut`` is a gated-write path that NEVER mutates on failure
(the B★ file-conservation safety property); the other two are pure reads.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_cut import (
    arch_allocate_contract,
    arch_propose_cut,
    arch_score_cut,
)

_EXEMPLAR_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "exemplars" / "insulin-pump"


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def tmp_repo(tmp_path):
    """A repo with the insulin-pump exemplar openAG model fragments."""
    model_dir = tmp_path / ".architecture" / "model"
    model_dir.mkdir(parents=True)
    for frag in sorted(_EXEMPLAR_DIR.glob("*.v3.yaml")):
        shutil.copy(frag, model_dir / frag.name)
    return tmp_path


# --- arch_propose_cut ---

_DROP_ALARM_PROPOSAL = {
    "ops": [
        {
            "kind": "remove",
            "target": "entity",
            "entity_kind": "components",
            "value": {"id": "COMP-ALARM"},
        }
    ]
}


def test_propose_cut_rejects_file_dropping_proposal(tmp_repo):
    out = _run(
        arch_propose_cut(
            repo_path=str(tmp_repo),
            node_id="SYS-PUMP",
            proposal=_DROP_ALARM_PROPOSAL,
        )
    )
    assert out["ok"] is False
    assert any("conservation" in r for r in out["rejections"])
    assert any("insulin_pump/alarm.py" in r for r in out["rejections"])


def test_propose_cut_does_not_mutate_on_reject(tmp_repo):
    model_dir = tmp_repo / ".architecture" / "model"
    before = {p.name: p.read_bytes() for p in model_dir.glob("*.v3.yaml")}

    out = _run(
        arch_propose_cut(
            repo_path=str(tmp_repo),
            node_id="SYS-PUMP",
            proposal=_DROP_ALARM_PROPOSAL,
        )
    )
    # A rejected proposal yields a verdict (rejections), never a digest.
    assert out["ok"] is False
    assert "digest" not in out

    after = {p.name: p.read_bytes() for p in model_dir.glob("*.v3.yaml")}
    assert before == after


def test_propose_cut_gate_discriminates_accept_vs_reject(tmp_repo):
    """The gate is genuine, not a blanket reject: a conservation-preserving
    split SUCCEEDS with a digest while the file-dropping split is rejected.

    Proves the B★ property is enforced by the real ``_split``/``apply_proposal``
    gate rather than being a no-op (the drop and the identity-replace differ
    only in whether they conserve the global claimed-file set).
    """
    from opencode_arch.mcp.tools._openag_loader import load_doc

    doc = load_doc(str(tmp_repo))
    alarm = next(
        e
        for e in doc["entities"]["components"]
        if e["id"] == "COMP-ALARM"
    )
    # Identity replace: re-claims alarm.py, so the global file set is conserved.
    conserving = {
        "ops": [
            {
                "kind": "replace",
                "target": "entity",
                "entity_kind": "components",
                "value": alarm,
            }
        ]
    }

    accepted = _run(
        arch_propose_cut(
            repo_path=str(tmp_repo), node_id="SYS-PUMP", proposal=conserving
        )
    )
    rejected = _run(
        arch_propose_cut(
            repo_path=str(tmp_repo), node_id="SYS-PUMP", proposal=_DROP_ALARM_PROPOSAL
        )
    )

    assert accepted["ok"] is True
    assert isinstance(accepted["digest"], str) and accepted["digest"]
    assert rejected["ok"] is False
    assert "digest" not in rejected


def test_propose_cut_invalid_node_id_errors(tmp_repo):
    out = _run(
        arch_propose_cut(
            repo_path=str(tmp_repo),
            node_id="  ",
            proposal=_DROP_ALARM_PROPOSAL,
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_propose_cut_missing_repo_returns_not_found():
    out = _run(
        arch_propose_cut(
            repo_path="/nonexistent/repo/path",
            node_id="SYS-PUMP",
            proposal=_DROP_ALARM_PROPOSAL,
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


# --- arch_score_cut ---

_NODES = ["actuate", "clock", "control", "sense"]
_EDGES = [
    ["actuate", "sense"],
    ["clock", "control"],
    ["control", "actuate"],
    ["sense", "control"],
]
_ALPHA = [["sense", "control", "actuate"], ["clock"]]
_BETA = [["sense", "control"], ["actuate", "clock"]]


def test_score_cut_ranks_alpha_over_beta():
    alpha = _run(arch_score_cut(nodes=_NODES, edges=_EDGES, cells=_ALPHA))
    beta = _run(arch_score_cut(nodes=_NODES, edges=_EDGES, cells=_BETA))
    assert alpha["ok"] is True
    assert beta["ok"] is True
    assert alpha["score"] > beta["score"]


def test_score_cut_rejects_empty_cell():
    out = _run(arch_score_cut(nodes=_NODES, edges=_EDGES, cells=[["actuate"], []]))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


# --- arch_allocate_contract ---

_IF_CUT = {
    "interface": "IF-SENSOR",
    "producer": {
        "id": "COMP-SENSOR",
        "guarantee": "delivers ±X every P",
        "assume": "power available",
    },
    "consumer": {
        "id": "COMP-CONTROLLER",
        "guarantee": "dose ∈ CON-SAFE-BAND",
    },
}


def test_allocate_contract_a2_downlaw():
    out = _run(arch_allocate_contract(interface_cut=_IF_CUT))
    assert out["ok"] is True
    assert out["consumer"]["assume"] == out["producer"]["guarantee"]
    assert out["producer"]["guarantee"]["attribute"] == "behavior"
    assert out["producer"]["guarantee"]["content"] == "delivers ±X every P"


def test_allocate_contract_malformed_errors():
    out = _run(arch_allocate_contract(interface_cut={"interface": "IF-X"}))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"

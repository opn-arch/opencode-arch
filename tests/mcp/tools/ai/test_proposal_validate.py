"""Tests for architect_proposal_validate MCP tool (T17)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml


def _run(coro):
    return asyncio.run(coro)


def _valid_wo_dict(wo_id: str = "wo-test-001") -> dict:
    return {
        "id": wo_id,
        "intent": "Add caching to view resolution",
        "input_slice_refs": [
            {"slice_id": "slice-1", "model_revision": "rev-1"}
        ],
        "expected_proposal_kinds": ["model-patch"],
        "budget": {"max_tokens": 1000, "max_wall_seconds": 60},
        "requested_by": "user@example.com",
        "created_at": "2026-09-04T00:00:00+00:00",
    }


def _write_wo(repo: Path, wo_dict: dict) -> str:
    from architecture_model.ai.work_order import WorkOrder

    wo = WorkOrder.from_dict(wo_dict)
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    (wo_dir / f"{wo.id}.yaml").write_text(
        yaml.safe_dump(wo.to_dict()), encoding="utf-8"
    )
    return wo.id


def _write_slice(repo: Path, slice_id: str, data: object) -> None:
    d = repo / ".architecture" / "lifecycle" / "slices"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slice_id}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def _valid_proposal_dict(wo_id: str = "wo-test-001") -> dict:
    return {
        "kind": "model-patch",
        "provenance": {
            "work_order_id": wo_id,
            "model_version": "rev-1",
            "prompt_digest": "digest-abc",
        },
        "operations": [],
    }


@pytest.fixture
def validate_tool():
    from opencode_arch.mcp.tools.ai.proposal_validate import (
        architect_proposal_validate_tool,
    )

    return architect_proposal_validate_tool


def test_happy_path(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    _write_slice(
        tmp_path,
        "slice-1",
        {"model_revision": "rev-1", "fragment": {"entities": {}}},
    )
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=["slice-1"],
        )
    )
    assert env["ok"] is True, env
    assert env["report"]["passed"] is True
    assert not any(
        f["severity"] == "error" for f in env["report"]["findings"]
    )


def test_empty_slice_ids(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=[],
        )
    )
    assert env["ok"] is True, env
    assert env["report"]["passed"] is True


def test_provenance_mismatch(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    prop = _valid_proposal_dict("wo-OTHER")
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=prop,
            work_order_id=wo_id,
            slice_ids=[],
        )
    )
    assert env["ok"] is True
    assert env["report"]["passed"] is False
    codes = [f.get("code") for f in env["report"]["findings"]]
    assert "provenance-mismatch" in codes


def test_proposal_not_dict(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal="not-a-dict",
            work_order_id=wo_id,
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_proposal_malformed(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal={"provenance": {"work_order_id": wo_id}},  # missing kind
            work_order_id=wo_id,
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert "errors" in env["error"]["details"]
    assert isinstance(env["error"]["details"]["errors"], list)


def test_empty_work_order_id(tmp_path: Path, validate_tool) -> None:
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(),
            work_order_id="",
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_non_string_work_order_id(tmp_path: Path, validate_tool) -> None:
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(),
            work_order_id=123,
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_slice_ids_not_list(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids="slice-1",
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_slice_ids_contains_empty(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=[""],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_slice_ids_contains_non_string(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=[42],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_workorder_missing(tmp_path: Path, validate_tool) -> None:
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict("wo-none"),
            work_order_id="wo-none",
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "workorder_missing"
    assert env["error"]["details"]["work_order_id"] == "wo-none"


def test_workorder_malformed(tmp_path: Path, validate_tool) -> None:
    wo_dir = tmp_path / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    (wo_dir / "wo-bad.yaml").write_text(
        "just: some\nrandom: fields\n", encoding="utf-8"
    )
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict("wo-bad"),
            work_order_id="wo-bad",
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"]["reason"] == "workorder_malformed"


def test_slice_missing(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=["slice-1"],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "slice_missing"
    assert env["error"]["details"]["slice_id"] == "slice-1"


def test_slice_malformed(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    _write_slice(tmp_path, "slice-1", ["not", "a", "dict"])
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=["slice-1"],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"]["reason"] == "slice_malformed"
    assert env["error"]["details"]["slice_id"] == "slice-1"


def test_repo_missing(tmp_path: Path, validate_tool) -> None:
    env = _run(
        validate_tool(
            repo_path=str(tmp_path / "does-not-exist"),
            proposal=_valid_proposal_dict(),
            work_order_id="wo-test-001",
            slice_ids=[],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


def test_finding_structure(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    prop = _valid_proposal_dict("wo-DIFFERENT")
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=prop,
            work_order_id=wo_id,
            slice_ids=[],
        )
    )
    assert env["ok"] is True
    findings = env["report"]["findings"]
    assert findings
    for f in findings:
        assert "severity" in f
        assert "message" in f
        assert "path" in f


def test_multiple_slices(tmp_path: Path, validate_tool) -> None:
    wo_id = _write_wo(tmp_path, _valid_wo_dict())
    _write_slice(
        tmp_path,
        "slice-1",
        {"model_revision": "rev-1", "fragment": {"entities": {}}},
    )
    _write_slice(
        tmp_path,
        "slice-2",
        {"model_revision": "rev-1", "fragment": {"entities": {}}},
    )
    env = _run(
        validate_tool(
            repo_path=str(tmp_path),
            proposal=_valid_proposal_dict(wo_id),
            work_order_id=wo_id,
            slice_ids=["slice-1", "slice-2"],
        )
    )
    assert env["ok"] is True
    assert env["report"]["passed"] is True

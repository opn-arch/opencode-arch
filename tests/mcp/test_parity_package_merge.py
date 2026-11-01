"""Parity tests for arch_package_merge native openAG tool."""
import asyncio
import re
from pathlib import Path

from openag.kernel.generations import GenerationStore
from openag.lifecycle import store_root
from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from opencode_arch.mcp.tools.lifecycle.arch_package_merge import arch_package_merge


def _seed(repo: Path, base, local, remote):
    repo.mkdir(parents=True, exist_ok=True)
    store = GenerationStore(store_root(str(repo)))
    store.record(base)    # 0000001
    store.record(local)   # 0000002
    store.record(remote)  # 0000003
    return repo


def _c(eid, name="n"):
    return {"id": eid, "kind": "Component", "name": name}


def test_parity_package_merge_clean(tmp_path):
    repo = _seed(
        tmp_path / "repo",
        base=[_c("COMP-A", "A")],
        local=[_c("COMP-A", "A"), _c("COMP-B", "B")],
        remote=[_c("COMP-A", "A")],
    )
    out = asyncio.run(arch_package_merge(
        repo_path=str(repo),
        base_revision="0000001",
        local_revision="0000002",
        remote_revision="0000003",
    ))
    assert getattr(arch_package_merge, "__wrapped__", None) is not None
    assert out["ok"] is True
    assert out["conflicts"] == []
    assert re.match(r"^\d{7}$", out["merged_generation"])
    assert out["merged_generation"] == "0000004"
    assert out["stats"]["conflicted"] == 0

    assert len(GenerationStore(store_root(str(repo))).all()) == 4

    records = read_journal(str(repo))
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_package_merge"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_package_merge"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans
    assert out_spans

    recs = [
        r for r in load_records(
            str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
        )
        if r.get("tool") == "arch_package_merge"
    ]
    assert len(recs) == 1
    assert recs[0]["outcome"] == "ok"


def test_parity_package_merge_conflict(tmp_path):
    repo = _seed(
        tmp_path / "repo",
        base=[_c("COMP-A", "A")],
        local=[_c("COMP-A", "A-local")],
        remote=[_c("COMP-A", "A-remote")],
    )
    out = asyncio.run(arch_package_merge(
        repo_path=str(repo),
        base_revision="0000001",
        local_revision="0000002",
        remote_revision="0000003",
    ))
    assert out["ok"] is True
    assert out["merged_generation"] is None
    assert out["conflicts"]
    assert out["conflicts"][0]["entity_id"] == "COMP-A"
    assert out["conflicts"][0]["reason"] == "modify/modify"
    assert out["stats"]["conflicted"] == 1
    assert len(GenerationStore(store_root(str(repo))).all()) == 3


def test_parity_package_merge_notfound(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    GenerationStore(store_root(str(repo))).record([_c("COMP-A", "A")])
    out = asyncio.run(arch_package_merge(
        repo_path=str(repo),
        base_revision="0000001",
        local_revision="0000002",
        remote_revision="0000003",
    ))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_parity_package_merge_badrev(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    out = asyncio.run(arch_package_merge(
        repo_path=str(repo),
        base_revision="bad",
        local_revision="0000002",
        remote_revision="0000003",
    ))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_package_merge_repo_missing(tmp_path):
    out = asyncio.run(arch_package_merge(
        repo_path=str(tmp_path / "nope"),
        base_revision="0000001",
        local_revision="0000002",
        remote_revision="0000003",
    ))
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

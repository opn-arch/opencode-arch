"""Tests for architect_artifact_plan MCP tool."""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.lifecycle.artifact_plan import artifact_plan_tool


def _run(coro):
    return asyncio.run(coro)


def _leaf(art_id: str, renderer: str = "svg", view_id: str = "view-1") -> dict:
    return {
        "id": art_id,
        "renderer": renderer,
        "view_ref": {"view_id": view_id, "model_revision": "0000001"},
    }


def _zip(art_id: str, refs: list[str]) -> dict:
    return {
        "id": art_id,
        "renderer": "zip",
        "bundle_refs": refs,
    }


# 1
def test_happy_two_leaves(tmp_path):
    specs = [_leaf("art-A", "svg"), _leaf("art-B", "markdown")]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is True, env
    plan = env["plan"]
    assert plan["order"] == ["art-A", "art-B"]
    assert plan["nodes"] == [
        {"spec_id": "art-A", "depends_on": []},
        {"spec_id": "art-B", "depends_on": []},
    ]


# 2
def test_zip_with_two_upstreams(tmp_path):
    specs = [
        _leaf("art-A", "svg"),
        _leaf("art-B", "markdown"),
        _zip("zip-1", ["art-B", "art-A"]),
    ]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is True, env
    plan = env["plan"]
    assert plan["order"][:2] == ["art-A", "art-B"]
    assert plan["order"][-1] == "zip-1"
    nodes_by_id = {n["spec_id"]: n for n in plan["nodes"]}
    assert nodes_by_id["zip-1"]["depends_on"] == ["art-A", "art-B"]
    assert nodes_by_id["art-A"]["depends_on"] == []
    assert nodes_by_id["art-B"]["depends_on"] == []


# 3
def test_chain(tmp_path):
    specs = [
        _leaf("art-A", "svg"),
        _zip("zip-1", ["art-A"]),
        _zip("zip-2", ["zip-1"]),
    ]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is True, env
    assert env["plan"]["order"] == ["art-A", "zip-1", "zip-2"]
    nodes_by_id = {n["spec_id"]: n for n in env["plan"]["nodes"]}
    assert nodes_by_id["zip-1"]["depends_on"] == ["art-A"]
    assert nodes_by_id["zip-2"]["depends_on"] == ["zip-1"]


# 4
def test_cycle_rejected(tmp_path):
    specs = [
        _zip("zip-1", ["zip-2"]),
        _zip("zip-2", ["zip-1"]),
    ]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    msg = env["error"]["message"].lower()
    details = env["error"]["details"]
    # cycle nodes surfaced somewhere (message or details)
    combined = msg + " " + str(details).lower()
    assert "zip-1" in combined and "zip-2" in combined


# 5
def test_missing_ref(tmp_path):
    specs = [
        _leaf("art-A", "svg"),
        _zip("zip-1", ["art-A", "art-missing"]),
    ]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    combined = env["error"]["message"] + " " + str(env["error"]["details"])
    assert "art-missing" in combined


# 6
def test_duplicate_ids(tmp_path):
    specs = [_leaf("art-A", "svg"), _leaf("art-A", "markdown")]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    combined = env["error"]["message"] + " " + str(env["error"]["details"])
    assert "art-A" in combined


# 7
def test_empty_specs(tmp_path):
    env = _run(artifact_plan_tool(str(tmp_path), []))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 8
def test_malformed_spec(tmp_path):
    specs = [{"id": "art-A"}]  # missing renderer
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 9
def test_determinism(tmp_path):
    specs = [
        _leaf("art-B", "svg"),
        _leaf("art-A", "markdown"),
        _zip("zip-Z", ["art-B", "art-A"]),
    ]
    e1 = _run(artifact_plan_tool(str(tmp_path), specs))
    e2 = _run(artifact_plan_tool(str(tmp_path), specs))
    assert e1 == e2


# 10
def test_nodes_sorted_by_spec_id(tmp_path):
    specs = [
        _leaf("art-C", "svg"),
        _leaf("art-A", "markdown"),
        _leaf("art-B", "html"),
    ]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is True
    ids = [n["spec_id"] for n in env["plan"]["nodes"]]
    assert ids == sorted(ids)
    assert ids == ["art-A", "art-B", "art-C"]


# 11
def test_repo_path_missing(tmp_path):
    bad = str(tmp_path / "does-not-exist")
    specs = [_leaf("art-A", "svg")]
    env = _run(artifact_plan_tool(bad, specs))
    assert env["ok"] is False
    # resolve_repo raises FileNotFoundError → NOT_FOUND via tool_result.
    assert env["error"]["code"] in ("NOT_FOUND", "INVALID_ARGUMENT")


# 12
def test_non_list_specs(tmp_path):
    env = _run(artifact_plan_tool(str(tmp_path), "not-a-list"))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 13
def test_leaf_only_has_empty_depends_on(tmp_path):
    specs = [_leaf("art-A", "svg")]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is True
    assert env["plan"]["nodes"] == [{"spec_id": "art-A", "depends_on": []}]
    assert env["plan"]["order"] == ["art-A"]


# 14
def test_depends_on_sorted(tmp_path):
    # bundle_refs given in reverse order; depends_on must be sorted asc.
    specs = [
        _leaf("art-A", "svg"),
        _leaf("art-B", "markdown"),
        _leaf("art-C", "html"),
        _zip("zip-1", ["art-C", "art-A", "art-B"]),
    ]
    env = _run(artifact_plan_tool(str(tmp_path), specs))
    assert env["ok"] is True
    nodes_by_id = {n["spec_id"]: n for n in env["plan"]["nodes"]}
    assert nodes_by_id["zip-1"]["depends_on"] == ["art-A", "art-B", "art-C"]

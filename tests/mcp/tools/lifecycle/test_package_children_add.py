"""Tests for architect_package_children_add MCP tool."""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from opencode_arch.mcp.tools.lifecycle.package_children_add import (
    package_children_add_tool,
)
from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool


MODEL_ONE_COMP = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-1
      name: Root
      status: ACTIVE
"""


def _run(coro):
    return asyncio.run(coro)


def _publish(repo):
    return _run(publish_package_tool(repo_path=str(repo), model_yaml=MODEL_ONE_COMP))


def _lifecycle(repo: Path) -> Path:
    return repo / ".architecture" / "lifecycle"


def _make_child(repo: Path, rel: str, arch_id: str = "child-pkg") -> Path:
    """Create a child package.yaml at <lifecycle>/rel and return its path."""
    from architecture_model.lifecycle.versions import SchemaVersions

    child_path = _lifecycle(repo) / rel
    child_dir = child_path.parent
    child_dir.mkdir(parents=True, exist_ok=True)
    (child_dir / ".architecture-model.yaml").write_text(
        MODEL_ONE_COMP, encoding="utf-8"
    )
    child_data = {
        "architecture_id": arch_id,
        "name": arch_id,
        "slug": arch_id,
        "contract_version": SchemaVersions.PACKAGE,
        "model_ref": ".architecture-model.yaml",
        "manifest_ref": "manifest.json",
    }
    child_path.write_text(yaml.safe_dump(child_data, sort_keys=True), encoding="utf-8")
    return child_path


def _call(repo, child_path):
    return _run(
        package_children_add_tool(repo_path=str(repo), child_path=child_path)
    )


# 1
def test_children_add_success(tmp_path):
    _publish(tmp_path)
    _make_child(tmp_path, "child/package.yaml")
    env = _call(tmp_path, "child/package.yaml")
    assert env["ok"] is True, env
    assert env["parent_architecture_id"] == "root-pkg"
    assert env["children"] == ["child/package.yaml"]


# 2
def test_children_add_appends_to_existing(tmp_path):
    _publish(tmp_path)
    _make_child(tmp_path, "a/package.yaml", arch_id="a-pkg")
    _make_child(tmp_path, "b/package.yaml", arch_id="b-pkg")
    env1 = _call(tmp_path, "a/package.yaml")
    assert env1["ok"], env1
    env2 = _call(tmp_path, "b/package.yaml")
    assert env2["ok"], env2
    assert env2["children"] == ["a/package.yaml", "b/package.yaml"]


# 3
def test_children_add_duplicate(tmp_path):
    _publish(tmp_path)
    _make_child(tmp_path, "child/package.yaml")
    env1 = _call(tmp_path, "child/package.yaml")
    assert env1["ok"], env1
    env2 = _call(tmp_path, "child/package.yaml")
    assert env2["ok"] is False
    assert env2["error"]["code"] == "PRECONDITION_FAILED"
    assert env2["error"]["details"]["child_path"] == "child/package.yaml"


# 4
def test_children_add_child_file_missing(tmp_path):
    _publish(tmp_path)
    env = _call(tmp_path, "nope/package.yaml")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["child_path"] == "nope/package.yaml"


# 5
def test_children_add_no_root_package(tmp_path):
    env = _call(tmp_path, "child/package.yaml")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 6
def test_children_add_persists_across_reload(tmp_path):
    from architecture_model.lifecycle.package import load_package

    _publish(tmp_path)
    _make_child(tmp_path, "child/package.yaml")
    env = _call(tmp_path, "child/package.yaml")
    assert env["ok"], env

    pkg = load_package(_lifecycle(tmp_path))
    assert pkg.children == ["child/package.yaml"]


# 7
def test_children_add_bad_repo_path(tmp_path):
    env = _run(
        package_children_add_tool(
            repo_path="/nonexistent-xyz-9999-abc",
            child_path="child/package.yaml",
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 8
def test_children_add_writes_valid_yaml(tmp_path):
    _publish(tmp_path)
    _make_child(tmp_path, "child/package.yaml")
    env = _call(tmp_path, "child/package.yaml")
    assert env["ok"], env

    raw = (_lifecycle(tmp_path) / "package.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    assert data["children"] == ["child/package.yaml"]

"""Tests for architect_package_stale MCP tool."""
from __future__ import annotations

import pytest

import asyncio
from pathlib import Path

import yaml

from opencode_arch.mcp.tools.lifecycle.package_children_add import (
    package_children_add_tool,
)
from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.package_stale import package_stale_tool


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


def _make_child(repo: Path, rel: str, arch_id: str = "child-pkg") -> None:
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
    _run(
        package_children_add_tool(
            repo_path=str(repo),
            child_path=rel,
        )
    )


def _stale(repo, paths):
    return _run(package_stale_tool(repo_path=str(repo), changed_paths=paths))


# 1
def test_stale_empty_changed_paths(tmp_path):
    _publish(tmp_path)
    env = _stale(tmp_path, [])
    assert env["ok"] is True, env
    assert env["stale"] == []


# 2
def test_stale_no_matches(tmp_path):
    _publish(tmp_path)
    env = _stale(tmp_path, ["totally/unrelated.txt"])
    assert env["ok"] is True, env
    assert env["stale"] == []


# 3
def test_stale_direct_match(tmp_path):
    # Root manifest node auto-owns '**/*.py' relative to package root.
    _publish(tmp_path)
    env = _stale(tmp_path, ["src/foo.py"])
    assert env["ok"] is True, env
    ids = {r["node_id"] for r in env["stale"]}
    assert "manifest:root-pkg" in ids
    manifest_rec = next(r for r in env["stale"] if r["node_id"] == "manifest:root-pkg")
    assert "owned path matched" in manifest_rec["reason"]
    assert manifest_rec["kind"] == "manifest"


# 4
def test_stale_transitive_propagation(tmp_path):
    # Child has model_ref -> .architecture-model.yaml at child/.
    # Changing that file makes model:child directly stale, and
    # model:root becomes upstream-stale via child.model -> root.model edge.
    _publish(tmp_path)
    _make_child(tmp_path, "child/package.yaml", arch_id="child-pkg")

    env = _stale(tmp_path, ["child/.architecture-model.yaml"])
    assert env["ok"], env
    by_id = {r["node_id"]: r for r in env["stale"]}
    assert "model:child-pkg" in by_id
    assert "owned path matched" in by_id["model:child-pkg"]["reason"]
    # descendant propagation: manifest:child, model:root, manifest:root
    assert "manifest:child-pkg" in by_id
    assert "model:root-pkg" in by_id
    assert by_id["model:root-pkg"]["reason"] == "upstream stale: model:child-pkg"


# 5
def test_stale_result_sorted_by_kind_and_node_id(tmp_path):
    _publish(tmp_path)
    _make_child(tmp_path, "child/package.yaml", arch_id="child-pkg")

    # Change root model file → model:root direct, manifest:root transitive.
    env = _stale(tmp_path, [".architecture-model.yaml"])
    assert env["ok"], env
    records = env["stale"]
    keys = [(r["kind"], r["node_id"]) for r in records]
    assert keys == sorted(keys)


# 6
@pytest.mark.no_pkg_init
def test_stale_no_root_package(tmp_path):
    env = _stale(tmp_path, ["foo.py"])
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 7
def test_stale_bad_repo_path(tmp_path):
    env = _run(
        package_stale_tool(
            repo_path="/nonexistent-xyz-9999-abc",
            changed_paths=["foo.py"],
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 8
def test_stale_reason_field_present_for_all_stale_records(tmp_path):
    _publish(tmp_path)
    env = _stale(tmp_path, ["src/foo.py"])
    assert env["ok"], env
    assert len(env["stale"]) >= 1
    for rec in env["stale"]:
        assert "reason" in rec
        assert isinstance(rec["reason"], str)
        assert rec["reason"]  # non-empty
        assert set(rec.keys()) >= {
            "node_id", "kind", "owned_paths", "inputs", "digest", "reason",
        }

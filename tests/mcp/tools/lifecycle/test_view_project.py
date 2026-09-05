"""Tests for architect_view_project MCP tool."""
from __future__ import annotations

import asyncio

import pytest
import yaml

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.slice_materialize import (
    slice_materialize_tool,
)
from opencode_arch.mcp.tools.lifecycle.view_project import view_project_tool


MODEL_YAML = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-A
      name: A
      status: ACTIVE
    - id: COMP-B
      name: B
      status: ACTIVE
relationships:
  - from: COMP-A
    to: COMP-B
    type: depends-on
"""


def _run(coro):
    return asyncio.run(coro)


def _slice_spec(**overrides):
    base = {
        "id": "slice-1",
        "architecture_id": "root-pkg",
        "model_revision": "0000001",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["components"]},
    }
    base.update(overrides)
    return base


def _view_spec(projector="test.projector", **overrides):
    base = {
        "id": "view-1",
        "slice_ref": {"slice_id": "slice-1", "model_revision": "0000001"},
        "projector": projector,
        "output_content_kind": "diagram",
    }
    base.update(overrides)
    return base


@pytest.fixture
def test_projector():
    """Register a deterministic test projector; cleanup on teardown."""
    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    def proj(fragment, config):
        return DiagramSpec(id="stub", title="Stub view")

    DEFAULT_REGISTRY.register("test.projector", proj, version="1.0.0")
    try:
        yield "test.projector"
    finally:
        DEFAULT_REGISTRY.unregister("test.projector")


def _publish_and_slice(tmp_path):
    _run(publish_package_tool(repo_path=str(tmp_path), model_yaml=MODEL_YAML))
    env = _run(
        slice_materialize_tool(
            repo_path=str(tmp_path),
            slice_spec=_slice_spec(),
            persist=True,
        )
    )
    assert env["ok"], env
    return env["model_revision"]


# 1
def test_project_success(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    view = _view_spec(projector=test_projector)
    view["slice_ref"]["model_revision"] = rev
    env = _run(view_project_tool(str(tmp_path), view, "slice-1"))
    assert env["ok"] is True, env
    assert env["view_id"] == "view-1"
    assert env["slice_id"] == "slice-1"
    assert env["model_revision"] == rev
    ds = env["diagram_spec"]
    assert isinstance(ds, dict)
    assert ds.get("id") == "stub"
    assert env["provenance"]["projector"] == test_projector
    assert env["provenance"]["projector_version"] == "1.0.0"
    assert env["warnings"] == []


# 2
def test_project_slice_not_found(tmp_path, test_projector):
    _run(publish_package_tool(repo_path=str(tmp_path), model_yaml=MODEL_YAML))
    view = _view_spec()
    env = _run(view_project_tool(str(tmp_path), view, "does-not-exist"))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"].get("slice_id") == "does-not-exist"


# 3
def test_project_view_spec_invalid(tmp_path, test_projector):
    _publish_and_slice(tmp_path)
    bad = _view_spec(projector=test_projector)
    del bad["output_content_kind"]  # required
    env = _run(view_project_tool(str(tmp_path), bad, "slice-1"))
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"].get("detail")


# 4
def test_project_projector_not_registered(tmp_path):
    rev = _publish_and_slice(tmp_path)
    view = _view_spec(projector="does.not.exist")
    view["slice_ref"]["model_revision"] = rev
    env = _run(view_project_tool(str(tmp_path), view, "slice-1"))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"].get("projector") == "does.not.exist"


# 5
def test_project_slice_ref_mismatch(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    view = _view_spec(projector=test_projector)
    view["slice_ref"] = {"slice_id": "different-slice", "model_revision": rev}
    env = _run(view_project_tool(str(tmp_path), view, "slice-1"))
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert "slice_ref" in env["error"]["message"] or "match" in env["error"]["message"]


# 6
def test_project_no_package(tmp_path, test_projector):
    view = _view_spec(projector=test_projector)
    env = _run(view_project_tool(str(tmp_path), view, "slice-1"))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 7
def test_project_federated_slice_rejected(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    # Hand-write a federated slice to disk bypassing T8's rejection.
    slices_dir = tmp_path / ".architecture" / "lifecycle" / "slices"
    fed_spec = _slice_spec(
        id="fed-slice",
        scope="federated",
        selectors={"entity_ids": ["COMP-A"]},
    )
    (slices_dir / "fed-slice.yaml").write_text(yaml.safe_dump(fed_spec))
    view = _view_spec(projector=test_projector)
    view["slice_ref"] = {"slice_id": "fed-slice", "model_revision": rev}
    env = _run(view_project_tool(str(tmp_path), view, "fed-slice"))
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert "federated" in env["error"]["message"].lower()


# 8
def test_project_bad_repo_path(test_projector):
    env = _run(
        view_project_tool(
            "/nonexistent-xyz-9999-abc-does-not-exist",
            _view_spec(projector=test_projector),
            "slice-1",
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"

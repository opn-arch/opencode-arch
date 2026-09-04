"""Tests for architect_view_render MCP tool."""
from __future__ import annotations

import asyncio

import pytest

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.slice_materialize import (
    slice_materialize_tool,
)
from opencode_arch.mcp.tools.lifecycle.view_render import view_render_tool


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


def _artifact_spec(renderer="svg", **overrides):
    base = {
        "id": "art-1",
        "renderer": renderer,
        "view_ref": {"view_id": "view-1", "model_revision": "0000001"},
    }
    base.update(overrides)
    return base


@pytest.fixture
def test_projector():
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


def _view_and_artifact(rev, renderer="svg", projector="test.projector"):
    v = _view_spec(projector=projector)
    v["slice_ref"]["model_revision"] = rev
    a = _artifact_spec(renderer=renderer)
    a["view_ref"]["model_revision"] = rev
    return v, a


# 1
def test_render_svg_success(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    v, a = _view_and_artifact(rev, "svg", test_projector)
    env = _run(view_render_tool(str(tmp_path), v, "slice-1", a))
    assert env["ok"] is True, env
    assert env["artifact_id"] == "art-1"
    assert env["content_type"] == "image/svg+xml"
    assert env["body_utf8"].lstrip().startswith("<") and "svg" in env["body_utf8"].lower()
    assert env["body_base64"] is None
    assert isinstance(env["digest"], str) and len(env["digest"]) == 64
    assert env["warnings"] == []


# 2
def test_render_markdown_success(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    v, a = _view_and_artifact(rev, "markdown", test_projector)
    env = _run(view_render_tool(str(tmp_path), v, "slice-1", a))
    assert env["ok"] is True, env
    assert env["content_type"] == "text/markdown"
    assert isinstance(env["body_utf8"], str) and env["body_utf8"]


# 3
def test_render_ai_context_success(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    v, a = _view_and_artifact(rev, "ai-context", test_projector)
    env = _run(view_render_tool(str(tmp_path), v, "slice-1", a))
    assert env["ok"] is True, env
    assert env["content_type"] == "text/plain"
    assert isinstance(env["body_utf8"], str) and env["body_utf8"]


# 4
def test_render_zip_rejected(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    v, _ = _view_and_artifact(rev, "svg", test_projector)
    # Build a valid zip artifact spec (needs bundle_refs, no view_ref).
    zip_art = {
        "id": "zip-1",
        "renderer": "zip",
        "bundle_refs": ["art-1", "art-2"],
    }
    env = _run(view_render_tool(str(tmp_path), v, "slice-1", zip_art))
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert "zip" in env["error"]["message"].lower()


# 5
def test_render_artifact_spec_invalid(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    v, _ = _view_and_artifact(rev, "svg", test_projector)
    bad = {"id": "art-1"}  # missing renderer
    env = _run(view_render_tool(str(tmp_path), v, "slice-1", bad))
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"].get("detail")


# 6
def test_render_renderer_mismatch(tmp_path, test_projector):
    """Invalid renderer name → SCHEMA_VIOLATION via ArtifactSpec validator."""
    rev = _publish_and_slice(tmp_path)
    v, _ = _view_and_artifact(rev, "svg", test_projector)
    bad = _artifact_spec(renderer="invalid-renderer-name")
    bad["view_ref"]["model_revision"] = rev
    env = _run(view_render_tool(str(tmp_path), v, "slice-1", bad))
    assert env["ok"] is False
    # Pydantic Literal rejects at parse → SCHEMA_VIOLATION.
    assert env["error"]["code"] == "SCHEMA_VIOLATION"


# 7
def test_render_digest_deterministic(tmp_path, test_projector):
    rev = _publish_and_slice(tmp_path)
    v, a = _view_and_artifact(rev, "svg", test_projector)
    e1 = _run(view_render_tool(str(tmp_path), v, "slice-1", a))
    e2 = _run(view_render_tool(str(tmp_path), v, "slice-1", a))
    assert e1["ok"] and e2["ok"]
    assert e1["digest"] == e2["digest"]


# 8
def test_render_slice_not_found(tmp_path, test_projector):
    _run(publish_package_tool(repo_path=str(tmp_path), model_yaml=MODEL_YAML))
    v = _view_spec(projector=test_projector)
    a = _artifact_spec(renderer="svg")
    env = _run(view_render_tool(str(tmp_path), v, "nope", a))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"].get("slice_id") == "nope"

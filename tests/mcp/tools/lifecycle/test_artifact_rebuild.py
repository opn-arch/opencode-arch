"""Tests for architect_artifact_rebuild MCP tool (T12)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool


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


def _publish(repo: Path) -> None:
    env = _run(publish_package_tool(repo_path=str(repo), model_yaml=MODEL_YAML))
    assert env["ok"], env


@pytest.fixture
def stub_projector():
    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    def proj(fragment, config):
        return DiagramSpec(id="stub", title="Stub view")

    DEFAULT_REGISTRY.register("t.stub", proj, version="1.0.0")
    try:
        yield "t.stub"
    finally:
        DEFAULT_REGISTRY.unregister("t.stub")


def _slice(**overrides) -> dict:
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


def _view(projector="t.stub", **overrides) -> dict:
    base = {
        "id": "view-1",
        "slice_ref": {"slice_id": "slice-1", "model_revision": "0000001"},
        "projector": projector,
        "output_content_kind": "diagram",
    }
    base.update(overrides)
    return base


def _artifact(renderer="svg", spec_id="art-1", **overrides) -> dict:
    base = {
        "id": spec_id,
        "renderer": renderer,
        "view_ref": {"view_id": "view-1", "model_revision": "0000001"},
    }
    base.update(overrides)
    return base


def _call(repo, arts, views, slices, force=False):
    from opencode_arch.mcp.tools.lifecycle.artifact_rebuild import (
        architect_artifact_rebuild_tool,
    )
    return _run(architect_artifact_rebuild_tool(
        repo_path=str(repo),
        artifact_specs=arts,
        view_specs=views,
        slice_specs=slices,
        force=force,
    ))


# -------------------------------------------------------------------- happy

def test_happy_svg(tmp_path, stub_projector):
    _publish(tmp_path)
    env = _call(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    assert env["ok"] is True, env
    assert env["skipped"] == []
    assert env["failed"] == []
    assert len(env["built"]) == 1
    entry = env["built"][0]
    assert entry["spec_id"] == "art-1"
    assert entry["renderer"] == "svg"
    assert Path(entry["output_path"]).exists()
    assert entry["emitted_digest"].startswith("sha256:")


def test_happy_two_artifacts_topological(tmp_path, stub_projector):
    _publish(tmp_path)
    arts = [_artifact("svg", "art-a"), _artifact("markdown", "art-b")]
    env = _call(tmp_path, arts, [_view()], [_slice()])
    assert env["ok"] is True, env
    assert env["failed"] == []
    assert [b["spec_id"] for b in env["built"]] == ["art-a", "art-b"]


# -------------------------------------------------------------------- failure surfaced

def test_unresolved_view_ref_ok_true_with_failure(tmp_path, stub_projector):
    _publish(tmp_path)
    env = _call(tmp_path, [_artifact("svg")], [], [_slice()])
    # Plan compliance: failures still return ok: True.
    assert env["ok"] is True, env
    assert env["built"] == []
    assert len(env["failed"]) == 1
    assert env["failed"][0]["reason"] == "unresolved_view_ref"


# -------------------------------------------------------------------- force

def test_force_rebuilds_when_matching(tmp_path, stub_projector):
    _publish(tmp_path)
    env1 = _call(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    digest = env1["built"][0]["emitted_digest"]
    art = _artifact("svg", parameters={"expected_digest": digest})
    env2 = _call(tmp_path, [art], [_view()], [_slice()], force=True)
    assert env2["ok"] is True
    assert env2["skipped"] == []
    assert len(env2["built"]) == 1


# -------------------------------------------------------------------- INVALID_ARGUMENT

def test_empty_artifact_specs(tmp_path):
    env = _call(tmp_path, [], [], [])
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_non_list_artifact_specs(tmp_path):
    env = _call(tmp_path, "not-a-list", [], [])
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_non_list_view_specs(tmp_path):
    env = _call(tmp_path, [_artifact("svg")], "nope", [_slice()])
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_non_list_slice_specs(tmp_path):
    env = _call(tmp_path, [_artifact("svg")], [_view()], "nope")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_non_bool_force(tmp_path):
    env = _call(tmp_path, [_artifact("svg")], [_view()], [_slice()], force="yes")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# -------------------------------------------------------------------- NOT_FOUND

def test_repo_missing(tmp_path):
    missing = tmp_path / "does-not-exist"
    env = _call(missing, [_artifact("svg")], [_view()], [_slice()])
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# -------------------------------------------------------------------- journal + determinism

def test_journal_events_present(tmp_path, stub_projector):
    _publish(tmp_path)
    env = _call(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    assert env["ok"] is True
    events = env["journal_events"]
    assert len(events) == 1
    assert events[0]["kind"] == "artifact.built"
    assert events[0]["spec_id"] == "art-1"


def test_determinism_non_timestamp_fields(tmp_path, stub_projector):
    _publish(tmp_path)
    arts = [_artifact("svg", "a"), _artifact("markdown", "b")]
    env1 = _call(tmp_path, arts, [_view()], [_slice()])
    # remove outputs so second run rebuilds
    for b in env1["built"]:
        Path(b["output_path"]).unlink()
    env2 = _call(tmp_path, arts, [_view()], [_slice()])
    assert [b["spec_id"] for b in env1["built"]] == [b["spec_id"] for b in env2["built"]]
    assert [b["emitted_digest"] for b in env1["built"]] == [
        b["emitted_digest"] for b in env2["built"]
    ]
    # journal event kinds & spec_ids identical (timestamps may differ)
    k1 = [(e["kind"], e["spec_id"]) for e in env1["journal_events"]]
    k2 = [(e["kind"], e["spec_id"]) for e in env2["journal_events"]]
    assert k1 == k2

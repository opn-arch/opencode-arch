"""Tests for architect_slice_materialize MCP tool."""
from __future__ import annotations

import asyncio

import yaml

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.slice_materialize import (
    slice_materialize_tool,
)


MODEL_TWO_COMPS_REL = """\
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


def _publish(repo, model_yaml=MODEL_TWO_COMPS_REL):
    return _run(publish_package_tool(repo_path=str(repo), model_yaml=model_yaml))


def _spec(**overrides):
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


def _mat(repo, spec, persist=True):
    return _run(
        slice_materialize_tool(
            repo_path=str(repo), slice_spec=spec, persist=persist,
        )
    )


# 1
def test_materialize_success_local_scope(tmp_path):
    _publish(tmp_path)
    env = _mat(tmp_path, _spec(), persist=False)
    assert env["ok"] is True, env
    assert env["slice_id"] == "slice-1"
    assert env["architecture_id"] == "root-pkg"
    assert env["model_revision"] == "0000001"
    assert isinstance(env["digest"], str) and env["digest"]
    assert env["warnings"] == []
    comps = env["fragment"]["entities"]["components"]
    ids = {c["id"] for c in comps}
    assert ids == {"COMP-A", "COMP-B"}


# 2
def test_materialize_persists_yaml_file(tmp_path):
    _publish(tmp_path)
    spec = _spec(generated_at="2026-01-01T00:00:00Z")
    env = _mat(tmp_path, spec, persist=True)
    assert env["ok"], env
    assert env["persisted_path"] == "slices/slice-1.yaml"
    p = tmp_path / ".architecture" / "lifecycle" / "slices" / "slice-1.yaml"
    assert p.exists()
    loaded = yaml.safe_load(p.read_text())
    assert loaded == spec


# 3
def test_materialize_persist_false_no_file(tmp_path):
    _publish(tmp_path)
    env = _mat(tmp_path, _spec(), persist=False)
    assert env["ok"], env
    assert env["persisted_path"] is None
    assert not (tmp_path / ".architecture" / "lifecycle" / "slices" / "slice-1.yaml").exists()


# 4
def test_materialize_slice_spec_invalid(tmp_path):
    _publish(tmp_path)
    bad = _spec()
    bad.pop("selectors")
    env = _mat(tmp_path, bad)
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"].get("detail")


# 5
def test_materialize_selectors_empty(tmp_path):
    _publish(tmp_path)
    env = _mat(tmp_path, _spec(selectors={}))
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"


# 6
def test_materialize_federated_scope_rejected(tmp_path):
    _publish(tmp_path)
    env = _mat(
        tmp_path,
        _spec(
            scope="federated",
            selectors={"entity_ids": ["COMP-A"]},
        ),
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert "federated" in env["error"]["message"].lower()


# 7
def test_materialize_no_root_package(tmp_path):
    env = _mat(tmp_path, _spec())
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 8
def test_materialize_missing_model_file(tmp_path):
    _publish(tmp_path)
    # Corrupt the CURRENT model file: delete published generation model.
    import shutil
    gen_dir = tmp_path / ".architecture" / "lifecycle" / "generations"
    for sub in gen_dir.iterdir():
        model_dir = sub / "model"
        if model_dir.exists():
            shutil.rmtree(model_dir)
    env = _mat(tmp_path, _spec())
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert "model" in env["error"]["message"].lower()


# 9
def test_materialize_digest_deterministic(tmp_path):
    _publish(tmp_path)
    spec = _spec(generated_at="2026-01-01T00:00:00Z")
    e1 = _mat(tmp_path, spec, persist=False)
    e2 = _mat(tmp_path, spec, persist=False)
    assert e1["ok"] and e2["ok"]
    assert e1["digest"] == e2["digest"]


# 10
def test_materialize_generated_at_injected(tmp_path):
    _publish(tmp_path)
    spec = _spec()  # no generated_at
    env = _mat(tmp_path, spec, persist=True)
    assert env["ok"], env
    p = tmp_path / ".architecture" / "lifecycle" / "slices" / "slice-1.yaml"
    loaded = yaml.safe_load(p.read_text())
    assert "generated_at" in loaded
    assert loaded["generated_at"]


# 11
def test_materialize_stub_entities(tmp_path):
    _publish(tmp_path)
    # boundary-stubs: select only COMP-A, but rel COMP-A->COMP-B forces stub of COMP-B.
    env = _mat(
        tmp_path,
        _spec(
            closure="boundary-stubs",
            selectors={"entity_ids": ["COMP-A"]},
        ),
        persist=False,
    )
    assert env["ok"], env
    assert isinstance(env["stub_entity_ids"], list)
    assert "COMP-B" in env["stub_entity_ids"]


# 12
def test_materialize_bad_repo_path(tmp_path):
    env = _run(
        slice_materialize_tool(
            repo_path="/nonexistent-xyz-9999-abc-does-not-exist",
            slice_spec=_spec(),
            persist=False,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"

"""Tests for architect_package_load MCP tool."""
from __future__ import annotations

import asyncio

import pytest

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.package_load import package_load_tool

VALID_MODEL_YAML = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-1
      name: Root
      status: ACTIVE
"""

VALID_MODEL_YAML_V2 = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-2
      name: Root2
      status: ACTIVE
"""


def _run(coro):
    return asyncio.run(coro)


def _publish(repo, **kw):
    return _run(publish_package_tool(repo_path=str(repo), **kw))


def _load(repo, **kw):
    return _run(package_load_tool(repo_path=str(repo), **kw))


# 1
def test_load_latest_generation_returns_model_yaml(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    env = _load(tmp_path)
    assert env["ok"] is True, env
    assert env["model_yaml"].strip()
    assert "COMP-1" in env["model_yaml"]


# 2
def test_load_latest_returns_current_revision(tmp_path):
    pub = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    env = _load(tmp_path)
    assert env["ok"]
    assert env["revision"] == pub["revision"]


# 3
def test_load_specific_revision(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML_V2)
    env = _load(tmp_path, revision="0000001")
    assert env["ok"], env
    assert env["revision"] == "0000001"
    assert "COMP-1" in env["model_yaml"]
    assert "COMP-2" not in env["model_yaml"]


# 4
def test_load_no_publication_returns_not_found(tmp_path):
    env = _load(tmp_path)
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 5
def test_load_missing_package_yaml_returns_not_found(tmp_path):
    # Create lifecycle dir but no package.yaml.
    (tmp_path / ".architecture" / "lifecycle").mkdir(parents=True)
    env = _load(tmp_path)
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 6
def test_load_invalid_revision_format_returns_invalid_argument(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    env = _load(tmp_path, revision="abc")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 7
def test_load_nonexistent_revision_returns_not_found(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    env = _load(tmp_path, revision="9999999")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 8
def test_load_bad_repo_path_returns_not_found(tmp_path):
    env = _run(package_load_tool(
        repo_path="/nonexistent-xyz-9999-abc-does-not-exist",
    ))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 9
def test_load_returns_manifest_when_published_with_one(tmp_path):
    _publish(
        tmp_path,
        model_yaml=VALID_MODEL_YAML,
        manifest_json='{"modules": ["a"]}',
    )
    env = _load(tmp_path)
    assert env["ok"]
    assert env["manifest_json"] is not None
    assert "modules" in env["manifest_json"]


# 10
def test_load_returns_none_manifest_when_published_without(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML, manifest_json=None)
    env = _load(tmp_path)
    assert env["ok"]
    assert env["manifest_json"] is None


# 10a — regression: manifest_json='{}' must round-trip, not collapse to None
def test_load_preserves_empty_object_manifest(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML, manifest_json="{}")
    env = _load(tmp_path)
    assert env["ok"], env
    assert env["manifest_json"] == "{}"


# 10b — populated manifest round-trips exactly
def test_load_preserves_populated_manifest(tmp_path):
    payload = '{"modules": []}'
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML, manifest_json=payload)
    env = _load(tmp_path)
    assert env["ok"], env
    assert env["manifest_json"] == payload


# 11
def test_load_revision_normalizes_short_form(tmp_path):
    _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    env = _load(tmp_path, revision="1")
    assert env["ok"], env
    assert env["revision"] == "0000001"
    assert "COMP-1" in env["model_yaml"]


# 12 (bonus) — root_digest present, generation_dir points at real dir
def test_load_returns_root_digest_and_generation_dir(tmp_path):
    pub = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    env = _load(tmp_path)
    assert env["ok"]
    assert env["root_digest"] == pub["digest"]
    assert env["generation_dir"] == pub["index_path"]
    assert env["package_id"] == pub["package_id"]

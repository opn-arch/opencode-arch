"""Tests for architect_package_publish MCP tool."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.lifecycle.package_publish import (
    publish_package_tool,
)

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


def _run(coro):
    return asyncio.run(coro)


def _publish(repo, **kw):
    return _run(publish_package_tool(repo_path=str(repo), **kw))


# 1
def test_publish_success_returns_ok_envelope(tmp_path):
    env = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    assert env["ok"] is True, env
    assert env["package_id"]
    assert env["revision"]
    assert env["digest"].startswith("sha256-v1:")
    assert env["index_path"]
    assert isinstance(env["index_path"], str)


# 2
def test_publish_persists_package_files(tmp_path):
    env = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    assert env["ok"]
    lifecycle_root = tmp_path / ".architecture" / "lifecycle"
    assert (lifecycle_root / "package.yaml").is_file()
    # generation dir must exist and contain model + manifest.
    gen_dir = Path(env["index_path"])
    assert gen_dir.is_dir()
    assert (gen_dir / "model" / ".architecture-model.yaml").is_file()
    assert (gen_dir / "manifest" / "manifest.json").is_file()
    assert (gen_dir / "digest.json").is_file()


# 3
def test_publish_records_journal_event(tmp_path):
    env = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    assert env["ok"]
    journal = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    assert journal.is_file()
    events = [json.loads(l) for l in journal.read_text().splitlines() if l.strip()]
    mcp_events = [e for e in events if e["event"] == "package.publish"]
    assert len(mcp_events) == 1
    payload = mcp_events[0]["payload"]
    assert payload["package_id"] == env["package_id"]
    assert payload["actor"] == "mcp"
    assert payload["digest"] == env["digest"]


# 4
def test_publish_invalid_repo_path_returns_not_found(tmp_path):
    env = _run(publish_package_tool(
        repo_path="/nonexistent/xyz-abc-123-does-not-exist",
        model_yaml=VALID_MODEL_YAML,
    ))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 5
def test_publish_repo_is_file_returns_invalid_argument(tmp_path):
    f = tmp_path / "a-file.txt"
    f.write_text("hi")
    env = _run(publish_package_tool(
        repo_path=str(f), model_yaml=VALID_MODEL_YAML,
    ))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 6
def test_publish_bad_yaml_returns_error(tmp_path):
    env = _publish(tmp_path, model_yaml="not: valid: yaml: at: all: [oops")
    assert env["ok"] is False
    assert env["error"]["code"] in {"INVALID_ARGUMENT", "SCHEMA_VIOLATION"}


# 7
def test_publish_empty_model_yaml_fails_gracefully(tmp_path):
    env = _publish(tmp_path, model_yaml="")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 8
def test_publish_manifest_optional_absent(tmp_path):
    env = _publish(tmp_path, model_yaml=VALID_MODEL_YAML, manifest_json=None)
    assert env["ok"] is True, env


# 9
def test_publish_manifest_valid_json_succeeds(tmp_path):
    env = _publish(
        tmp_path,
        model_yaml=VALID_MODEL_YAML,
        manifest_json='{"modules": []}',
    )
    assert env["ok"] is True, env
    gen_dir = Path(env["index_path"])
    body = (gen_dir / "manifest" / "manifest.json").read_text()
    assert json.loads(body) == {"modules": []}


# 10
def test_publish_manifest_bad_json_returns_error(tmp_path):
    env = _publish(
        tmp_path, model_yaml=VALID_MODEL_YAML, manifest_json="not valid json"
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


# 11
def test_publish_parent_matches_root_records_and_succeeds(tmp_path):
    # First publish creates root pkg.
    env1 = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    assert env1["ok"]
    root_id = env1["package_id"]
    # Publish B referencing root as parent -> succeeds (parent linkage is
    # implicit in Phase 1 tree; tool merely validates the id exists).
    env2 = _publish(
        tmp_path, model_yaml=VALID_MODEL_YAML, parent_package_id=root_id
    )
    assert env2["ok"], env2
    assert env2["revision"] != env1["revision"]


# 12
def test_publish_parent_not_found_returns_precondition_failed(tmp_path):
    env = _publish(
        tmp_path,
        model_yaml=VALID_MODEL_YAML,
        parent_package_id="does-not-exist",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"


# 13
def test_publish_returns_envelope_shape(tmp_path):
    env = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    assert isinstance(env, dict)
    assert "ok" in env
    # Success envelope has no bare dict leaking.
    assert env["ok"] in (True, False)


# 14 (bonus) — second publish advances revision.
def test_publish_second_call_advances_revision(tmp_path):
    e1 = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    e2 = _publish(tmp_path, model_yaml=VALID_MODEL_YAML)
    assert e1["ok"] and e2["ok"]
    assert int(e1["revision"]) + 1 == int(e2["revision"])


# 15 — regression: publish without manifest must NOT write b"{}" on disk.
# Empty (0-byte) file is the unambiguous "no manifest" marker.
def test_publish_without_manifest_does_not_write_empty_json_object(tmp_path):
    env = _publish(tmp_path, model_yaml=VALID_MODEL_YAML, manifest_json=None)
    assert env["ok"], env
    manifest_path = (
        Path(env["index_path"]) / "manifest" / "manifest.json"
    )
    # File exists (Phase 1 always writes it) but must be empty, not "{}".
    assert manifest_path.is_file()
    assert manifest_path.read_bytes() == b""

"""Tests for architect_package_diff MCP tool."""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.package_diff import package_diff_tool


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

MODEL_TWO_COMPS = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-1
      name: Root
      status: ACTIVE
    - id: COMP-2
      name: Extra
      status: ACTIVE
"""

MODEL_REL_AB = """\
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
    - id: COMP-C
      name: C
      status: ACTIVE
relationships:
  - from: COMP-A
    to: COMP-B
    type: depends-on
"""

MODEL_REL_AC = """\
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
    - id: COMP-C
      name: C
      status: ACTIVE
relationships:
  - from: COMP-A
    to: COMP-C
    type: depends-on
"""


def _run(coro):
    return asyncio.run(coro)


def _publish(repo, **kw):
    return _run(publish_package_tool(repo_path=str(repo), **kw))


def _diff(repo, frm, to):
    return _run(
        package_diff_tool(
            repo_path=str(repo), from_revision=frm, to_revision=to,
        )
    )


# 1
def test_diff_success_no_changes(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP, manifest_json='{"a": 1}')
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP, manifest_json='{"a": 1}')
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"] is True, env
    assert env["from_revision"] == "0000001"
    assert env["to_revision"] == "0000002"
    ents = env["diff"]["entities"]
    for kind_diff in ents.values():
        assert kind_diff["added"] == []
        assert kind_diff["removed"] == []
        assert kind_diff["changed"] == []
    rels = env["diff"]["relationships"]
    assert rels["added"] == [] and rels["removed"] == [] and rels["changed"] == []


# 2
def test_diff_added_entity(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    _publish(tmp_path, model_yaml=MODEL_TWO_COMPS)
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"], env
    comps = env["diff"]["entities"]["components"]
    assert "COMP-2" in comps["added"]
    assert comps["removed"] == []


# 3
def test_diff_removed_entity(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_TWO_COMPS)
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"], env
    comps = env["diff"]["entities"]["components"]
    assert "COMP-2" in comps["removed"]
    assert comps["added"] == []


# 4
def test_diff_changed_relationship(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_REL_AB)
    _publish(tmp_path, model_yaml=MODEL_REL_AC)
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"], env
    rels = env["diff"]["relationships"]
    added_keys = {(r["from"], r["to"], r["type"]) for r in rels["added"]}
    removed_keys = {(r["from"], r["to"], r["type"]) for r in rels["removed"]}
    assert ("COMP-A", "COMP-C", "depends-on") in added_keys
    assert ("COMP-A", "COMP-B", "depends-on") in removed_keys


# 5
def test_diff_invalid_revision_format(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    env = _diff(tmp_path, "1", "0000001")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    assert "7-digit zero-padded" in env["error"]["message"]
    assert env["error"]["details"]["revision"] == "1"


# 6
def test_diff_nonexistent_from_revision(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    env = _diff(tmp_path, "0000099", "0000001")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["revision"] == "0000099"


# 7
def test_diff_nonexistent_to_revision(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP)
    env = _diff(tmp_path, "0000001", "0000099")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["revision"] == "0000099"


# 8
def test_diff_manifest_change(tmp_path):
    _publish(
        tmp_path,
        model_yaml=MODEL_ONE_COMP,
        manifest_json='{"files": ["a.py"], "symbols": [{"name": "f", "signature": "() -> int"}]}',
    )
    _publish(
        tmp_path,
        model_yaml=MODEL_ONE_COMP,
        manifest_json='{"files": ["a.py", "b.py"], "symbols": [{"name": "f", "signature": "() -> str"}]}',
    )
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"], env
    man = env["diff"]["manifest"]
    assert "b.py" in man["files_added"]
    assert man["files_removed"] == []
    assert "f" in man["symbols_signature_changed"]


# 9
def test_diff_no_manifest_both_sides(tmp_path):
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP, manifest_json=None)
    _publish(tmp_path, model_yaml=MODEL_ONE_COMP, manifest_json=None)
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"], env
    man = env["diff"]["manifest"]
    assert man["files_added"] == []
    assert man["files_removed"] == []
    assert man["symbols_added"] == []
    assert man["symbols_removed"] == []
    assert man["symbols_signature_changed"] == []


# 10
def test_diff_repo_path_invalid(tmp_path):
    env = _run(
        package_diff_tool(
            repo_path="/nonexistent-xyz-9999-abc-does-not-exist",
            from_revision="0000001",
            to_revision="0000002",
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 11
def test_diff_no_package(tmp_path):
    env = _diff(tmp_path, "0000001", "0000002")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"

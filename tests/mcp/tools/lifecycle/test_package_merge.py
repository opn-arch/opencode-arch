"""Tests for architect_package_merge MCP tool (T20)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle import package_merge as pkg_merge_mod
from opencode_arch.mcp.tools.lifecycle.package_merge import (
    architect_package_merge_tool,
)


def _run(coro):
    return asyncio.run(coro)


def _publish(repo, model_yaml):
    return _run(publish_package_tool(repo_path=str(repo), model_yaml=model_yaml))


def _merge(repo, b, l, r):
    return _run(
        architect_package_merge_tool(
            repo_path=str(repo),
            base_revision=b,
            local_revision=l,
            remote_revision=r,
        )
    )


def _model(components, relationships=None, project="t"):
    parts = [
        "meta:",
        f"  project: {project}",
        "  schema_version: '2.0'",
        "  generated_at: '2026-01-01T00:00:00+00:00'",
        "entities:",
        "  components:",
    ]
    for c in components:
        parts.append(f"    - id: {c['id']}")
        parts.append(f"      name: {c.get('name', 'X')}")
        parts.append(f"      status: {c.get('status', 'ACTIVE')}")
    if relationships:
        parts.append("relationships:")
        for r in relationships:
            parts.append(f"  - from: {r['from']}")
            parts.append(f"    to: {r['to']}")
            parts.append(f"    type: {r.get('type', 'depends-on')}")
    return "\n".join(parts) + "\n"


BASE_MODEL = _model([{"id": "COMP-1", "name": "A"}])
LOCAL_MODEL = _model([{"id": "COMP-1", "name": "A"}, {"id": "COMP-2", "name": "L"}])
REMOTE_MODEL = _model([{"id": "COMP-1", "name": "A"}, {"id": "COMP-3", "name": "R"}])


# 1
def test_happy_path_no_conflicts_publishes(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    _publish(tmp_path, REMOTE_MODEL)
    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    assert env["ok"] is True, env
    assert env["conflicts"] == []
    assert env["merged_digest"]
    assert env["merged_revision"] == "0000004"
    # New generation exists.
    gens_dir = tmp_path / ".architecture" / "lifecycle" / "generations"
    assert (gens_dir / "0000004").exists()


# 2
def test_happy_path_journal_event_recorded(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    _publish(tmp_path, REMOTE_MODEL)
    _merge(tmp_path, "0000001", "0000002", "0000003")
    journal = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    events = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]
    merge_events = [e for e in events if e.get("event") == "lifecycle.package.merge"]
    assert len(merge_events) == 1
    payload = merge_events[0]["payload"]
    assert payload["base_revision"] == "0000001"
    assert payload["local_revision"] == "0000002"
    assert payload["remote_revision"] == "0000003"
    assert payload["merged_revision"] == "0000004"
    assert payload["merged_digest"]
    assert "stats" in payload


# 3
def test_conflict_path_not_published_no_journal(tmp_path):
    # Divergent change on same field.
    base = _model([{"id": "COMP-1", "name": "A"}])
    local = _model([{"id": "COMP-1", "name": "L"}])
    remote = _model([{"id": "COMP-1", "name": "R"}])
    _publish(tmp_path, base)
    _publish(tmp_path, local)
    _publish(tmp_path, remote)
    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    assert env["ok"] is True, env
    assert env["merged_digest"] is None
    assert len(env["conflicts"]) >= 1
    c = env["conflicts"][0]
    assert c["entity_id"] == "COMP-1"
    assert c["field"] == "name"
    # No new generation.
    gens_dir = tmp_path / ".architecture" / "lifecycle" / "generations"
    assert not (gens_dir / "0000004").exists()
    # No journal event of merge.
    journal = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    events = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]
    assert all(e.get("event") != "lifecycle.package.merge" for e in events)


# 4
def test_missing_base_revision(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    env = _merge(tmp_path, "0000099", "0000001", "0000002")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "base_revision_missing"


# 5
def test_missing_local_revision(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    env = _merge(tmp_path, "0000001", "0000099", "0000002")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "local_revision_missing"


# 6
def test_missing_remote_revision(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    env = _merge(tmp_path, "0000001", "0000002", "0000099")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "remote_revision_missing"


# 7
def test_invalid_revision_format(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    env = _merge(tmp_path, "1", "0000001", "0000001")
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"]["reason"] == "base_revision_invalid"


# 8
def test_no_package(tmp_path):
    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "package_missing"


# 9
def test_repo_missing():
    env = _run(
        architect_package_merge_tool(
            repo_path="/nonexistent-xyz-12345-abc",
            base_revision="0000001",
            local_revision="0000002",
            remote_revision="0000003",
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 10
def test_malformed_model_revision(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    _publish(tmp_path, REMOTE_MODEL)
    # Corrupt the local revision model file.
    bad_path = (
        tmp_path / ".architecture" / "lifecycle" / "generations" / "0000002"
        / "model" / ".architecture-model.yaml"
    )
    bad_path.write_text("!!! not: valid: yaml: [", encoding="utf-8")
    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert "malformed" in env["error"]["details"]["reason"]


# 11
def test_merge_integrity_error_maps_to_internal(tmp_path, monkeypatch):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    _publish(tmp_path, REMOTE_MODEL)

    from opencode_arch.lifecycle_exec.merge import MergeIntegrityError

    def _boom(*_a, **_kw):
        raise MergeIntegrityError("synthetic integrity failure")

    monkeypatch.setitem(pkg_merge_mod.__dict__, "three_way_merge", _boom)

    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    assert env["ok"] is False
    assert env["error"]["code"] == "INTERNAL"
    # No traceback / newline leaks.
    assert "\n" not in env["error"]["message"]
    assert "synthetic integrity failure" in env["error"]["details"]["reason"]


# 12
def test_unknown_exception_maps_to_internal(tmp_path, monkeypatch):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    _publish(tmp_path, REMOTE_MODEL)

    def _boom(*_a, **_kw):
        raise RuntimeError("something exploded")

    monkeypatch.setitem(pkg_merge_mod.__dict__, "three_way_merge", _boom)

    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    assert env["ok"] is False
    assert env["error"]["code"] == "INTERNAL"
    assert "\n" not in env["error"]["message"]


# 13
def test_response_is_json_serializable(tmp_path):
    _publish(tmp_path, BASE_MODEL)
    _publish(tmp_path, LOCAL_MODEL)
    _publish(tmp_path, REMOTE_MODEL)
    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    encoded = json.dumps(env)
    assert '"merged_digest"' in encoded


# 14
def test_conflict_response_is_json_serializable(tmp_path):
    base = _model([{"id": "COMP-1", "name": "A"}])
    local = _model([{"id": "COMP-1", "name": "L"}])
    remote = _model([{"id": "COMP-1", "name": "R"}])
    _publish(tmp_path, base)
    _publish(tmp_path, local)
    _publish(tmp_path, remote)
    env = _merge(tmp_path, "0000001", "0000002", "0000003")
    encoded = json.dumps(env)
    assert '"conflicts"' in encoded


# 15
def test_server_registers_package_merge():
    """architect_package_merge must be importable via the server module.

    N66 pattern: FastMCP is not available in the test env (``mcp`` module
    is None), so we can't introspect ``_tool_manager._tools``. We match
    the T19 pattern but strengthen it slightly: import the tool factory
    AND verify the module registers the wrapper by string presence
    (source-level check — sufficient since server.py is a leaf module).
    """
    from opencode_arch.mcp import server as server_mod
    from opencode_arch.mcp.tools.lifecycle.package_merge import (
        architect_package_merge_tool,
    )

    assert callable(architect_package_merge_tool)
    assert hasattr(server_mod, "mcp")

    # Strengthened check: server.py source references the tool. This
    # catches accidental removal of the @mcp.tool() registration that
    # a callable-import check alone would miss.
    server_src = Path(server_mod.__file__).read_text(encoding="utf-8")
    assert "architect_package_merge_tool" in server_src
    assert "async def architect_package_merge" in server_src

"""Tests for architect_package_list_generations MCP tool."""
from __future__ import annotations

import pytest

import asyncio

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
from opencode_arch.mcp.tools.lifecycle.package_list_generations import (
    package_list_generations_tool,
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


def _publish(repo):
    return _run(publish_package_tool(
        repo_path=str(repo), model_yaml=VALID_MODEL_YAML,
    ))


def _list(repo):
    return _run(package_list_generations_tool(repo_path=str(repo)))


# 1
@pytest.mark.no_pkg_init
def test_list_no_publications_returns_not_found(tmp_path):
    env = _list(tmp_path)
    # No package.yaml auto-created by list => NOT_FOUND.
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 2
def test_list_after_one_publish_returns_one_gen(tmp_path):
    _publish(tmp_path)
    env = _list(tmp_path)
    assert env["ok"] is True, env
    assert env["generations"] == ["0000001"]
    assert env["current"] == "0000001"


# 3
def test_list_after_three_publishes_returns_three_sorted(tmp_path):
    _publish(tmp_path)
    _publish(tmp_path)
    _publish(tmp_path)
    env = _list(tmp_path)
    assert env["ok"], env
    assert env["generations"] == ["0000001", "0000002", "0000003"]
    assert env["current"] == "0000003"


# 4
def test_list_bad_repo_returns_not_found(tmp_path):
    env = _run(package_list_generations_tool(
        repo_path="/nonexistent-abc-9999-does-not-exist",
    ))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


# 5
def test_list_returns_package_id(tmp_path):
    _publish(tmp_path)
    env = _list(tmp_path)
    assert env["ok"]
    assert env["package_id"] == "root-pkg"

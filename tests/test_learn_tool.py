"""Tests for architect_learn tool."""
import json
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.learn import record_learning


@pytest.fixture
def learning_path(tmp_path):
    return tmp_path / "arch-learning"


class TestArchitectLearn:
    @pytest.mark.asyncio
    async def test_add_heuristic(self, learning_path):
        result = await record_learning(
            learning_type="heuristic",
            stage="infer",
            condition="module_count > 50",
            action="use package_group strategy",
            rationale="too many caps",
            learned_from="django",
            threshold_parameter="LARGE_REPO_MODULE_THRESHOLD",
            threshold_value="50",
            _learning_path=learning_path,
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["id"].startswith("HR-")

    @pytest.mark.asyncio
    async def test_add_archetype(self, learning_path):
        result = await record_learning(
            learning_type="archetype",
            name="contrib-monolith",
            indicators="large top-level dir, >5 sub-packages",
            problem="treated as one capability",
            solution="recurse one level",
            _learning_path=learning_path,
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["id"].startswith("AP-")

    @pytest.mark.asyncio
    async def test_add_workflow(self, learning_path):
        result = await record_learning(
            learning_type="workflow",
            trigger="score < 50",
            diagnosis="too many components",
            fix_applied="package-level seeding",
            validation="285→24 comps",
            files_changed="infer.py, allocate.py",
            commit="abc123",
            _learning_path=learning_path,
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["id"].startswith("WL-")

    @pytest.mark.asyncio
    async def test_unknown_type(self, learning_path):
        result = await record_learning(
            learning_type="bogus",
            _learning_path=learning_path,
        )
        data = json.loads(result)
        assert data["status"] == "error"

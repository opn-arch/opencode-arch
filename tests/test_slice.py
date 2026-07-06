"""Tests for the architect_slice MCP tool."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.slice import slice_context


class TestSliceTool:
    @pytest.mark.asyncio
    async def test_slice_returns_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def main(): pass\n")
            result = await slice_context(repo_path=tmpdir)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_slice_respects_budget(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(20):
                Path(tmpdir, f"module_{i}.py").write_text(f"def func_{i}(): pass\n")
            result = await slice_context(repo_path=tmpdir, budget=200)
            # 200 tokens * 5 chars generous upper bound
            assert len(result) < 200 * 5

    @pytest.mark.asyncio
    async def test_slice_with_focus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "web.py").write_text("class WebServer: pass\n")
            Path(tmpdir, "db.py").write_text("class Database: pass\n")
            result = await slice_context(repo_path=tmpdir, focus="web")
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_slice_nonexistent_path(self):
        result = await slice_context(repo_path="/tmp/nonexistent_xyz")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_slice_with_model_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def main(): pass\n")
            Path(tmpdir, ".architecture-model.yaml").write_text(
                "meta:\n  project: test\n  schema_version: '1.3'\n"
                "components:\n  - id: COMP-1\n    name: Main\n    status: ACTIVE\n    layer: core\n"
            )
            result = await slice_context(repo_path=tmpdir)
            assert isinstance(result, str)
            assert len(result) > 0

"""Tests for architect_stats and architect_correct tools."""
import asyncio
import pytest
from pathlib import Path


@pytest.fixture
def tmp_repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1")
    return tmp_path


class TestStats:
    def test_returns_session_and_historical(self):
        from opencode_arch.mcp.tools.stats import get_stats
        result = asyncio.run(get_stats())
        assert "session" in result
        assert "suggestions" in result

    def test_with_tool_filter(self):
        from opencode_arch.mcp.tools.stats import get_stats
        result = asyncio.run(get_stats(tool_filter="architect_scan"))
        assert "session" in result


class TestCorrect:
    def test_store_correction(self, tmp_repo):
        from opencode_arch.mcp.tools.correct import store_correction
        result = asyncio.run(store_correction(
            repo_path=str(tmp_repo),
            correction_type="rename",
            target="COMP-1",
            reason="Better name",
            suggestion={"new_name": "DataProcessor"},
        ))
        assert result["stored"] is True
        assert result["correction"]["id"] == "COR-1"
        assert result["correction"]["type"] == "rename"

    def test_invalid_type(self, tmp_repo):
        from opencode_arch.mcp.tools.correct import store_correction
        result = asyncio.run(store_correction(
            repo_path=str(tmp_repo),
            correction_type="invalid",
            target="COMP-1",
            reason="x",
        ))
        assert "error" in result

    def test_bad_path(self):
        from opencode_arch.mcp.tools.correct import store_correction
        result = asyncio.run(store_correction(
            repo_path="/nonexistent",
            correction_type="rename",
            target="COMP-1",
            reason="x",
        ))
        assert "error" in result

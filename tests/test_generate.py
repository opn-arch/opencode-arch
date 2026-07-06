# tests/test_generate.py
"""Tests for the architect_generate MCP tool."""
import pytest
import tempfile
from pathlib import Path
import subprocess
import sys

from opencode_arch.mcp.tools.generate import run_tests_on_generated_code


class TestGenerateTool:
    @pytest.mark.asyncio
    async def test_run_tests_passing(self):
        """Should report pass when generated code passes tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple project with tests
            Path(tmpdir, "calculator.py").write_text(
                "def add(a, b):\n    return a + b\n"
            )
            Path(tmpdir, "test_calculator.py").write_text(
                "from calculator import add\n\n"
                "def test_add():\n    assert add(1, 2) == 3\n"
            )
            result = await run_tests_on_generated_code(repo_path=tmpdir)
            assert result["passed"] is True
            assert result["pass_rate"] == 1.0
            assert result["total_tests"] >= 1

    @pytest.mark.asyncio
    async def test_run_tests_failing(self):
        """Should report failure with details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "calculator.py").write_text(
                "def add(a, b):\n    return a - b  # bug!\n"
            )
            Path(tmpdir, "test_calculator.py").write_text(
                "from calculator import add\n\n"
                "def test_add():\n    assert add(1, 2) == 3\n"
            )
            result = await run_tests_on_generated_code(repo_path=tmpdir)
            assert result["passed"] is False
            assert result["pass_rate"] < 1.0
            assert len(result.get("failures", [])) > 0

    @pytest.mark.asyncio
    async def test_run_tests_no_tests_found(self):
        """Should handle repos with no tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1\n")
            result = await run_tests_on_generated_code(repo_path=tmpdir)
            assert result["total_tests"] == 0

    @pytest.mark.asyncio
    async def test_run_tests_nonexistent_path(self):
        """Should return error for nonexistent path."""
        result = await run_tests_on_generated_code(repo_path="/tmp/nonexistent_xyz")
        assert "error" in result

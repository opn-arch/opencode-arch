"""Tests for the generate CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from opencode_arch.cli.generate import run_generate
from opencode_arch.runner.base import RunResult


class TestGenerateCommand:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Should run generate loop and report passing tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "calc.py").write_text("def add(a, b):\n    return a + b\n")
            Path(tmpdir, "test_calc.py").write_text(
                "from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n"
            )
            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            result = await run_generate(repo_path=tmpdir, runner=mock_runner, max_iter=3)
            assert result["passed"] is True
            assert result["pass_rate"] == 1.0
            assert result["iterations"] == 1

    @pytest.mark.asyncio
    async def test_generate_nonexistent_path(self):
        """Should fail for nonexistent repo."""
        mock_runner = AsyncMock()
        result = await run_generate(repo_path="/tmp/nonexistent_xyz_abc", runner=mock_runner)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generate_no_tests(self):
        """Should handle repos with no tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1\n")
            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            result = await run_generate(repo_path=tmpdir, runner=mock_runner)
            assert result["total_tests"] == 0
            assert result["iterations"] == 1

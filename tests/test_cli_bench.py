"""Tests for the bench CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from opencode_arch.cli.bench import run_bench
from opencode_arch.runner.base import RunResult

MOCK_YAML = "meta:\n  project: t\n  schema_version: '1.3'\nentities:\n  components:\n    - id: COMP-1\n      name: X\n      status: ACTIVE\n"


class TestBenchCommand:
    @pytest.mark.asyncio
    async def test_bench_multiple_repos(self):
        repos = []
        for i in range(3):
            d = tempfile.mkdtemp()
            Path(d, "app.py").write_text(f"x = {i}\n")
            repos.append(d)
        mock_runner = AsyncMock()
        mock_runner.run.return_value = RunResult(output=f"```yaml\n{MOCK_YAML}```", exit_code=0, success=True)
        results = await run_bench(repos=repos, runner=mock_runner)
        assert len(results) == 3
        for r in results:
            assert "success" in r
            assert "repo" in r

    @pytest.mark.asyncio
    async def test_bench_handles_failures(self):
        d = tempfile.mkdtemp()
        Path(d, "app.py").write_text("x = 1\n")
        mock_runner = AsyncMock()
        mock_runner.run.return_value = RunResult(output=f"```yaml\n{MOCK_YAML}```", exit_code=0, success=True)
        results = await run_bench(repos=[d, "/tmp/nonexistent_xyz_bench"], runner=mock_runner)
        assert len(results) == 2
        assert results[1]["success"] is False

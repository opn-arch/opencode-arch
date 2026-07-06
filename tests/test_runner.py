"""Tests for the runner backends."""
import pytest
from unittest.mock import patch, MagicMock

from opencode_arch.runner.base import RunResult
from opencode_arch.runner.opencode import OpencodeRunner


class TestRunResult:
    def test_run_result_fields(self):
        r = RunResult(output="hello", exit_code=0, success=True)
        assert r.output == "hello"
        assert r.exit_code == 0
        assert r.success is True

    def test_run_result_failure(self):
        r = RunResult(output="error", exit_code=1, success=False)
        assert r.success is False


class TestOpencodeRunner:
    @pytest.mark.asyncio
    async def test_run_calls_subprocess(self):
        """Should call opencode run with the prompt."""
        runner = OpencodeRunner()
        mock_result = MagicMock()
        mock_result.stdout = "extraction complete"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("opencode_arch.runner.opencode.subprocess.run", return_value=mock_result) as mock_run:
            result = await runner.run(
                prompt="Extract architecture",
                repo_path="/tmp/test-repo",
            )
            assert result.success is True
            assert "extraction complete" in result.output
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "opencode" in call_args[0][0][0]
            assert "run" in call_args[0][0][1]

    @pytest.mark.asyncio
    async def test_run_handles_timeout(self):
        """Should handle subprocess timeout gracefully."""
        import subprocess
        runner = OpencodeRunner(timeout=1)

        with patch("opencode_arch.runner.opencode.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="opencode", timeout=1)):
            result = await runner.run(prompt="test", repo_path="/tmp/x")
            assert result.success is False
            assert "timeout" in result.output.lower()

    @pytest.mark.asyncio
    async def test_run_handles_not_found(self):
        """Should handle missing opencode binary."""
        runner = OpencodeRunner()

        with patch("opencode_arch.runner.opencode.subprocess.run", side_effect=FileNotFoundError("opencode not found")):
            result = await runner.run(prompt="test", repo_path="/tmp/x")
            assert result.success is False
            assert "not found" in result.output.lower()

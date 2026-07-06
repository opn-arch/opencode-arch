"""Tests for the extract CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from opencode_arch.cli.extract import run_extract, _extract_yaml_from_output
from opencode_arch.runner.base import RunResult


MOCK_AGENT_YAML = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: App
      status: ACTIVE
  capabilities:
    - id: CAP-F1
      name: Core
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
"""


class TestExtractCommand:
    @pytest.mark.asyncio
    async def test_extract_success(self):
        """Should run full extraction loop and return metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("class App: pass\n")

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(
                output=f"```yaml\n{MOCK_AGENT_YAML}```",
                exit_code=0,
                success=True,
            )

            result = await run_extract(
                repo_path=tmpdir,
                runner=mock_runner,
                budget=2000,
                focus="all",
                target_score=80,
            )
            assert result["success"] is True
            assert result["score"] >= 80
            assert result["tokens_used"] > 0
            assert Path(tmpdir, ".architecture-model.yaml").exists()

    @pytest.mark.asyncio
    async def test_extract_runner_failure(self):
        """Should handle runner failure gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1\n")

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(
                output="Error: model unavailable",
                exit_code=1,
                success=False,
            )

            result = await run_extract(
                repo_path=tmpdir,
                runner=mock_runner,
            )
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_extract_nonexistent_path(self):
        """Should fail for nonexistent repo."""
        mock_runner = AsyncMock()
        result = await run_extract(
            repo_path="/tmp/nonexistent_xyz_abc",
            runner=mock_runner,
        )
        assert result["success"] is False


class TestYamlExtraction:
    def test_extract_yaml_fenced(self):
        output = f"Some text\n```yaml\n{MOCK_AGENT_YAML}```\nMore text"
        result = _extract_yaml_from_output(output)
        assert result is not None
        assert "meta:" in result

    def test_extract_yaml_generic_fence(self):
        output = f"Here:\n```\nmeta:\n  project: x\n  schema_version: '1.3'\n```"
        result = _extract_yaml_from_output(output)
        assert result is not None
        assert "meta:" in result

    def test_extract_yaml_none_for_no_yaml(self):
        output = "No yaml here, just text about the project."
        result = _extract_yaml_from_output(output)
        assert result is None

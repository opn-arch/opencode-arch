"""Tests for the architect_extract MCP tool."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import tempfile
import os

from opencode_arch.mcp.tools.extract import extract_architecture


class TestExtractTool:
    @pytest.mark.asyncio
    async def test_extract_returns_yaml_with_surrogate(self):
        """Extract should return a YAML architecture model string when surrogate available."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.return_value = (
            "entities:\n"
            "  capabilities:\n"
            "    - id: CAP-F1\n"
            "      name: Core\n"
            "      status: ACTIVE\n"
        )

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            # Create a temp dir to act as repo
            with tempfile.TemporaryDirectory() as tmpdir:
                # Put a Python file in it so manifest generation works
                Path(tmpdir, "main.py").write_text("def hello(): pass\n")
                result = await extract_architecture(repo_path=tmpdir, focus="all")
                assert "entities" in result
                assert "CAP-F1" in result

    @pytest.mark.asyncio
    async def test_extract_with_focus(self):
        """Extract with focus should pass focus to prompt."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.return_value = (
            "entities:\n  components:\n    - id: COMP-1\n      name: DB\n      status: ACTIVE\n"
        )

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            with tempfile.TemporaryDirectory() as tmpdir:
                Path(tmpdir, "data.py").write_text("class DB: pass\n")
                result = await extract_architecture(repo_path=tmpdir, focus="data-layer")
                assert "entities" in result
                # Verify focus was passed to surrogate prompt
                call_args = mock_surrogate.generate.call_args
                assert "data-layer" in call_args[0][1]  # user prompt contains focus

    @pytest.mark.asyncio
    async def test_extract_nonexistent_path(self):
        """Extract should return error for nonexistent path."""
        result = await extract_architecture(repo_path="/tmp/nonexistent_repo_xyz")
        assert "error" in result.lower() or "Error" in result

    @pytest.mark.asyncio
    async def test_extract_fallback_no_surrogate(self):
        """Extract should fall back to manifest-only when no surrogate available."""
        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=None):
            with tempfile.TemporaryDirectory() as tmpdir:
                Path(tmpdir, "app.py").write_text("class App:\n    pass\n")
                result = await extract_architecture(repo_path=tmpdir, focus="all")
                # Should return some YAML (manifest-based)
                assert isinstance(result, str)
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_extract_surrogate_error(self):
        """Extract should handle surrogate errors gracefully."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.side_effect = RuntimeError("Model unavailable")

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            with tempfile.TemporaryDirectory() as tmpdir:
                Path(tmpdir, "main.py").write_text("x = 1\n")
                result = await extract_architecture(repo_path=tmpdir)
                assert "error" in result.lower() or "Error" in result

    @pytest.mark.asyncio
    async def test_extract_strips_markdown_fences(self):
        """Extract should strip markdown code fences from surrogate output."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.return_value = (
            "```yaml\n"
            "entities:\n"
            "  components:\n"
            "    - id: COMP-1\n"
            "      name: Main\n"
            "```"
        )

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            with tempfile.TemporaryDirectory() as tmpdir:
                Path(tmpdir, "main.py").write_text("x = 1\n")
                result = await extract_architecture(repo_path=tmpdir, focus="all")
                assert "```" not in result
                assert "entities:" in result

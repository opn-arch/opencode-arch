"""Tests for the architect_scan MCP tool."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.scan import scan_repository


class TestScanTool:
    @pytest.mark.asyncio
    async def test_scan_returns_manifest_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def hello():\n    pass\n")
            result = await scan_repository(repo_path=tmpdir)
            assert isinstance(result, dict)
            assert "generated_at" in result
            assert "modules" in result

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self):
        result = await scan_repository(repo_path="/tmp/nonexistent_xyz_123")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_includes_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("class App:\n    x = 1\n")
            result = await scan_repository(repo_path=tmpdir)
            assert "metrics" in result

    @pytest.mark.asyncio
    async def test_scan_detects_python_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir, "myapp")
            pkg.mkdir()
            Path(pkg, "__init__.py").write_text("")
            Path(pkg, "models.py").write_text("class User:\n    pass\n")
            Path(pkg, "views.py").write_text("def index(): pass\n")
            result = await scan_repository(repo_path=tmpdir)
            assert len(result.get("modules", [])) >= 2

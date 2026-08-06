"""Tests for architect_export MCP tool."""
import asyncio
import pytest
from pathlib import Path


MINIMAL_MODEL = """
meta:
  project: test-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Core
      status: ACTIVE
relationships:
  - from: COMP-1
    to: COMP-1
    type: depends_on
"""


@pytest.fixture
def repo_with_model(tmp_path):
    (tmp_path / ".architecture-model.yaml").write_text(MINIMAL_MODEL)
    (tmp_path / "CONTEXT.md").write_text("# Test Context\nSome context here.")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core.py").write_text("def hello(): pass")
    return tmp_path


class TestExportTool:
    def test_export_returns_files(self, repo_with_model):
        from opencode_arch.mcp.tools.export import export_repository
        result = asyncio.run(export_repository(repo_path=str(repo_with_model)))
        assert "error" not in result
        assert result["file_count"] > 0
        assert "files" in result
        # Should always have reference docs
        assert any("README" in f for f in result["files"])

    def test_export_writes_to_output_dir(self, repo_with_model):
        from opencode_arch.mcp.tools.export import export_repository
        out_dir = repo_with_model / "export-out"
        result = asyncio.run(export_repository(
            repo_path=str(repo_with_model),
            output_dir=str(out_dir),
            output_format="dir",
        ))
        assert "error" not in result
        assert out_dir.exists()
        assert any(out_dir.iterdir())

    def test_export_zip(self, repo_with_model):
        from opencode_arch.mcp.tools.export import export_repository
        out = repo_with_model / "export.zip"
        result = asyncio.run(export_repository(
            repo_path=str(repo_with_model),
            output_dir=str(out),
            output_format="zip",
        ))
        assert "error" not in result
        assert out.exists()
        assert out.stat().st_size > 0

    def test_export_custom_prefix(self, repo_with_model):
        from opencode_arch.mcp.tools.export import export_repository
        result = asyncio.run(export_repository(
            repo_path=str(repo_with_model),
            prefix="myprefix",
        ))
        assert "error" not in result
        assert result["prefix"] == "myprefix"
        # Prefixed files should use custom prefix
        prefixed = [f for f in result["files"] if f.startswith("myprefix--")]
        assert len(prefixed) > 0

    def test_export_bad_path(self):
        from opencode_arch.mcp.tools.export import export_repository
        result = asyncio.run(export_repository(repo_path="/nonexistent"))
        assert "error" in result

    def test_export_no_model(self, tmp_path):
        """Export should still work without a model — just fewer files."""
        from opencode_arch.mcp.tools.export import export_repository
        (tmp_path / "CONTEXT.md").write_text("# Context")
        result = asyncio.run(export_repository(repo_path=str(tmp_path)))
        # Should not error — just produce reference docs + CONTEXT
        assert "error" not in result
        assert result["file_count"] >= 1

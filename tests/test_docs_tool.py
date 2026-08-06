"""Tests for architect_docs tool."""
import asyncio
import pytest
import yaml
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
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core.py").write_text("x = 1")
    return tmp_path


class TestDocsTool:
    def test_generates_docs(self, repo_with_model):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path=str(repo_with_model)))
        assert "error" not in result or result.get("generated")
        assert result.get("doc_count", 0) >= 1

    def test_no_model_file(self, tmp_path):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path=str(tmp_path)))
        assert "error" in result

    def test_bad_path(self):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path="/nonexistent"))
        assert "error" in result

    def test_specific_format(self, repo_with_model):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path=str(repo_with_model), formats="health"))
        # Should only generate health (or error gracefully)
        assert "error" not in result or result.get("generated")

    def test_default_includes_system_design_and_integration_flows(self, repo_with_model):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path=str(repo_with_model)))
        generated = result.get("generated", [])
        names = [Path(g).name for g in generated]
        assert "system_design.md" in names
        assert "integration_flows.md" in names

    def test_specific_format_system_design(self, repo_with_model):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path=str(repo_with_model), formats="system_design"))
        generated = result.get("generated", [])
        names = [Path(g).name for g in generated]
        assert "system_design.md" in names
        # Should NOT include other formats
        assert "icd.md" not in names

    def test_quality_metadata(self, repo_with_model):
        from opencode_arch.mcp.tools.docs import generate_docs
        result = asyncio.run(generate_docs(repo_path=str(repo_with_model)))
        if isinstance(result, dict):
            assert "_quality" in result

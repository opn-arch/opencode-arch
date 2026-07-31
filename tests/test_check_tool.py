"""Tests for architect_check MCP tool."""
import pytest
from opencode_arch.mcp.tools.check import check_representativeness


@pytest.mark.asyncio
async def test_check_nonexistent_path():
    result = await check_representativeness(repo_path="/nonexistent", model_yaml="meta: {}")
    assert "error" in result


@pytest.mark.asyncio
async def test_check_returns_scores(tmp_path):
    # Create a minimal project
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Core:\n    def run(self): pass\n\ndef helper(): pass\n")
    (pkg / "cli.py").write_text("from pkg import core\n\nclass CLI:\n    def main(self): pass\n")

    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: Core
      status: ACTIVE
      files: [pkg/core.py]
    - id: C2
      name: CLI
      status: ACTIVE
      files: [pkg/cli.py]
relationships:
  - from: C2
    to: C1
    type: depends_on
"""
    result = await check_representativeness(repo_path=str(tmp_path), model_yaml=model_yaml)
    assert "error" not in result
    assert "file_coverage" in result
    assert "relationship_accuracy" in result
    assert "boundary_coherence" in result
    assert "overall" in result
    assert 0 <= result["overall"] <= 100


@pytest.mark.asyncio
async def test_check_reports_uncovered_files(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Core:\n    def run(self): pass\n")
    (pkg / "orphan.py").write_text("class Orphan:\n    def lost(self): pass\n")

    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: Core
      status: ACTIVE
      files: [pkg/core.py]
relationships: []
"""
    result = await check_representativeness(repo_path=str(tmp_path), model_yaml=model_yaml)
    assert result["file_coverage"] < 100.0
    assert len(result["uncovered_files"]) >= 1

"""Tests for architect_decompose tool."""
import asyncio
import pytest
from pathlib import Path


MINIMAL_MODEL_WITH_COMPONENTS = """
meta:
  project: test-decompose
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Models
      status: ACTIVE
      files: [src/models/user.py, src/models/item.py]
    - id: COMP-2
      name: API
      status: ACTIVE
      files: [src/api/routes.py]
relationships:
  - from: COMP-2
    to: COMP-1
    type: depends_on
"""


@pytest.fixture
def repo_with_model(tmp_path):
    """Create repo with model and source files."""
    (tmp_path / ".architecture-model.yaml").write_text(MINIMAL_MODEL_WITH_COMPONENTS)
    models = tmp_path / "src" / "models"
    models.mkdir(parents=True)
    (models / "__init__.py").write_text("")
    (models / "user.py").write_text("class User:\n    pass\n")
    (models / "item.py").write_text("class Item:\n    pass\n")
    api = tmp_path / "src" / "api"
    api.mkdir(parents=True)
    (api / "__init__.py").write_text("")
    (api / "routes.py").write_text("from ..models.user import User\n\ndef get_user():\n    pass\n")
    return tmp_path


class TestDecomposeTool:
    def test_no_model_file(self, tmp_path):
        from opencode_arch.mcp.tools.decompose import decompose_repository
        result = asyncio.run(decompose_repository(repo_path=str(tmp_path)))
        assert "error" in result

    def test_bad_path(self):
        from opencode_arch.mcp.tools.decompose import decompose_repository
        result = asyncio.run(decompose_repository(repo_path="/nonexistent"))
        assert "error" in result

    def test_decompose_with_model(self, repo_with_model):
        from opencode_arch.mcp.tools.decompose import decompose_repository
        result = asyncio.run(decompose_repository(repo_path=str(repo_with_model)))
        # Should not error (may or may not produce sub-models depending on config)
        assert "error" not in result
        assert "_quality" in result

    def test_quality_metadata(self, repo_with_model):
        from opencode_arch.mcp.tools.decompose import decompose_repository
        result = asyncio.run(decompose_repository(repo_path=str(repo_with_model)))
        assert "_quality" in result
        assert "latency_ms" in result["_quality"]

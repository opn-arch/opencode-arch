"""Tests for entity fallback in architect_extract."""
import asyncio
import pytest
from pathlib import Path


RELATIONSHIPS_ONLY_MODEL = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components: []
relationships:
  - from: COMP-1
    to: COMP-2
    type: depends_on
"""

COMPLETE_MODEL = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Core
      status: ACTIVE
      files: [src/core.py]
    - id: COMP-2
      name: Utils
      status: ACTIVE
      files: [src/utils.py]
relationships:
  - from: COMP-1
    to: COMP-2
    type: depends_on
"""


@pytest.fixture
def python_repo(tmp_path):
    """Create a minimal Python repo with some files."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "core.py").write_text("class Core:\n    pass\n\ndef main():\n    pass\n")
    (src / "utils.py").write_text("def helper():\n    pass\n")
    (src / "api.py").write_text("from .core import Core\n\ndef endpoint():\n    pass\n")
    return tmp_path


class TestEntityFallback:
    def test_relationships_without_entities_returns_suggestions(self, python_repo):
        from opencode_arch.mcp.tools.extract import store_extraction
        result = asyncio.run(store_extraction(
            repo_path=str(python_repo),
            model_yaml=RELATIONSHIPS_ONLY_MODEL,
        ))
        assert result["stored"] is False
        assert result["reason"] == "relationships_without_entities"
        assert "suggested_components" in result
        assert len(result["suggested_components"]) >= 1
        assert "original_relationships" in result

    def test_complete_model_stores_normally(self, python_repo):
        from opencode_arch.mcp.tools.extract import store_extraction
        result = asyncio.run(store_extraction(
            repo_path=str(python_repo),
            model_yaml=COMPLETE_MODEL,
        ))
        assert result.get("stored") is True
        assert (python_repo / ".architecture-model.yaml").exists()

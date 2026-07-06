"""Tests for the architect_validate MCP tool."""
import pytest
from unittest.mock import patch, AsyncMock

from opencode_arch.mcp.tools.validate import validate_architecture


# The parser expects: meta.schema_version, meta.project, entities.<type_list>, relationships[{type, from, to}]
VALID_YAML = """
meta:
  schema_version: "1.3"
  project: "test-project"
entities:
  capabilities:
    - id: CAP-F1
      name: Core Processing
      status: ACTIVE
  components:
    - id: COMP-1
      name: Processor
      status: ACTIVE
relationships:
  - type: realizes
    from: COMP-1
    to: CAP-F1
"""

INVALID_YAML = """
meta:
  schema_version: "1.3"
  project: "test-project"
entities:
  capabilities:
    - id: CAP-F1
      name: Core Processing
      status: ACTIVE
relationships:
  - type: realizes
    from: COMP-MISSING
    to: CAP-F1
"""

MALFORMED_YAML = "not: [valid: yaml: {{{"


class TestValidateTool:
    @pytest.mark.asyncio
    async def test_validate_valid_model(self):
        """Valid model should score high."""
        result = await validate_architecture(model_yaml=VALID_YAML)
        assert "score" in result
        # Score: 100 - warnings for unrealized capability (CAP-F1 IS realized by COMP-1)
        # and missing source_artifacts (warning). Orphan component info doesn't affect.
        assert result["score"] >= 80
        assert result["entity_count"] == 2
        assert result["relationship_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_orphaned_reference(self):
        """Model with orphaned reference should have lower score and issues."""
        result = await validate_architecture(model_yaml=INVALID_YAML)
        assert result["score"] < 100
        assert len(result.get("issues", [])) > 0

    @pytest.mark.asyncio
    async def test_validate_malformed_yaml(self):
        """Malformed YAML should return score=0 with parse error."""
        result = await validate_architecture(model_yaml=MALFORMED_YAML)
        assert result["score"] == 0
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_validate_empty_model(self):
        """Empty model should validate but with low/zero score."""
        empty_yaml = "meta:\n  schema_version: '1.3'\n  project: test\nentities: {}\nrelationships: []\n"
        result = await validate_architecture(model_yaml=empty_yaml)
        assert "score" in result
        assert result["entity_count"] == 0

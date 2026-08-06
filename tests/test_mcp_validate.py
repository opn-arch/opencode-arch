# tests/test_mcp_validate.py
"""Tests for the architect_validate MCP tool."""
import pytest

from opencode_arch.mcp.tools.validate import validate_architecture


VALID_YAML = """\
meta:
  schema_version: "1.3"
  project: "test-project"
entities:
  capabilities:
    - id: CAP-S1
      name: Core Processing
      status: ACTIVE
  components:
    - id: COMP-1
      name: Processor
      status: ACTIVE
relationships:
  - type: realizes
    from: COMP-1
    to: CAP-S1
"""

ORPHAN_YAML = """\
meta:
  schema_version: "1.3"
  project: "test-project"
entities:
  capabilities:
    - id: CAP-S1
      name: Core Processing
      status: ACTIVE
relationships:
  - type: realizes
    from: COMP-MISSING
    to: CAP-S1
"""

MALFORMED_YAML = "{{not valid yaml"


class TestValidateTool:
    @pytest.mark.asyncio
    async def test_validate_valid_model(self):
        result = await validate_architecture(model_yaml=VALID_YAML)
        assert result["score"] >= 80
        assert result["is_valid"] is True
        assert result["entity_count"] == 2
        assert result["relationship_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_orphaned_reference(self):
        result = await validate_architecture(model_yaml=ORPHAN_YAML)
        assert result["score"] < 100
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_validate_malformed_yaml(self):
        result = await validate_architecture(model_yaml=MALFORMED_YAML)
        assert result["score"] == 0
        assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_empty_model(self):
        result = await validate_architecture(
            model_yaml="meta:\n  project: x\n  schema_version: '1.3'\nentities: {}\nrelationships: []\n"
        )
        assert "score" in result
        assert result["entity_count"] == 0

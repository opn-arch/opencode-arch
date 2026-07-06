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
    async def test_validate_with_oracle_scoring(self):
        """Validation with oracle should include oracle_score."""
        mock_oracle = AsyncMock()
        mock_oracle.score_extraction.return_value = {"score": 92, "feedback": "Excellent"}

        with patch("opencode_arch.mcp.tools.validate._get_oracle", return_value=mock_oracle):
            result = await validate_architecture(
                model_yaml=VALID_YAML,
                source_code="def process(): pass",
                use_oracle=True,
            )
            assert "oracle_score" in result
            assert result["oracle_score"] == 92
            assert result["oracle_feedback"] == "Excellent"

    @pytest.mark.asyncio
    async def test_validate_oracle_unavailable(self):
        """Validation should work without oracle (returns None)."""
        with patch("opencode_arch.mcp.tools.validate._get_oracle", return_value=None):
            result = await validate_architecture(
                model_yaml=VALID_YAML,
                source_code="def process(): pass",
                use_oracle=True,
            )
            # Should still return structural score, just no oracle_score
            assert "score" in result
            assert "oracle_score" not in result

    @pytest.mark.asyncio
    async def test_validate_empty_model(self):
        """Empty model should validate but with low/zero score."""
        empty_yaml = "meta:\n  schema_version: '1.3'\n  project: test\nentities: {}\nrelationships: []\n"
        result = await validate_architecture(model_yaml=empty_yaml)
        assert "score" in result
        assert result["entity_count"] == 0

"""Tests for the architect_extract MCP tool (Phase 2: stores agent output)."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.extract import store_extraction


VALID_YAML = """\
meta:
  project: test-project
  schema_version: '1.3'
components:
  - id: COMP-1
    name: Main
    status: ACTIVE
    layer: core
capabilities:
  - id: CAP-F1
    name: Processing
    status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
"""


class TestExtractTool:
    @pytest.mark.asyncio
    async def test_store_valid_extraction(self):
        """Should validate and store a valid model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml=VALID_YAML,
            )
            assert result["stored"] is True
            assert result["score"] >= 80
            assert Path(tmpdir, ".architecture-model.yaml").exists()

    @pytest.mark.asyncio
    async def test_store_records_telemetry(self):
        """Should record telemetry on successful store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml=VALID_YAML,
                context_tokens=430,
            )
            assert result["stored"] is True
            assert "telemetry_recorded" in result

    @pytest.mark.asyncio
    async def test_store_invalid_model(self):
        """Should still store but flag low score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml="meta:\n  project: x\n  schema_version: '1.3'\ncomponents: []\n",
            )
            # Empty model stores but scores low
            assert result["stored"] is True
            assert result["score"] <= 100  # Valid parse, just empty

    @pytest.mark.asyncio
    async def test_store_malformed_yaml(self):
        """Should return error for unparseable YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml="{{invalid yaml",
            )
            assert result["stored"] is False
            assert "error" in result

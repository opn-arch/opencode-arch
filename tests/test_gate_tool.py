"""Tests for architect_gate MCP tool."""
import pytest

from opencode_arch.mcp.tools.gate import check_gate
from opencode_arch.mcp.tools.author import author_architecture


@pytest.mark.asyncio
async def test_gate_with_concept_model(tmp_path):
    # Create a simple Python file so manifest has something
    (tmp_path / "app.py").write_text("def login(): pass\n")

    # Author a model first
    requirements = "# Actors\n- User: end user\n# Capabilities\n- CAP-1: Login"
    await author_architecture(str(tmp_path), requirements)

    # Run gate
    result = await check_gate(str(tmp_path))
    assert "error" not in result
    assert "lifecycle_phase" in result
    assert "overall" in result
    assert "phase_requirements_met" in result
    assert isinstance(result["issues"], list)


@pytest.mark.asyncio
async def test_gate_with_inline_yaml(tmp_path):
    # Create a source file
    (tmp_path / "main.py").write_text("def main(): pass\n")

    model_yaml = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Main
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: Entry
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
"""
    result = await check_gate(str(tmp_path), model_yaml=model_yaml)
    assert "error" not in result
    assert "overall" in result


@pytest.mark.asyncio
async def test_gate_invalid_path():
    result = await check_gate("/nonexistent/path")
    assert "error" in result


@pytest.mark.asyncio
async def test_gate_no_model(tmp_path):
    # No model file and no model_yaml
    result = await check_gate(str(tmp_path))
    assert "error" in result

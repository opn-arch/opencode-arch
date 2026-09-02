"""Tests for architect_gate MCP tool."""
import pytest
import yaml

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


@pytest.mark.asyncio
async def test_gate_aggregates_recursive_model_hierarchy(tmp_path, monkeypatch):
    (tmp_path / "root.py").write_text("def root(): pass\n")
    (tmp_path / "child.py").write_text("def child(): pass\n")
    child_dir = tmp_path / "models" / "child"
    child_dir.mkdir(parents=True)

    root = {
        "meta": {"project": "root", "schema_version": "1.3"},
        "entities": {
            "components": [{"id": "COMP-ROOT", "name": "Root", "status": "ACTIVE", "files": ["root.py"]}],
            "systems": [{
                "id": "SYS-CHILD", "name": "Child", "status": "ACTIVE",
                "source_block": "S1", "sub_model_ref": "models/child/.architecture-model.yaml",
            }],
        },
        "relationships": [],
    }
    child = {
        "meta": {"project": "child", "schema_version": "1.3"},
        "entities": {
            "components": [{"id": "COMP-CHILD", "name": "Child", "status": "ACTIVE", "files": ["child.py"]}],
            "capabilities": [{"id": "CAP-CHILD", "name": "Child capability", "status": "ACTIVE"}],
        },
        "relationships": [],
    }
    (tmp_path / ".architecture-model.yaml").write_text(yaml.safe_dump(root))
    (child_dir / ".architecture-model.yaml").write_text(yaml.safe_dump(child))

    async def _skip_assessment(*args, **kwargs):
        return {}

    monkeypatch.setattr("opencode_arch.mcp.tools.assess.assess_conversation", _skip_assessment)
    monkeypatch.setattr("opencode_arch.mcp.tools.evaluate.evaluate_workspace", _skip_assessment)

    result = await check_gate(str(tmp_path))

    assert result["file_coverage"] == 100.0
    assert result["capability_realization"] == 0.0
    assert result["phase_requirements_met"] is False

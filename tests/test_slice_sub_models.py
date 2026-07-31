"""Test MCP slice tool uses sub-models for block focus."""
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_slice_uses_sub_model_for_block_focus(tmp_path):
    from opencode_arch.mcp.tools.slice import slice_context

    (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Stub
relationships: []
""")
    sub_dir = tmp_path / ".architecture-models" / "F1"
    sub_dir.mkdir(parents=True)
    (sub_dir / ".architecture-model.yaml").write_text("""
meta:
  project: test/F1
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Rich sub-model detail
      pattern: service-layer
relationships: []
""")
    result = await slice_context(str(tmp_path), focus="F1", budget=4000, detail="standard")
    # Should contain sub-model data (project name from sub-model is "test/F1")
    assert "test/F1" in result

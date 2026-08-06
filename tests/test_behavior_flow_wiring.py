"""Tests for behavior flow decomposition wiring in extract and docs tools."""
import asyncio
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


MINIMAL_MODEL_YAML = textwrap.dedent("""\
meta:
  project: test-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Frontend
      status: ACTIVE
    - id: COMP-2
      name: Backend
      status: ACTIVE
  behaviors:
    - id: BEH-1
      name: UserLogin
      status: ACTIVE
      source_file: src/auth.py
    - id: BEH-2
      name: FetchData
      status: ACTIVE
      source_file: src/api.py
relationships:
  - from: BEH-1
    to: COMP-1
    type: realizes
  - from: BEH-1
    to: COMP-2
    type: uses
  - from: BEH-2
    to: COMP-2
    type: realizes
""")


def _make_fake_classification():
    """Build a fake BehaviorClassification result."""
    beh1 = MagicMock()
    beh1.id = "BEH-1"
    beh1.name = "UserLogin"
    flow_trace = MagicMock()
    flow_trace.touched_components = ["COMP-1", "COMP-2"]

    classification = MagicMock()
    classification.cross_component = [(beh1, flow_trace)]
    classification.crud_groups = {}
    classification.trivial = []
    return classification


@pytest.mark.asyncio
async def test_extract_generates_behavior_flows(tmp_path):
    """store_extraction should produce behavior_flows in result when behaviors exist."""
    model_file = tmp_path / ".architecture-model.yaml"
    model_file.write_text(MINIMAL_MODEL_YAML)

    # Create minimal source files so path exists
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def login(): pass")
    (tmp_path / "src" / "api.py").write_text("def fetch(): pass")

    classification = _make_fake_classification()

    with patch("architecture_model.manifest.generator.generate_manifest") as mock_gen, \
         patch("architecture_model.manifest.call_graph.build_call_graph") as mock_cg, \
         patch("architecture_model.orchestration.behavior_flows.classify_behaviors") as mock_classify, \
         patch("architecture_model.orchestration.behavior_flows.build_behavior_manifest") as mock_bm, \
         patch("architecture_model.orchestration.behavior_flows.build_behavior_sub_model") as mock_bsm, \
         patch("architecture_model.orchestration.behavior_flows.build_file_to_comp") as mock_ftc, \
         patch("architecture_model.orchestration.behavior_flows.summarize_crud_group") as mock_scg, \
         patch("architecture_model.docs.behavior_spec.generate_behavior_spec") as mock_spec, \
         patch("architecture_model.docs.behavior_spec.generate_behavior_index") as mock_idx:

        mock_gen.return_value = MagicMock()
        mock_cg.return_value = MagicMock()
        mock_ftc.return_value = {"src/auth.py": "COMP-1", "src/api.py": "COMP-2"}
        mock_classify.return_value = classification
        mock_bm.return_value = MagicMock()
        mock_bsm.return_value = MagicMock()
        mock_spec.return_value = "# BEH-1 Spec"
        mock_idx.return_value = "# Behavior Index"

        # Also mock save_model for sub-model writing
        with patch("architecture_model.core.parser.save_model"):
            from opencode_arch.mcp.tools.extract import store_extraction
            result = await store_extraction(
                repo_path=str(tmp_path),
                model_yaml=MINIMAL_MODEL_YAML,
            )

    assert result.get("stored") is True
    assert "behavior_flows" in result
    assert result["behavior_flows"]["cross_component"] == 1
    assert result["behavior_flows"]["crud_groups"] == 0
    assert result["behavior_flows"]["trivial"] == 0


@pytest.mark.asyncio
async def test_docs_behaviors_format(tmp_path):
    """generate_docs with formats='behaviors' should create behaviors/index.md."""
    model_file = tmp_path / ".architecture-model.yaml"
    model_file.write_text(MINIMAL_MODEL_YAML)

    classification = _make_fake_classification()

    with patch("architecture_model.manifest.generator.generate_manifest") as mock_gen, \
         patch("architecture_model.manifest.call_graph.build_call_graph") as mock_cg, \
         patch("architecture_model.orchestration.behavior_flows.classify_behaviors") as mock_classify, \
         patch("architecture_model.orchestration.behavior_flows.build_behavior_manifest") as mock_bm, \
         patch("architecture_model.orchestration.behavior_flows.build_file_to_comp") as mock_ftc, \
         patch("architecture_model.orchestration.behavior_flows.summarize_crud_group") as mock_scg, \
         patch("architecture_model.docs.behavior_spec.generate_behavior_spec") as mock_spec, \
         patch("architecture_model.docs.behavior_spec.generate_behavior_index") as mock_idx:

        mock_gen.return_value = MagicMock()
        mock_cg.return_value = MagicMock()
        mock_ftc.return_value = {"src/auth.py": "COMP-1", "src/api.py": "COMP-2"}
        mock_classify.return_value = classification
        mock_bm.return_value = MagicMock()
        mock_spec.return_value = "# BEH-1 Spec"
        mock_idx.return_value = "# Behavior Index"

        from opencode_arch.mcp.tools.docs import generate_docs
        result = await generate_docs(repo_path=str(tmp_path), formats="behaviors")

    assert result.get("generated")
    assert any("behaviors/index.md" in p for p in result["generated"])
    index_file = tmp_path / "docs" / "architecture" / "behaviors" / "index.md"
    assert index_file.exists()
    assert index_file.read_text() == "# Behavior Index"

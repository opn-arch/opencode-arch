"""Test CLI confidence command."""
from pathlib import Path
from opencode_arch.cli.confidence import run_confidence


def test_run_confidence_with_model(tmp_path):
    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: FullComp
      status: ACTIVE
      contract: Does X
      pattern: adapter
      files: [a.py]
      source_block: S1
    - id: C2
      name: EmptyComp
      status: ACTIVE
      source_block: S1
relationships: []
"""
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
    output = run_confidence(str(tmp_path))
    assert "S1" in output
    assert "FullComp" in output or "C1" in output


def test_run_confidence_no_model(tmp_path):
    output = run_confidence(str(tmp_path))
    assert "no model" in output.lower() or "not found" in output.lower() or "error" in output.lower()

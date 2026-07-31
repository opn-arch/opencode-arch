"""Tests for the launch pre-flight logic."""
import json
from pathlib import Path

import pytest

from opencode_arch.cli.launch import (
    run_launch, _update_context_md, _ensure_opencode_json,
    CONTEXT_START, CONTEXT_END,
)


class TestUpdateContextMd:
    def test_creates_new_context_md(self, tmp_path):
        _update_context_md(tmp_path, None, "", None, None)
        content = (tmp_path / "CONTEXT.md").read_text()
        assert CONTEXT_START in content
        assert CONTEXT_END in content
        assert "opencode-arch" in content

    def test_appends_to_existing(self, tmp_path):
        (tmp_path / "CONTEXT.md").write_text("# My Project\n\nExisting content.\n")
        _update_context_md(tmp_path, None, "slice content", None, None)
        content = (tmp_path / "CONTEXT.md").read_text()
        assert "# My Project" in content
        assert "Existing content." in content
        assert CONTEXT_START in content
        assert "slice content" in content

    def test_replaces_existing_section(self, tmp_path):
        initial = f"# Project\n\n{CONTEXT_START}\nold content\n{CONTEXT_END}\n\n# Footer\n"
        (tmp_path / "CONTEXT.md").write_text(initial)
        _update_context_md(tmp_path, None, "new slice", None, None)
        content = (tmp_path / "CONTEXT.md").read_text()
        assert "old content" not in content
        assert "new slice" in content
        assert "# Project" in content
        assert "# Footer" in content

    def test_idempotent(self, tmp_path):
        _update_context_md(tmp_path, None, "slice1", None, None)
        _update_context_md(tmp_path, None, "slice2", None, None)
        content = (tmp_path / "CONTEXT.md").read_text()
        assert content.count(CONTEXT_START) == 1
        assert "slice2" in content
        assert "slice1" not in content


class TestEnsureOpencodeJson:
    def test_creates_if_missing(self, tmp_path):
        _ensure_opencode_json(tmp_path)
        path = tmp_path / "opencode.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["name"] == "opencode-arch"
        assert len(data["mcp"]["tools"]) == 9

    def test_does_not_overwrite_existing(self, tmp_path):
        (tmp_path / "opencode.json").write_text('{"custom": true}')
        _ensure_opencode_json(tmp_path)
        data = json.loads((tmp_path / "opencode.json").read_text())
        assert data == {"custom": True}


class TestRunLaunch:
    def test_preflight_on_empty_dir(self, tmp_path):
        # Create a minimal Python file so scan finds something
        (tmp_path / "app.py").write_text("def hello(): pass\n")
        result = run_launch(str(tmp_path), skip_exec=True)
        assert result["repo"] == str(tmp_path)
        assert "context_md" in result["steps"]
        assert "opencode_json" in result["steps"]
        assert (tmp_path / "CONTEXT.md").exists()
        assert (tmp_path / "opencode.json").exists()

    def test_preflight_with_existing_model(self, tmp_path):
        # Create a valid model file
        from architecture_model.core.types import ArchitectureModel, Entities, Component, ModelMeta
        from architecture_model.core.parser import save_model
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(components=[Component(id="COMP-1", name="Core", status="ACTIVE")]),
            relationships=[],
        )
        save_model(model, tmp_path / ".architecture-model.yaml")
        (tmp_path / "core.py").write_text("def main(): pass\n")
        
        result = run_launch(str(tmp_path), skip_exec=True)
        assert "model" in result["steps"]

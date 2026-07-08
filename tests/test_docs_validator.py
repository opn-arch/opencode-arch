"""Tests for the docs validator - checks generated docs against model and manifest."""
from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel,
    ModelMeta,
    Entities,
    Component,
    Interface,
    Status,
    ComponentKind,
    InterfaceType,
)


def _make_model():
    """Create a minimal model for testing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.4", project="test"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Core Engine", status=Status.ACTIVE, kind=ComponentKind.MODULE),
                Component(id="COMP-2", name="CLI Module", status=Status.ACTIVE, kind=ComponentKind.MODULE),
            ],
            interfaces=[
                Interface(id="IF-1", name="REST API", status=Status.ACTIVE, type=InterfaceType.REST),
            ],
        ),
        relationships=[],
    )


SAMPLE_MANIFEST = {
    "modules": [
        {"file": "src/core/engine.py", "functions": ["process", "validate"], "classes": ["Engine"]},
        {"file": "src/cli/main.py", "functions": ["main", "parse_args"], "classes": ["CLI"]},
    ],
    "metrics": {"total_files": 10, "total_lines": 2000},
}


def _write_doc(tmp_path, filename, content, artifact_id=None):
    """Write a test doc file, optionally with frontmatter."""
    doc = ""
    if artifact_id:
        doc = f"---\nartifact_id: {artifact_id}\n---\n"
    doc += content
    (tmp_path / filename).write_text(doc)


class TestValidateDocsAllPass:
    """test_validate_docs_all_pass - docs with only valid references -> is_valid=True"""

    def test_all_valid_references_pass(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        # Doc only references things that exist in manifest/model
        content = (
            "# System Overview\n"
            "\n"
            "The `src/core/engine.py` file contains the core logic.\n"
            "The `process()` function handles data.\n"
            "Component `COMP-1` is the Core Engine.\n"
        )
        _write_doc(tmp_path, "system-overview.md", content, artifact_id="system-overview")

        result = validate_docs(tmp_path, model, SAMPLE_MANIFEST)

        assert result.is_valid is True
        assert result.total_artifacts == 1
        assert result.passed == 1
        assert result.failed == 0


class TestValidateDocsInvalidPath:
    """test_validate_docs_invalid_path - doc references nonexistent path -> error"""

    def test_invalid_path_produces_error(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        content = (
            "# Overview\n"
            "\n"
            "See `src/nonexistent.py` for details.\n"
        )
        _write_doc(tmp_path, "overview.md", content, artifact_id="overview")

        result = validate_docs(tmp_path, model, SAMPLE_MANIFEST)

        assert result.is_valid is False
        assert len(result.issues) >= 1
        error_issues = [i for i in result.issues if i.severity == "error"]
        assert any(i.issue_type == "invalid_path" for i in error_issues)
        assert any("src/nonexistent.py" in i.message for i in error_issues)


class TestValidateDocsUnknownFunction:
    """test_validate_docs_unknown_function - unknown function -> warning (not error)"""

    def test_unknown_function_produces_warning(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        content = (
            "# API\n"
            "\n"
            "Call `nonexistent_func()` to start.\n"
        )
        _write_doc(tmp_path, "api.md", content, artifact_id="api")

        result = validate_docs(tmp_path, model, SAMPLE_MANIFEST)

        # Should be valid since warnings don't fail
        assert result.is_valid is True
        warning_issues = [i for i in result.issues if i.severity == "warning"]
        assert any(i.issue_type == "unknown_function" for i in warning_issues)
        assert any("nonexistent_func" in i.message for i in warning_issues)


class TestValidateDocsUnknownComponent:
    """test_validate_docs_unknown_component - COMP-999 not in model -> error"""

    def test_unknown_component_produces_error(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        content = (
            "# Components\n"
            "\n"
            "The `COMP-999` handles billing.\n"
        )
        _write_doc(tmp_path, "components.md", content, artifact_id="components")

        result = validate_docs(tmp_path, model, SAMPLE_MANIFEST)

        assert result.is_valid is False
        error_issues = [i for i in result.issues if i.severity == "error"]
        assert any(i.issue_type == "unknown_component" for i in error_issues)
        assert any("COMP-999" in i.message for i in error_issues)


class TestValidateDocsEmptyDir:
    """test_validate_docs_empty_dir - no markdown files -> total=0, is_valid=True"""

    def test_empty_directory_is_valid(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        result = validate_docs(tmp_path, model, SAMPLE_MANIFEST)

        assert result.is_valid is True
        assert result.total_artifacts == 0
        assert result.passed == 0
        assert result.failed == 0
        assert result.issues == []


class TestExtractFileReferences:
    """test_extract_file_references - correctly extracts backtick-wrapped file paths"""

    def test_extracts_py_paths(self):
        from opencode_arch.cli.docs_validator import _extract_file_references

        content = (
            "Line 1\n"
            "See `src/core/engine.py` for details.\n"
            "Also check `tests/test_main.py` and regular text.\n"
            "This is not a path: `some_variable`\n"
        )
        refs = _extract_file_references(content)
        paths = [path for _, path in refs]

        assert "src/core/engine.py" in paths
        assert "tests/test_main.py" in paths
        assert "some_variable" not in paths

    def test_extracts_various_extensions(self):
        from opencode_arch.cli.docs_validator import _extract_file_references

        content = (
            "`config/settings.yaml` has the config.\n"
            "`package.json` is in the root.\n"
            "`src/app.ts` is the entry point.\n"
            "`pyproject.toml` has dependencies.\n"
        )
        refs = _extract_file_references(content)
        paths = [path for _, path in refs]

        assert "config/settings.yaml" in paths
        assert "package.json" in paths
        assert "src/app.ts" in paths
        assert "pyproject.toml" in paths

    def test_returns_line_numbers(self):
        from opencode_arch.cli.docs_validator import _extract_file_references

        content = (
            "Line 1: nothing\n"
            "Line 2: `src/foo.py` here\n"
            "Line 3: nothing\n"
            "Line 4: `src/bar.py` here\n"
        )
        refs = _extract_file_references(content)

        assert (2, "src/foo.py") in refs
        assert (4, "src/bar.py") in refs


class TestExtractCodeReferences:
    """test_extract_code_references - correctly extracts function/class names"""

    def test_extracts_function_calls(self):
        from opencode_arch.cli.docs_validator import _extract_code_references

        content = (
            "Call `process()` to start.\n"
            "Then `validate()` checks.\n"
            "But `some text` is not a function.\n"
        )
        refs = _extract_code_references(content)
        names = [name for _, name in refs]

        assert "process" in names
        assert "validate" in names
        assert "some text" not in names

    def test_extracts_class_names(self):
        from opencode_arch.cli.docs_validator import _extract_code_references

        content = (
            "The `Engine` class handles processing.\n"
            "`CLI` is the command-line interface.\n"
            "But `lowercase` is not a class.\n"
        )
        refs = _extract_code_references(content)
        names = [name for _, name in refs]

        assert "Engine" in names
        assert "CLI" in names

    def test_returns_line_numbers(self):
        from opencode_arch.cli.docs_validator import _extract_code_references

        content = (
            "Line 1: `process()` here\n"
            "Line 2: nothing\n"
            "Line 3: `Engine` there\n"
        )
        refs = _extract_code_references(content)

        assert (1, "process") in refs
        assert (3, "Engine") in refs


class TestGetManifestFiles:
    """test_get_manifest_files - extracts file set from manifest structure"""

    def test_extracts_from_modules(self):
        from opencode_arch.cli.docs_validator import _get_manifest_files

        files = _get_manifest_files(SAMPLE_MANIFEST)

        assert "src/core/engine.py" in files
        assert "src/cli/main.py" in files

    def test_returns_empty_for_none(self):
        from opencode_arch.cli.docs_validator import _get_manifest_files

        files = _get_manifest_files(None)
        assert files == set()

    def test_handles_files_key(self):
        from opencode_arch.cli.docs_validator import _get_manifest_files

        manifest = {
            "modules": [],
            "files": ["README.md", "setup.py"],
        }
        files = _get_manifest_files(manifest)

        assert "README.md" in files
        assert "setup.py" in files


class TestArtifactWithNoIssuesPasses:
    """test_artifact_with_no_issues_passes - artifact with valid content passes"""

    def test_clean_artifact_passes(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        # Only references things that exist
        content = (
            "# Architecture Overview\n"
            "\n"
            "This system has two main components:\n"
            "- `COMP-1` (Core Engine)\n"
            "- `COMP-2` (CLI Module)\n"
            "\n"
            "The core uses `src/core/engine.py` with the `process()` function.\n"
        )
        _write_doc(tmp_path, "architecture.md", content, artifact_id="architecture")

        result = validate_docs(tmp_path, model, SAMPLE_MANIFEST)

        assert result.is_valid is True
        assert result.passed == 1
        assert result.failed == 0
        # No errors at all
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) == 0


class TestValidateDocsNoManifest:
    """When manifest is None, skip path/function checks, only do model checks."""

    def test_no_manifest_skips_file_checks(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        # Reference a path that doesn't exist — but no manifest, so no error
        content = "# Doc\n\nSee `src/nonexistent.py` for details.\n"
        _write_doc(tmp_path, "doc.md", content, artifact_id="doc")

        result = validate_docs(tmp_path, model, manifest=None)

        # Should pass since we can't verify paths without manifest
        path_errors = [i for i in result.issues if i.issue_type == "invalid_path"]
        assert len(path_errors) == 0

    def test_no_manifest_still_checks_components(self, tmp_path):
        from opencode_arch.cli.docs_validator import validate_docs

        model = _make_model()
        content = "# Doc\n\n`COMP-999` is referenced.\n"
        _write_doc(tmp_path, "doc.md", content, artifact_id="doc")

        result = validate_docs(tmp_path, model, manifest=None)

        # Component check still works
        assert result.is_valid is False
        assert any(i.issue_type == "unknown_component" for i in result.issues)


class TestArtifactIdExtraction:
    """Test _get_artifact_id_from_file extracts from frontmatter or filename."""

    def test_from_frontmatter(self, tmp_path):
        from opencode_arch.cli.docs_validator import _get_artifact_id_from_file

        doc = "---\nartifact_id: system-overview\n---\n# Content\n"
        filepath = tmp_path / "something.md"
        filepath.write_text(doc)

        assert _get_artifact_id_from_file(filepath) == "system-overview"

    def test_fallback_to_filename(self, tmp_path):
        from opencode_arch.cli.docs_validator import _get_artifact_id_from_file

        doc = "# Content without frontmatter\n"
        filepath = tmp_path / "api-reference.md"
        filepath.write_text(doc)

        assert _get_artifact_id_from_file(filepath) == "api-reference"

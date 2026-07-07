"""Tests for rich dependency context in blind regen prompts."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _make_subsystem(name: str, source_files: list, dependencies: list):
    """Create a mock subsystem with given deps."""
    sub = MagicMock()
    sub.name = name
    sub.source_files = [Path(f) for f in source_files]
    sub.dependencies = dependencies
    return sub


def test_dependency_context_includes_signatures(tmp_path):
    """Dependency context should include function signatures from upstream."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    # Create a minimal model file with a component that has signatures
    model_yaml = tmp_path / ".architecture-model.yaml"
    model_yaml.write_text("""\
meta:
  project: test
  schema_version: '1.4'
entities:
  components:
    - id: comp-utils
      name: utils
      status: ACTIVE
      kind: module
      files: ["mylib/utils.py"]
      signatures:
        - name: format_value
          params: ["x: Any", "precision: int = 2"]
          returns: "str"
          body_hint: "return f'{x:.{precision}f}'"
        - name: validate
          params: ["data: dict"]
          returns: "bool"
      constants:
        - name: MAX_SIZE
          value: "1024"
          type: int
    - id: comp-core
      name: core
      status: ACTIVE
      kind: module
      files: ["mylib/core.py"]
      signatures:
        - name: process
          params: ["items: list"]
          returns: "list"
relationships: []
""")

    subsystem = _make_subsystem(
        name="stdlib",
        source_files=["mylib/stdlib.py"],
        dependencies=["utils"],
    )

    context = _build_dependency_context(subsystem, tmp_path)

    # Should include function signatures
    assert "format_value" in context
    assert "validate" in context
    # Should include constants
    assert "MAX_SIZE" in context
    assert "1024" in context
    # Should NOT include unrelated subsystem (core)
    assert "process" not in context


def test_dependency_context_includes_class_info(tmp_path):
    """Dependency context should include class names and members."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    model_yaml = tmp_path / ".architecture-model.yaml"
    model_yaml.write_text("""\
meta:
  project: test
  schema_version: '1.4'
entities:
  components:
    - id: comp-base
      name: _base
      status: ACTIVE
      kind: module
      files: ["structlog/_base.py"]
      symbols:
        - name: BoundLoggerBase
          kind: class
          supers: ["object"]
          members: ["bind", "unbind", "try_unbind", "new", "_logger"]
      signatures:
        - name: get_context
          params: ["self"]
          returns: "dict[str, Any]"
      constants: []
relationships: []
""")

    subsystem = _make_subsystem(
        name="stdlib",
        source_files=["structlog/stdlib.py"],
        dependencies=["_base"],
    )

    context = _build_dependency_context(subsystem, tmp_path)

    assert "BoundLoggerBase" in context
    assert "bind" in context
    assert "get_context" in context


def test_dependency_context_empty_when_no_deps(tmp_path):
    """No dependencies should produce empty string."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    subsystem = _make_subsystem(
        name="utils",
        source_files=["mylib/utils.py"],
        dependencies=[],
    )

    context = _build_dependency_context(subsystem, tmp_path)
    assert context == ""


def test_dependency_context_fallback_without_model(tmp_path):
    """Without model file, should still list dependency names."""
    from opencode_arch.cli.regen_loop import _build_dependency_context

    subsystem = _make_subsystem(
        name="core",
        source_files=["mylib/core.py"],
        dependencies=["utils", "config"],
    )

    context = _build_dependency_context(subsystem, tmp_path)

    # Should at least mention the dependency names
    assert "utils" in context
    assert "config" in context

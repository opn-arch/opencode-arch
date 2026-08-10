"""Tests for spot-check regeneration probe and MCP tools."""
from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

import pytest

from opencode_arch.regen.spot_check import (
    SpotCheckDiagnostic,
    SpotCheckResult,
    SpotCheckTarget,
    _parse_generated_code,
    _structural_similarity,
    run_spot_check,
    select_target,
)
from opencode_arch.regen.self_heal import HealAction, classify_failure


@pytest.fixture
def simple_model_dir(tmp_path):
    """Create a minimal architecture model for testing."""
    model_yaml = textwrap.dedent("""\
        meta:
          project: test-project
          schema_version: '2.0'
        entities:
          components:
            - id: COMP-1
              name: MyWidget
              status: ACTIVE
              files:
                - src/widget.py
              signatures:
                - name: do_thing
                  params: [x, y]
                  returns: int
                  body_hint: "return x + y"
              constants:
                - name: MAX_SIZE
                  value: "100"
              test_contracts:
                - test_method: test_do_thing
                  assertion: "do_thing(1, 2) == 3"
          capabilities: []
        relationships: []
    """)
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
    # Create source file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "widget.py").write_text(textwrap.dedent("""\
        MAX_SIZE = 100

        def do_thing(x, y):
            return x + y

        class Widget:
            pass
    """))
    return tmp_path


def test_select_target_specific_component(simple_model_dir):
    """Passes component_id, gets correct target."""
    target = asyncio.run(select_target(simple_model_dir, component_id="COMP-1"))
    assert target.component_id == "COMP-1"
    assert "src/widget.py" in target.files
    assert "Regenerate: MyWidget" in target.model_context


def test_spot_check_dry_run(simple_model_dir):
    """No LLM backend → dry-run result."""
    target = SpotCheckTarget(
        component_id="COMP-1",
        files=["src/widget.py"],
        model_context="# test",
    )
    result = asyncio.run(run_spot_check(target, simple_model_dir))
    assert not result.success
    assert result.iterations == 0
    assert result.diagnostics[0].category == "TEST_INFRA"
    assert "Dry run" in result.diagnostics[0].message


def test_classify_failure_missing_impl():
    """MISSING_IMPL diagnostic → add_body_hint action."""
    diagnostics = [
        SpotCheckDiagnostic(
            category="MISSING_IMPL",
            severity="critical",
            message="No generated code for src/widget.py",
            function_name="do_thing",
        )
    ]
    actions = classify_failure(diagnostics)
    assert len(actions) == 1
    assert actions[0].pattern == "MISSING_IMPL"
    assert actions[0].action == "add_body_hint"
    assert actions[0].target == "do_thing"


def test_structural_similarity_identical():
    """Same code → 100%."""
    code = textwrap.dedent("""\
        def foo():
            pass

        def bar():
            pass

        class Baz:
            pass
    """)
    assert _structural_similarity(code, code) == 100.0


def test_structural_similarity_partial():
    """Some functions missing → <100%."""
    actual = textwrap.dedent("""\
        def foo():
            pass

        def bar():
            pass

        class Baz:
            pass
    """)
    generated = textwrap.dedent("""\
        def foo():
            pass

        class Baz:
            pass
    """)
    sim = _structural_similarity(actual, generated)
    # 2 out of 3 names match → ~66.7%
    assert 60.0 < sim < 70.0


def test_parse_generated_code():
    """Parse fenced code blocks with filenames."""
    raw = textwrap.dedent("""\
        Here is the code:
        ```python src/widget.py
        def foo():
            return 1
        ```
    """)
    files = _parse_generated_code(raw)
    assert "src/widget.py" in files
    assert "def foo():" in files["src/widget.py"]


def test_regen_score_mcp_tool_no_model(tmp_path):
    """regen_score returns error when no model exists."""
    from opencode_arch.mcp.tools.regen_score import regen_score
    
    result = asyncio.run(regen_score(repo_path=str(tmp_path)))
    assert "error" in result

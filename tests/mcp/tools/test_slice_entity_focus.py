"""Phase 3 Task 19 — architect_slice accepts focus='entity(<id>)'.

The slice tool must accept the entity-focus scope form and route it
through ``architecture_model.core.slicer.slice_by_entity`` so the
returned context is limited to the entity plus its 1-hop neighborhood.
Unrelated entities must not appear in the compressed context.
"""

from __future__ import annotations

import asyncio
import textwrap

from opencode_arch.mcp.tools.slice import slice_context


def _run(coro):
    return asyncio.run(coro)


def _write_model(tmp_path):
    model_yaml = textwrap.dedent(
        """\
        meta:
          project: entity-focus-fixture
          schema_version: '2.1'
        entities:
          components:
            - id: COMP-1
              name: Focused
              status: ACTIVE
            - id: COMP-2
              name: Neighbor
              status: ACTIVE
            - id: COMP-99
              name: Unrelated
              status: ACTIVE
          capabilities:
            - id: CAP-F1
              name: FocusedCap
              status: ACTIVE
        relationships:
          - from: COMP-1
            to: CAP-F1
            type: realizes
          - from: COMP-1
            to: COMP-2
            type: depends-on
        """
    )
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)


def test_architect_slice_entity_focus_includes_target(tmp_path):
    _write_model(tmp_path)
    result = _run(slice_context(str(tmp_path), focus="entity(COMP-1)", budget=4000))
    assert isinstance(result, str)
    assert "COMP-1" in result


def test_architect_slice_entity_focus_excludes_unrelated(tmp_path):
    _write_model(tmp_path)
    result = _run(slice_context(str(tmp_path), focus="entity(COMP-1)", budget=4000))
    # COMP-99 has no relationship path to COMP-1 → must be pruned.
    assert "COMP-99" not in result


def test_architect_slice_entity_focus_unknown_entity_falls_back(tmp_path):
    _write_model(tmp_path)
    # Unknown entity id must not raise — falls back gracefully (full model or error string).
    result = _run(slice_context(str(tmp_path), focus="entity(DOES-NOT-EXIST)", budget=4000))
    assert isinstance(result, str)
    assert result  # non-empty

"""Phase 3 Task 21 — architect_evaluate emits drill-down link map.

The envelope grows a ``drilldowns`` key mapping ``entity_id`` to the
list of relative artifact paths (family1/COMP-1.md, family3/COMP-1.md,
...) discovered under ``.architecture/lifecycle/artifacts/entity_pages/``.
Only entities with at least one generated page appear.
"""

from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.evaluate import evaluate_workspace


def _run(coro):
    return asyncio.run(coro)


def test_evaluate_envelope_includes_empty_drilldowns_when_no_pages(tmp_path):
    result = _run(evaluate_workspace(str(tmp_path), force_refresh=True))
    assert "drilldowns" in result
    assert result["drilldowns"] == {}


def test_evaluate_drilldowns_maps_entities_to_relative_urls(tmp_path):
    ep_root = tmp_path / ".architecture" / "lifecycle" / "artifacts" / "entity_pages"
    (ep_root / "family1").mkdir(parents=True)
    (ep_root / "family3").mkdir(parents=True)
    (ep_root / "family1" / "COMP-1.md").write_text("# Alpha\n")
    (ep_root / "family3" / "COMP-1.md").write_text("# Alpha (logical)\n")
    (ep_root / "family1" / "CAP-F1.md").write_text("# Cap\n")

    result = _run(evaluate_workspace(str(tmp_path), force_refresh=True))
    drill = result["drilldowns"]

    assert set(drill.keys()) == {"COMP-1", "CAP-F1"}
    # URLs are relative to entity_pages/ and sorted for determinism.
    assert drill["COMP-1"] == ["family1/COMP-1.md", "family3/COMP-1.md"]
    assert drill["CAP-F1"] == ["family1/CAP-F1.md"]


def test_evaluate_drilldowns_ignores_non_md_and_unknown_dirs(tmp_path):
    ep_root = tmp_path / ".architecture" / "lifecycle" / "artifacts" / "entity_pages"
    (ep_root / "family1").mkdir(parents=True)
    (ep_root / "family1" / "COMP-1.md").write_text("body")
    # noise: non-family subdir + non-md file
    (ep_root / "notes").mkdir()
    (ep_root / "notes" / "README.txt").write_text("x")
    (ep_root / "family1" / "index.txt").write_text("x")

    result = _run(evaluate_workspace(str(tmp_path), force_refresh=True))
    assert result["drilldowns"] == {"COMP-1": ["family1/COMP-1.md"]}

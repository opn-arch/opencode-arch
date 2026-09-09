"""Verification tests for scope='descendants:each' per-subsystem fan-out.

Phase 2 Task 27 adds per-subsystem fan-out ALONGSIDE the Phase 1
merged-fragment path. See ``test_rebuild_descendants.py`` for the
merged-fragment regression suite; this file locks in fan-out
semantics:

* One ``ArtifactSpec`` with ``scope='descendants:each'`` produces
  N artifacts (root + one per descendant).
* Each artifact's ``spec_id`` is namespaced ``<orig>.<sub_slug>`` so
  output paths do not collide across descendants.
* Each artifact's fragment contains ONLY that descendant's entities
  (no merge across descendants).
* The Phase 1 merged-fragment path (``scope='descendants'``) is not
  affected — see ``test_descendants_scope_merges_child_models``.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool


ROOT_MODEL_YAML = """\
meta:
  project: root
  schema_version: '2.0'
entities:
  components:
    - id: COMP-ROOT
      name: Root
      status: ACTIVE
relationships: []
"""


CHILD_A_YAML = """\
meta:
  project: child-a
  schema_version: '2.0'
entities:
  components:
    - id: COMP-A
      name: ChildA
      status: ACTIVE
relationships: []
"""


CHILD_B_YAML = """\
meta:
  project: child-b
  schema_version: '2.0'
entities:
  components:
    - id: COMP-B
      name: ChildB
      status: ACTIVE
relationships: []
"""


def _run(coro):
    return asyncio.run(coro)


def _publish_root(repo: Path) -> None:
    env = _run(publish_package_tool(repo_path=str(repo), model_yaml=ROOT_MODEL_YAML))
    assert env["ok"], env


def _lifecycle(repo: Path) -> Path:
    return repo / ".architecture" / "lifecycle"


def _current_gen(repo: Path) -> Path:
    return (_lifecycle(repo) / "CURRENT").resolve()


def _make_child(repo: Path, slug: str, arch_id: str, model_yaml: str) -> None:
    from architecture_model.lifecycle.versions import SchemaVersions

    child_dir = _current_gen(repo) / slug
    child_dir.mkdir(parents=True, exist_ok=True)
    (child_dir / ".architecture-model.yaml").write_text(model_yaml, encoding="utf-8")
    (child_dir / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "architecture_id": arch_id,
                "name": arch_id,
                "slug": arch_id,
                "contract_version": SchemaVersions.PACKAGE,
                "model_ref": ".architecture-model.yaml",
                "manifest_ref": "manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    root_pkg_yaml = _lifecycle(repo) / "package.yaml"
    data = yaml.safe_load(root_pkg_yaml.read_text(encoding="utf-8"))
    children = list(data.get("children") or [])
    child_rel = f"{slug}/package.yaml"
    if child_rel not in children:
        children.append(child_rel)
    data["children"] = children
    root_pkg_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


@pytest.fixture
def capturing_projector():
    """Register a projector that records per-call the fragment's component ids."""
    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    captured: dict = {"calls": []}

    def proj(fragment, config):
        comps = list(getattr(fragment.entities, "components", []) or [])
        captured["calls"].append(sorted(c.id for c in comps))
        return DiagramSpec(id="cap", title="Capturing view")

    DEFAULT_REGISTRY.register("t.capture_fanout", proj, version="1.0.0")
    try:
        yield captured
    finally:
        DEFAULT_REGISTRY.unregister("t.capture_fanout")


def _slice(scope: str) -> dict:
    return {
        "id": "slice-1",
        "architecture_id": "root-pkg",
        "model_revision": "0000001",
        "scope": scope,
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["components"]},
    }


def _view() -> dict:
    return {
        "id": "view-1",
        "slice_ref": {"slice_id": "slice-1", "model_revision": "0000001"},
        "projector": "t.capture_fanout",
        "output_content_kind": "diagram",
    }


def _artifact(spec_id: str = "art") -> dict:
    return {
        "id": spec_id,
        "renderer": "markdown",
        "view_ref": {"view_id": "view-1", "model_revision": "0000001"},
    }


def _rebuild(repo, arts, views, slices, **kw):
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts

    return rebuild_artifacts(repo, arts, views, slices, **kw)


# ------------------------------------------------------------------ fan-out


def test_fanout_produces_one_artifact_per_descendant(tmp_path, capturing_projector):
    """One spec + scope='descendants:each' yields root + N descendant artifacts."""
    _publish_root(tmp_path)
    _make_child(tmp_path, slug="child-a", arch_id="child-a", model_yaml=CHILD_A_YAML)
    _make_child(tmp_path, slug="child-b", arch_id="child-b", model_yaml=CHILD_B_YAML)

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants:each")],
    )
    assert report.failed == [], report.failed
    # 1 root + 2 descendants = 3 artifacts.
    assert len(report.built) == 3, [b["spec_id"] for b in report.built]

    spec_ids = sorted(b["spec_id"] for b in report.built)
    # Every spec_id starts with the original id and carries a slug suffix.
    for sid in spec_ids:
        assert sid.startswith("art."), sid
    # Each output_path carries the subsystem slug.
    output_paths = sorted(b["output_path"] for b in report.built)
    for p in output_paths:
        assert Path(p).name.startswith("art.")


def test_fanout_fragments_are_isolated_per_subsystem(tmp_path, capturing_projector):
    """Each render's fragment contains ONLY that subsystem's entities (no merge)."""
    _publish_root(tmp_path)
    _make_child(tmp_path, slug="child-a", arch_id="child-a", model_yaml=CHILD_A_YAML)
    _make_child(tmp_path, slug="child-b", arch_id="child-b", model_yaml=CHILD_B_YAML)

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants:each")],
    )
    assert report.failed == [], report.failed
    assert len(capturing_projector["calls"]) == 3

    # Each fragment is a single-package view (one component each — no merge).
    frag_ids = sorted(tuple(c) for c in capturing_projector["calls"])
    assert frag_ids == [("COMP-A",), ("COMP-B",), ("COMP-ROOT",)]


def test_fanout_no_children_yields_single_root_artifact(tmp_path, capturing_projector):
    """scope='descendants:each' with no children still renders root once."""
    _publish_root(tmp_path)

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants:each")],
    )
    assert report.failed == [], report.failed
    assert len(report.built) == 1
    assert capturing_projector["calls"] == [["COMP-ROOT"]]


def test_merged_fragment_scope_unaffected(tmp_path, capturing_projector):
    """Phase 1 scope='descendants' still returns one merged artifact."""
    _publish_root(tmp_path)
    _make_child(tmp_path, slug="child-a", arch_id="child-a", model_yaml=CHILD_A_YAML)

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants")],
    )
    assert report.failed == [], report.failed
    assert len(report.built) == 1
    # Fragment contains BOTH entities — merged, not fanned out.
    assert capturing_projector["calls"] == [["COMP-A", "COMP-ROOT"]]

"""Verification tests for scope='descendants' rebuild behavior (Phase 1, Task 13).

Phase 1 shipping semantics vs. plan intent — READ BEFORE EDITING
-----------------------------------------------------------------
Plan Task 13 originally asked for **per-subsystem fan-out**: enumerate
``iter_descendants(root_pkg, include_self=True)``, rebuild ONCE per
descendant, and emit N artifacts whose output paths carry a subsystem
slug (e.g. ``conops-a.md``, ``conops-b.md``). See
``docs/plans/2026-09-08-phase-1-substrate-and-liveness.md`` lines
1449–1528 in the AMS repo.

The Phase 1 shipping semantics are **merged-fragment**, NOT fan-out:

* ``materialize()`` (ams ``model_slice_materializer.py:184``) walks
  ``iter_descendants(pkg, include_self=False)`` and merges every
  descendant's entities into ONE fragment.
* ``rebuild_artifacts`` (oca ``lifecycle_exec/rebuild.py:210``) has
  no ``slice.scope`` awareness — it produces exactly one artifact per
  ``ArtifactSpec``, regardless of scope, at the fixed path
  ``<lifecycle>/artifacts/<spec_id>.<ext>``.

Merged-fragment answers "give me one architectural document that
spans the whole tree." Per-subsystem fan-out answers "give me one
document per M2 subsystem, addressable by slug." They are different
features. Phase 1 ships merged-fragment; per-subsystem fan-out is
deferred to Phase 2 (see the Phase 2 plan for the "Executor
per-subsystem fan-out" task).

**These tests lock in the merged-fragment path.** They are the
regression suite for that behavior. When fan-out lands in Phase 2 it
will introduce ADDITIONAL tests asserting ``len(report.built) == N``
and per-artifact fragment isolation; it should not modify these
assertions.

Fixture note
------------
Child packages are placed directly inside the CURRENT generation
directory (``.architecture/lifecycle/generations/0000001/<slug>/``)
because :func:`opencode_arch.lifecycle_bridge.resolve_current_pkg`
rebases the root package onto ``<lifecycle>/CURRENT/`` before
descendants are walked. We register children by editing the root
``package.yaml`` in-place rather than going through
``package_children_add_tool`` because that tool validates the child
path against ``<lifecycle>/<rel>`` (un-resolved), whereas ``rebuild``
resolves via ``<lifecycle>/CURRENT/<rel>``. Writing directly matches
what the merge path actually exercises without depending on the
authoring surface.
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


CHILD_MODEL_YAML = """\
meta:
  project: child
  schema_version: '2.0'
entities:
  components:
    - id: COMP-CHILD
      name: Child
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
    """Resolve the CURRENT-generation directory (a symlink target)."""
    return (_lifecycle(repo) / "CURRENT").resolve()


def _make_child(
    repo: Path,
    slug: str = "child",
    arch_id: str = "child-pkg",
    model_yaml: str = CHILD_MODEL_YAML,
) -> None:
    """Create + register a descendant package inside CURRENT generation.

    Layout produced:
        .architecture/lifecycle/generations/0000001/<slug>/package.yaml
        .architecture/lifecycle/generations/0000001/<slug>/.architecture-model.yaml

    Then appends ``<slug>/package.yaml`` to the root descriptor's
    ``children`` list in-place (see module docstring for why we bypass
    ``package_children_add_tool``).
    """
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

    # Register in root package.yaml (in-place, no tool validation).
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
    """Register a projector that records the fragment component ids it sees."""
    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    captured: dict = {"component_ids": None, "call_count": 0}

    def proj(fragment, config):
        captured["call_count"] += 1
        # ``fragment`` is an ArchitectureModel instance.
        comps = list(getattr(fragment.entities, "components", []) or [])
        captured["component_ids"] = sorted(c.id for c in comps)
        return DiagramSpec(id="cap", title="Capturing view")

    DEFAULT_REGISTRY.register("t.capture", proj, version="1.0.0")
    try:
        yield captured
    finally:
        DEFAULT_REGISTRY.unregister("t.capture")


def _slice(scope: str = "descendants") -> dict:
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
        "projector": "t.capture",
        "output_content_kind": "diagram",
    }


def _artifact(spec_id: str = "art-1") -> dict:
    return {
        "id": spec_id,
        "renderer": "markdown",
        "view_ref": {"view_id": "view-1", "model_revision": "0000001"},
    }


def _rebuild(repo, arts, views, slices, **kw):
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts

    return rebuild_artifacts(repo, arts, views, slices, **kw)


# ---------------------------------------------------------------- baselines


def test_local_scope_sees_only_root(tmp_path, capturing_projector):
    """Sanity: scope='local' does NOT pull in child entities.

    Anchors the semantics of the descendants tests below — the contrast
    between 'local' and 'descendants' is the entire point.
    """
    _publish_root(tmp_path)
    _make_child(tmp_path)

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="local")],
    )
    assert report.failed == [], report.failed
    assert len(report.built) == 1
    assert capturing_projector["component_ids"] == ["COMP-ROOT"]


# ---------------------------------------------------------------- descendants


def test_descendants_scope_merges_child_models(tmp_path, capturing_projector):
    """scope='descendants' merges every child package's model into fragment."""
    _publish_root(tmp_path)
    _make_child(tmp_path)

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants")],
    )
    assert report.failed == [], report.failed
    assert len(report.built) == 1
    # Fragment contains BOTH root + descendant entities.
    assert capturing_projector["component_ids"] == ["COMP-CHILD", "COMP-ROOT"]
    # One artifact => exactly one projector invocation (guards against
    # double-materialize regressions in the executor).
    assert capturing_projector["call_count"] == 1


def test_descendants_scope_no_children_is_not_error(tmp_path, capturing_projector):
    """scope='descendants' with zero registered children is a no-op, not an error.

    Boundary check only — the descendants merge loop degrades to a no-op
    here, so this test would still pass if ``iter_descendants`` were
    stubbed to return ``[]``. The real merge-semantics coverage lives in
    ``test_descendants_scope_merges_child_models`` and
    ``test_descendants_scope_multiple_children``.
    """
    _publish_root(tmp_path)  # no _make_child

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants")],
    )
    assert report.failed == [], report.failed
    assert capturing_projector["component_ids"] == ["COMP-ROOT"]


def test_descendants_scope_multiple_children(tmp_path, capturing_projector):
    """Every registered child contributes to the merged fragment."""
    _publish_root(tmp_path)
    _make_child(tmp_path, slug="a", arch_id="child-a")
    _make_child(
        tmp_path,
        slug="b",
        arch_id="child-b",
        model_yaml=CHILD_MODEL_YAML.replace("COMP-CHILD", "COMP-CHILD-B").replace(
            "name: Child", "name: ChildB"
        ),
    )

    report = _rebuild(
        tmp_path,
        [_artifact()],
        [_view()],
        [_slice(scope="descendants")],
    )
    assert report.failed == [], report.failed
    # Assertion is stable because the projector sorts by id — this does
    # NOT pin ``iter_descendants`` traversal order.
    assert capturing_projector["component_ids"] == [
        "COMP-CHILD",
        "COMP-CHILD-B",
        "COMP-ROOT",
    ]
    assert capturing_projector["call_count"] == 1

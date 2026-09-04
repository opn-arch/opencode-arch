"""Tests for opencode_arch.lifecycle_exec.rebuild (T11)."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool


MODEL_YAML = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-A
      name: A
      status: ACTIVE
    - id: COMP-B
      name: B
      status: ACTIVE
relationships:
  - from: COMP-A
    to: COMP-B
    type: depends-on
"""


def _run(coro):
    return asyncio.run(coro)


def _publish(repo: Path) -> None:
    env = _run(publish_package_tool(repo_path=str(repo), model_yaml=MODEL_YAML))
    assert env["ok"], env


@pytest.fixture
def stub_projector():
    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    def proj(fragment, config):
        return DiagramSpec(id="stub", title="Stub view")

    DEFAULT_REGISTRY.register("t.stub", proj, version="1.0.0")
    try:
        yield "t.stub"
    finally:
        DEFAULT_REGISTRY.unregister("t.stub")


def _slice(**overrides) -> dict:
    base = {
        "id": "slice-1",
        "architecture_id": "root-pkg",
        "model_revision": "0000001",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["components"]},
    }
    base.update(overrides)
    return base


def _view(projector="t.stub", **overrides) -> dict:
    base = {
        "id": "view-1",
        "slice_ref": {"slice_id": "slice-1", "model_revision": "0000001"},
        "projector": projector,
        "output_content_kind": "diagram",
    }
    base.update(overrides)
    return base


def _artifact(renderer="svg", spec_id="art-1", **overrides) -> dict:
    base = {
        "id": spec_id,
        "renderer": renderer,
        "view_ref": {"view_id": "view-1", "model_revision": "0000001"},
    }
    base.update(overrides)
    return base


def _rebuild(repo, arts, views, slices, **kw):
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts
    return rebuild_artifacts(repo, arts, views, slices, **kw)


# -------------------------------------------------------------------- happy


def test_happy_path_svg(tmp_path, stub_projector):
    _publish(tmp_path)
    report = _rebuild(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    assert report.failed == []
    assert report.skipped == []
    assert len(report.built) == 1
    entry = report.built[0]
    assert entry["spec_id"] == "art-1"
    assert entry["renderer"] == "svg"
    assert entry["emitted_digest"].startswith("sha256:")
    out = Path(entry["output_path"])
    assert out.exists()
    assert out.suffix == ".svg"
    assert entry["emitted_digest"] == "sha256:" + hashlib.sha256(out.read_bytes()).hexdigest()


def test_happy_path_two_artifacts_topological(tmp_path, stub_projector):
    _publish(tmp_path)
    arts = [_artifact("svg", "art-a"), _artifact("markdown", "art-b")]
    report = _rebuild(tmp_path, arts, [_view()], [_slice()])
    assert report.failed == []
    assert [b["spec_id"] for b in report.built] == ["art-a", "art-b"]
    exts = sorted(Path(b["output_path"]).suffix for b in report.built)
    assert exts == [".md", ".svg"]


def test_renderer_extensions(tmp_path, stub_projector):
    _publish(tmp_path)
    arts = [
        _artifact("svg", "a-svg"),
        _artifact("markdown", "a-md"),
        _artifact("html", "a-html"),
        _artifact("ai-context", "a-ai"),
    ]
    report = _rebuild(tmp_path, arts, [_view()], [_slice()])
    assert report.failed == [], report.failed
    ext_by_id = {b["spec_id"]: Path(b["output_path"]).suffix for b in report.built}
    assert ext_by_id == {
        "a-svg": ".svg",
        "a-md": ".md",
        "a-html": ".html",
        "a-ai": ".txt",
    }


# -------------------------------------------------------------------- skip / force


def test_skip_matching_digest(tmp_path, stub_projector):
    _publish(tmp_path)
    r1 = _rebuild(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    digest = r1.built[0]["emitted_digest"]
    art = _artifact("svg", parameters={"expected_digest": digest})
    r2 = _rebuild(tmp_path, [art], [_view()], [_slice()])
    assert r2.built == []
    assert len(r2.skipped) == 1
    assert r2.skipped[0]["reason"] == "up_to_date"
    assert r2.skipped[0]["spec_id"] == "art-1"


def test_force_rebuilds_when_matching(tmp_path, stub_projector):
    _publish(tmp_path)
    r1 = _rebuild(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    digest = r1.built[0]["emitted_digest"]
    art = _artifact("svg", parameters={"expected_digest": digest})
    r2 = _rebuild(tmp_path, [art], [_view()], [_slice()], force=True)
    assert r2.skipped == []
    assert len(r2.built) == 1


# -------------------------------------------------------------------- errors


def test_zip_renderer_unsupported(tmp_path, stub_projector):
    _publish(tmp_path)
    # A leaf svg plus a zip that bundles it.
    zip_spec = {"id": "z-1", "renderer": "zip", "bundle_refs": ["art-1"]}
    arts = [_artifact("svg"), zip_spec]
    report = _rebuild(tmp_path, arts, [_view()], [_slice()])
    zip_fail = [f for f in report.failed if f["spec_id"] == "z-1"]
    assert zip_fail and zip_fail[0]["reason"] == "zip_renderer_unsupported"


def test_unresolved_view_ref(tmp_path, stub_projector):
    _publish(tmp_path)
    report = _rebuild(tmp_path, [_artifact("svg")], [], [_slice()])
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "unresolved_view_ref"
    assert report.failed[0]["spec_id"] == "art-1"


def test_unresolved_slice_ref(tmp_path, stub_projector):
    _publish(tmp_path)
    report = _rebuild(tmp_path, [_artifact("svg")], [_view()], [])
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "unresolved_slice_ref"


def test_federated_slice_unsupported(tmp_path, stub_projector):
    _publish(tmp_path)
    fed = _slice(
        scope="federated",
        selectors={"entity_kinds": ["components"], "entity_ids": ["COMP-A"]},
    )
    report = _rebuild(tmp_path, [_artifact("svg")], [_view()], [fed])
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "federated_slice_unsupported"


def test_empty_artifact_specs(tmp_path):
    report = _rebuild(tmp_path, [], [_view()], [_slice()])
    assert report.built == []
    assert report.skipped == []
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "spec_parse_error"
    assert report.failed[0]["spec_id"] == "*"
    assert report.journal_events == []


def test_malformed_artifact_spec(tmp_path):
    bad = {"id": "art-1"}  # missing renderer
    report = _rebuild(tmp_path, [bad], [_view()], [_slice()])
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "spec_parse_error"
    assert report.failed[0]["spec_id"] == "*"
    assert report.journal_events == []


def test_duplicate_view_dag_error(tmp_path):
    v1 = _view()
    v2 = _view()  # same id + same model_revision
    report = _rebuild(tmp_path, [_artifact("svg")], [v1, v2], [_slice()])
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "dag_error"


def test_cycle_artifact_dag_error(tmp_path):
    z1 = {"id": "z-1", "renderer": "zip", "bundle_refs": ["z-2"]}
    z2 = {"id": "z-2", "renderer": "zip", "bundle_refs": ["z-1"]}
    report = _rebuild(tmp_path, [z1, z2], [_view()], [_slice()])
    assert len(report.failed) == 1
    assert report.failed[0]["reason"] == "dag_error"


def test_digest_mismatch_writes_pending(tmp_path, stub_projector):
    _publish(tmp_path)
    art = _artifact("svg", parameters={"expected_digest": "sha256:deadbeef"})
    report = _rebuild(tmp_path, [art], [_view()], [_slice()])
    assert report.built == []
    assert len(report.failed) == 1
    fail = report.failed[0]
    assert fail["reason"] == "digest_mismatch"
    assert fail["output_path"].endswith(".pending")
    pending = Path(fail["output_path"])
    assert pending.exists()
    final = pending.with_suffix("")  # strips ".pending"
    # final should NOT exist unless something else wrote it — we didn't rebuild
    assert not final.exists() or final.suffix != ".svg" or True
    # More precise: original path (without .pending) should not exist
    original = Path(str(pending)[:-len(".pending")])
    assert not original.exists()


def test_journal_events_ordered(tmp_path, stub_projector):
    _publish(tmp_path)
    r1 = _rebuild(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    digest = r1.built[0]["emitted_digest"]

    # Now: skip 'art-1', fail 'art-2' (unresolved view), build 'art-3'
    good = _artifact("svg", "art-1", parameters={"expected_digest": digest})
    bad_view = _artifact("markdown", "art-2")
    bad_view["view_ref"] = {"view_id": "missing", "model_revision": "0000001"}
    fresh = _artifact("html", "art-3")
    report = _rebuild(tmp_path, [good, bad_view, fresh], [_view()], [_slice()])

    kinds = [(e["kind"], e["spec_id"]) for e in report.journal_events]
    assert kinds == [
        ("artifact.skipped", "art-1"),
        ("artifact.failed", "art-2"),
        ("artifact.built", "art-3"),
    ]


def test_determinism(tmp_path, stub_projector):
    _publish(tmp_path)
    arts = [_artifact("svg", "a"), _artifact("markdown", "b")]
    fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    r1 = _rebuild(tmp_path, arts, [_view()], [_slice()], _now=lambda: fixed)
    # Clean output so second run rebuilds identically.
    for b in r1.built:
        Path(b["output_path"]).unlink()
    r2 = _rebuild(tmp_path, arts, [_view()], [_slice()], _now=lambda: fixed)
    assert [b["spec_id"] for b in r1.built] == [b["spec_id"] for b in r2.built]
    assert [b["emitted_digest"] for b in r1.built] == [
        b["emitted_digest"] for b in r2.built
    ]
    assert r1.journal_events == r2.journal_events


def test_timestamp_injection(tmp_path, stub_projector):
    _publish(tmp_path)
    fixed = datetime(2026, 6, 1, 12, 30, 45, tzinfo=timezone.utc)
    report = _rebuild(
        tmp_path, [_artifact("svg")], [_view()], [_slice()],
        _now=lambda: fixed,
    )
    assert report.journal_events[0]["timestamp"] == fixed.isoformat()


def test_repo_missing_raises_value_error(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError):
        _rebuild(missing, [_artifact("svg")], [_view()], [_slice()])


def test_report_to_dict(tmp_path, stub_projector):
    _publish(tmp_path)
    report = _rebuild(tmp_path, [_artifact("svg")], [_view()], [_slice()])
    d = report.to_dict()
    assert set(d.keys()) == {"built", "skipped", "failed", "journal_events"}
    assert isinstance(d["built"], list)

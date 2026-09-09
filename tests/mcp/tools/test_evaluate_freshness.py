"""Phase 1 Task 14 — architect_evaluate surfaces freshness_summary."""

from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.evaluate import evaluate_workspace


def _run(coro):
    return asyncio.run(coro)


def test_evaluate_reports_freshness_summary(tmp_path):
    (tmp_path / ".architecture-model.yaml").write_text(
        "meta: {project: t, schema_version: '1.3'}\nentities: {}\nrelationships: []\n"
    )
    (tmp_path / ".architecture" / "lifecycle" / "artifacts").mkdir(parents=True)
    result = _run(evaluate_workspace(repo_path=str(tmp_path), force_refresh=True))
    assert "freshness_summary" in result
    assert set(result["freshness_summary"].keys()) >= {"fresh", "stale", "pending", "total"}
    assert result["freshness_summary"]["total"] == 0


def test_evaluate_freshness_counts_present_artifacts(tmp_path):
    artifacts = tmp_path / ".architecture" / "lifecycle" / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "foo.md").write_text("# foo\n")
    (artifacts / "bar.html").write_text("<html></html>")
    result = _run(evaluate_workspace(repo_path=str(tmp_path), force_refresh=True))
    fs = result["freshness_summary"]
    assert fs["total"] == 2
    # Phase 1: no persisted provenance yet — everything falls in unknown.
    assert fs["unknown"] == 2
    assert fs["fresh"] == 0
    assert fs["stale"] == 0
    assert fs["pending"] == 0


def test_evaluate_freshness_missing_artifacts_dir(tmp_path):
    # No .architecture/lifecycle/artifacts/ at all — must not raise.
    result = _run(evaluate_workspace(repo_path=str(tmp_path), force_refresh=True))
    assert "freshness_summary" in result
    fs = result["freshness_summary"]
    assert fs == {"fresh": 0, "stale": 0, "pending": 0, "unknown": 0, "total": 0}


def test_evaluate_freshness_ignores_subdirectories(tmp_path):
    """Renderer-created subdirs (e.g. pipeline-html ``assets/``) don't count.

    Locks in the ``is_file()`` guard so a future maintainer doesn't turn it
    into a recursive walk.
    """
    artifacts = tmp_path / ".architecture" / "lifecycle" / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "pipeline.html").write_text("<html></html>")
    assets = artifacts / "assets"
    assets.mkdir()
    (assets / "styles.css").write_text("body{}")
    (assets / "badges.js").write_text("// badges")
    result = _run(evaluate_workspace(repo_path=str(tmp_path), force_refresh=True))
    fs = result["freshness_summary"]
    # Only the top-level file counts; asset children are ignored.
    assert fs["total"] == 1
    assert fs["unknown"] == 1


# ---------------------------------------------------------- Phase 2 Task 28


def test_evaluate_freshness_reads_provenance_sidecar(tmp_path):
    """Sidecar with ``freshness: fresh`` buckets the parent as fresh."""
    import json

    artifacts = tmp_path / ".architecture" / "lifecycle" / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "foo.md").write_text("# foo\n")
    (artifacts / "foo.md.provenance.json").write_text(
        json.dumps({"freshness": "fresh", "revision": "0000001"})
    )
    (artifacts / "bar.md").write_text("# bar\n")
    (artifacts / "bar.md.provenance.json").write_text(
        json.dumps({"freshness": "stale", "revision": "0000001"})
    )
    (artifacts / "baz.md").write_text("# baz\n")  # no sidecar
    result = _run(evaluate_workspace(repo_path=str(tmp_path), force_refresh=True))
    fs = result["freshness_summary"]
    assert fs["total"] == 3  # sidecars themselves excluded from total
    assert fs["fresh"] == 1
    assert fs["stale"] == 1
    assert fs["unknown"] == 1
    assert fs["pending"] == 0


def test_evaluate_freshness_after_real_rebuild(tmp_path):
    """End-to-end: rebuild produces sidecars → evaluate reports fresh."""
    import asyncio

    import yaml

    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.versions import SchemaVersions
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts
    from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool

    # Init root package.yaml (this test lives outside tests/lifecycle_exec/
    # which has an autouse conftest fixture for this).
    lifecycle = tmp_path / ".architecture" / "lifecycle"
    lifecycle.mkdir(parents=True, exist_ok=True)
    (lifecycle / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "architecture_id": "root-pkg",
                "name": "root-pkg",
                "slug": "root-pkg",
                "contract_version": SchemaVersions.PACKAGE,
                "model_ref": "model/.architecture-model.yaml",
                "manifest_ref": "manifest/manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    model_yaml = (
        "meta:\n  project: t\n  schema_version: '2.0'\n"
        "entities:\n  components:\n    - id: COMP-1\n      name: C\n      status: ACTIVE\n"
        "relationships: []\n"
    )
    env = asyncio.run(
        publish_package_tool(repo_path=str(tmp_path), model_yaml=model_yaml)
    )
    assert env["ok"], env

    def proj(fragment, config):
        return DiagramSpec(id="d", title="D")

    DEFAULT_REGISTRY.register("t.eval_fresh", proj, version="1.0.0")
    try:
        report = rebuild_artifacts(
            tmp_path,
            [
                {
                    "id": "art",
                    "renderer": "markdown",
                    "view_ref": {"view_id": "v", "model_revision": "0000001"},
                }
            ],
            [
                {
                    "id": "v",
                    "slice_ref": {"slice_id": "s", "model_revision": "0000001"},
                    "projector": "t.eval_fresh",
                    "output_content_kind": "diagram",
                }
            ],
            [
                {
                    "id": "s",
                    "architecture_id": "root-pkg",
                    "model_revision": "0000001",
                    "scope": "local",
                    "closure": "strict",
                    "shared_refs": "none",
                    "selectors": {"entity_kinds": ["components"]},
                }
            ],
        )
    finally:
        DEFAULT_REGISTRY.unregister("t.eval_fresh")

    assert report.failed == [], report.failed
    assert len(report.built) == 1

    # Sidecar should exist next to art.md.
    artifacts_dir = tmp_path / ".architecture" / "lifecycle" / "artifacts"
    assert (artifacts_dir / "art.md").exists()
    assert (artifacts_dir / "art.md.provenance.json").exists()

    result = _run(evaluate_workspace(repo_path=str(tmp_path), force_refresh=True))
    fs = result["freshness_summary"]
    # Sidecar is excluded from the top-level count; artifact bucketed as fresh.
    assert fs["total"] == 1, fs
    assert fs["fresh"] >= 1, fs

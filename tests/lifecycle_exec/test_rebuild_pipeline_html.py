"""E2E: architect_artifact_rebuild → pipeline.html on disk (DoD step 5).

The ``pipeline-html`` renderer has an incompatible signature
(``(*, materialized_slice, sil_store=None) -> str``) and is dispatched via
a special-case branch in :func:`rebuild_artifacts`. This test drives the
full T11 executor with a ``pipeline-html`` artifact spec and asserts:

* the HTML file lands at ``<repo>/.architecture/lifecycle/artifacts/<id>.html``
* the file contains the ``<script id="pipeline-state">`` payload
* the static asset tree is mirrored next to the HTML (index.css, badges.js,
  drilldown.js) so ``<link>`` / ``<script>`` tags resolve via ``file://``
* rebuilding is deterministic (byte-identical HTML on the second run)
* an ``artifact.built`` journal event is recorded
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts
from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool


_MODEL_YAML = """\
meta:
  project: pipeline-html-e2e
  schema_version: '2.0'
entities:
  components:
    - id: COMP-COLLECTOR
      name: Collector
      status: ACTIVE
    - id: COMP-BUILDER
      name: Builder
      status: ACTIVE
    - id: COMP-VIEWER
      name: Viewer
      status: ACTIVE
relationships:
  - from: COMP-COLLECTOR
    to: COMP-BUILDER
    type: depends-on
  - from: COMP-BUILDER
    to: COMP-VIEWER
    type: depends-on
"""


def _publish(repo: Path) -> None:
    env = asyncio.run(publish_package_tool(repo_path=str(repo), model_yaml=_MODEL_YAML))
    assert env["ok"], env


def _slice() -> dict:
    return {
        "id": "slice-pipeline",
        "architecture_id": "root-pkg",
        "model_revision": "0000001",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["components"]},
    }


def _view() -> dict:
    return {
        "id": "view-pipeline",
        "slice_ref": {"slice_id": "slice-pipeline", "model_revision": "0000001"},
        # pipeline-html renderer skips projection; projector value is inert.
        "projector": "pipeline_html_data",
        "output_content_kind": "diagram",
    }


def _artifact() -> dict:
    return {
        "id": "pipeline",
        "renderer": "pipeline-html",
        "view_ref": {"view_id": "view-pipeline", "model_revision": "0000001"},
    }


# --------------------------------------------------------------------- tests


def test_rebuild_emits_pipeline_html_and_assets(tmp_path):
    _publish(tmp_path)
    report = rebuild_artifacts(tmp_path, [_artifact()], [_view()], [_slice()])

    assert report.failed == [], report.failed
    assert report.skipped == []
    assert len(report.built) == 1

    entry = report.built[0]
    assert entry["spec_id"] == "pipeline"
    assert entry["renderer"] == "pipeline-html"
    assert entry["emitted_digest"].startswith("sha256:")

    html_path = Path(entry["output_path"])
    assert html_path.exists()
    assert html_path.suffix == ".html"
    assert html_path.name == "pipeline.html"

    html = html_path.read_text(encoding="utf-8")
    assert '<script id="pipeline-state"' in html
    assert '<link rel="stylesheet" href="assets/pipeline_dashboard/index.css">' in html
    assert '<script src="assets/pipeline_dashboard/badges.js"' in html

    # embedded JSON payload lists all three components
    start = html.index('<script id="pipeline-state"')
    open_end = html.index(">", start) + 1
    close = html.index("</script>", open_end)
    payload = json.loads(html[open_end:close].strip())
    node_ids = {n["id"] for n in payload["nodes"]}
    assert {"COMP-COLLECTOR", "COMP-BUILDER", "COMP-VIEWER"} <= node_ids
    # no SIL store → empty badges
    assert payload["badges"] == {}

    # assets mirrored next to the HTML
    assets_dir = html_path.parent / "assets" / "pipeline_dashboard"
    assert assets_dir.is_dir()
    for name in ("index.css", "badges.js", "drilldown.js"):
        f = assets_dir / name
        assert f.is_file(), f"missing asset: {f}"
        assert f.stat().st_size > 0

    # journal event recorded
    kinds = [ev["kind"] for ev in report.journal_events]
    assert "artifact.built" in kinds


def test_rebuild_pipeline_html_is_deterministic(tmp_path):
    _publish(tmp_path)
    r1 = rebuild_artifacts(tmp_path, [_artifact()], [_view()], [_slice()])
    digest_1 = r1.built[0]["emitted_digest"]
    bytes_1 = Path(r1.built[0]["output_path"]).read_bytes()

    r2 = rebuild_artifacts(
        tmp_path, [_artifact()], [_view()], [_slice()], force=True
    )
    digest_2 = r2.built[0]["emitted_digest"]
    bytes_2 = Path(r2.built[0]["output_path"]).read_bytes()

    assert digest_1 == digest_2
    assert bytes_1 == bytes_2

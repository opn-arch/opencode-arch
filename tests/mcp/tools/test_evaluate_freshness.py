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

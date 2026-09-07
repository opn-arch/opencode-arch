"""DoD step 4 — end-to-end: bind OCA SILStore, run AMS pipeline against
``tests/fixtures/sil/tiny_repo/`` (in the sibling repo), then invoke
``architect_component_health`` and verify a real stage record surfaces.

Skips gracefully when the sibling AMS repo is not present.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.component_health import component_health_tool
from opencode_arch.sil.store import SILStore


# Sibling AMS repo relative to workspace root (mirrors tests/e2e/conftest.py's
# PROJECT_DIR convention: workspace/architecture-model-standard).
_AMS_REPO = Path(__file__).resolve().parents[2].parent / "architecture-model-standard"
_TINY_REPO = _AMS_REPO / "tests" / "fixtures" / "sil" / "tiny_repo"


def _run(coro):
    return asyncio.run(coro)


def _run_ams_pipeline(repo: Path, output_dir: Path) -> None:
    """Import + drive the AMS pipeline stages in-process."""
    from architecture_model.pipeline.allocate import AllocateStage
    from architecture_model.pipeline.contract import ContractStage
    from architecture_model.pipeline.coordinator import PipelineCoordinator
    from architecture_model.pipeline.infer import InferStage
    from architecture_model.pipeline.observe import ObserveStage
    from architecture_model.pipeline.protocol import PipelineContext
    from architecture_model.pipeline.relate import RelateStage
    from architecture_model.pipeline.specify import SpecifyStage

    ctx = PipelineContext(repo_path=repo, output_dir=output_dir)
    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
    }
    PipelineCoordinator(stages).run_all(ctx)


def test_component_health_reflects_real_pipeline_run(tmp_path):
    """Bind OCA SILStore, run AMS pipeline on tiny_repo, query health tool."""
    if not _TINY_REPO.exists():
        pytest.skip(f"sibling tiny_repo fixture missing: {_TINY_REPO}")

    # Stage the sibling repo under tmp_path so the health tool can locate the
    # conventional .architecture/sil.sqlite alongside it.
    import shutil

    workdir = tmp_path / "repo"
    shutil.copytree(_TINY_REPO, workdir)
    sil_dir = workdir / ".architecture"
    sil_dir.mkdir(exist_ok=True)
    db_path = sil_dir / "sil.sqlite"

    # Bind the SQLite-backed store into the AMS decorator plumbing, run the
    # pipeline, then unbind so we don't leak across tests.
    from architecture_model.sil.decorators import bind_store

    store = SILStore(db_path)
    bind_store(store)
    try:
        _run_ams_pipeline(workdir, tmp_path / ".arch")
    finally:
        bind_store(None)

    # Query the health tool for one of the stages we know got instrumented.
    result = _run(
        component_health_tool(repo_path=str(workdir), component_id="stage:observe")
    )

    assert result["ok"] is True, result
    record = result["record"]
    assert record["component_id"] == "stage:observe"
    assert record["kind"] == "runtime-component"
    assert record["metrics"]["invocations_7d"] >= 1
    assert 0.0 <= record["metrics"]["failure_rate_7d"] <= 1.0
    assert record["metrics"]["avg_duration_ms"] >= 0
    assert len(record["recent_events"]) >= 1

    ev = record["recent_events"][0]
    assert ev["kind"] == "invocation"
    assert ev["outcome"] == "ok"

    trend = result["trend"]
    assert trend["invocations_7d"] == record["metrics"]["invocations_7d"]


def test_component_health_missing_component_returns_not_found_after_run(tmp_path):
    """Sanity: querying an unknown component_id after a real run still returns NOT_FOUND."""
    if not _TINY_REPO.exists():
        pytest.skip(f"sibling tiny_repo fixture missing: {_TINY_REPO}")

    import shutil

    workdir = tmp_path / "repo"
    shutil.copytree(_TINY_REPO, workdir)
    sil_dir = workdir / ".architecture"
    sil_dir.mkdir(exist_ok=True)
    db_path = sil_dir / "sil.sqlite"

    from architecture_model.sil.decorators import bind_store

    store = SILStore(db_path)
    bind_store(store)
    try:
        _run_ams_pipeline(workdir, tmp_path / ".arch")
    finally:
        bind_store(None)

    result = _run(
        component_health_tool(
            repo_path=str(workdir), component_id="stage:definitely-not-a-stage"
        )
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "NOT_FOUND"

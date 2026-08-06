"""Tests for D1 (pipeline dict) and D3 (model snapshots) in store_extraction."""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from opencode_arch.mcp.tools.extract import store_extraction


MINIMAL_MODEL = """
meta:
  project: test-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Core
      status: ACTIVE
relationships:
  - from: COMP-1
    to: COMP-1
    type: depends_on
"""


class TestPipelineDict:
    """D1: store_extraction returns a pipeline dict with step statuses."""

    @pytest.mark.asyncio
    async def test_successful_extraction_has_pipeline(self):
        """Successful extraction → result has pipeline key with step statuses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            assert result["stored"] is True
            assert "pipeline" in result
            pipeline = result["pipeline"]
            # All steps should have a status
            for step_name, step_info in pipeline.items():
                assert "status" in step_info, f"Step {step_name} missing status"
                assert step_info["status"] in ("ok", "error"), f"Step {step_name} has invalid status"

    @pytest.mark.asyncio
    async def test_missing_dependency_shows_error(self):
        """If a step dependency fails, that step shows 'error' but others still run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch telemetry to fail
            with patch("opencode_arch.mcp.tools.extract._get_telemetry_store", side_effect=RuntimeError("db broken")):
                result = await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            assert result["stored"] is True
            assert result["pipeline"]["telemetry"]["status"] == "error"
            assert "db broken" in result["pipeline"]["telemetry"]["error"]

    @pytest.mark.asyncio
    async def test_warnings_key_always_present(self):
        """warnings key is always present (may be empty list)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            assert "warnings" in result
            assert isinstance(result["warnings"], list)


class TestModelSnapshots:
    """D3: model snapshots before overwrite."""

    @pytest.mark.asyncio
    async def test_first_extraction_no_snapshot(self):
        """First extraction → no snapshot created (no prior model)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            assert result["stored"] is True
            snapshot_dir = Path(tmpdir) / ".architecture" / "snapshots"
            if snapshot_dir.exists():
                assert len(list(snapshot_dir.glob("*.yaml"))) == 0

    @pytest.mark.asyncio
    async def test_second_extraction_creates_snapshot(self):
        """Second extraction → snapshot of first model exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            # Second extraction
            await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            snapshot_dir = Path(tmpdir) / ".architecture" / "snapshots"
            assert snapshot_dir.exists()
            snapshots = list(snapshot_dir.glob("*.yaml"))
            assert len(snapshots) == 1

    @pytest.mark.asyncio
    async def test_snapshot_cap_at_10(self):
        """After 12 extractions → only 10 snapshots kept."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(12):
                await store_extraction(repo_path=tmpdir, model_yaml=MINIMAL_MODEL)
            snapshot_dir = Path(tmpdir) / ".architecture" / "snapshots"
            snapshots = list(snapshot_dir.glob("*.yaml"))
            assert len(snapshots) == 10

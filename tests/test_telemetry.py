"""Tests for telemetry store and recorder."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.telemetry.store import TelemetryStore
from opencode_arch.telemetry.recorder import record_invocation


class TestTelemetryStore:
    def test_create_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            assert store.db_path.exists()

    def test_record_and_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.record(tool="architect_slice", repo="test-repo", context_tokens=430, output_quality=85, iterations=1)
            records = store.query(tool="architect_slice")
            assert len(records) == 1
            assert records[0]["context_tokens"] == 430
            assert records[0]["output_quality"] == 85

    def test_record_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            for i in range(5):
                store.record(tool="architect_extract", repo=f"repo-{i}", context_tokens=400 + i * 10, output_quality=70 + i * 5, iterations=1)
            records = store.query(tool="architect_extract")
            assert len(records) == 5

    def test_average_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.record(tool="slice", repo="a", context_tokens=400, output_quality=80, iterations=1)
            store.record(tool="slice", repo="b", context_tokens=600, output_quality=90, iterations=2)
            avg = store.averages(tool="slice")
            assert avg["avg_context_tokens"] == 500
            assert avg["avg_output_quality"] == 85
            assert avg["avg_iterations"] == 1.5


class TestRecorder:
    @pytest.mark.asyncio
    async def test_record_invocation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            await record_invocation(store=store, tool="architect_scan", repo="my-project", context_tokens=0, output_quality=100, iterations=1)
            records = store.query(tool="architect_scan")
            assert len(records) == 1

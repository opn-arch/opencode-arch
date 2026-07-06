"""Tests for the metrics CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from opencode_arch.cli.metrics import show_metrics, format_metrics_table
from opencode_arch.telemetry.store import TelemetryStore


class TestMetricsCommand:
    def test_format_metrics_table_with_data(self):
        records = [
            {"tool": "extract", "repo": "my-repo", "context_tokens": 430, "output_quality": 94, "iterations": 1, "timestamp": 1720300000},
        ]
        output = format_metrics_table(records)
        assert "my-repo" in output
        assert "94" in output

    def test_format_metrics_table_empty(self):
        output = format_metrics_table([])
        assert "No records" in output

    def test_show_metrics_queries_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = TelemetryStore(db_path=db_path)
            store.record(tool="extract", repo="test", context_tokens=500, output_quality=90, iterations=1)
            with patch("opencode_arch.cli.metrics.TelemetryStore", return_value=store):
                show_metrics(tool="extract", last=5)

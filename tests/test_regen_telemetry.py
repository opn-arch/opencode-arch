"""Tests for the regen_outcomes extension to TelemetryStore."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.telemetry.store import TelemetryStore


class TestRegenOutcomes:
    def test_log_and_query_outcome(self):
        """Should log a regen outcome and retrieve it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.log_regen_outcome(
                repo="test-repo",
                subsystem="core",
                iteration=3,
                features={"constant_count": 5, "signature_count": 10, "contract_count": 8},
                pass_rate=0.75,
                time_seconds=42.5,
            )
            records = store.query_regen_outcomes(repo="test-repo")
            assert len(records) == 1
            assert records[0]["subsystem"] == "core"
            assert records[0]["iteration"] == 3
            assert records[0]["constant_count"] == 5
            assert records[0]["signature_count"] == 10
            assert records[0]["contract_count"] == 8
            assert records[0]["pass_rate"] == 0.75
            assert records[0]["time_seconds"] == 42.5

    def test_get_patterns_empty(self):
        """Should return empty list when no outcomes recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            patterns = store.get_patterns()
            assert patterns == []

    def test_get_patterns_aggregation(self):
        """Should aggregate stats per subsystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            # Two outcomes for same subsystem
            store.log_regen_outcome(
                repo="repo-a", subsystem="parser", iteration=2,
                features={"constant_count": 4, "signature_count": 6, "contract_count": 3},
                pass_rate=0.5, time_seconds=30.0,
            )
            store.log_regen_outcome(
                repo="repo-a", subsystem="parser", iteration=4,
                features={"constant_count": 6, "signature_count": 8, "contract_count": 5},
                pass_rate=0.8, time_seconds=50.0,
            )
            patterns = store.get_patterns()
            assert len(patterns) == 1
            assert patterns[0]["subsystem"] == "parser"
            assert patterns[0]["avg_pass_rate"] == pytest.approx(0.65)
            assert patterns[0]["avg_iterations"] == pytest.approx(3.0)
            assert patterns[0]["attempts"] == 2

    def test_get_patterns_with_filter(self):
        """Should filter by repo category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.log_regen_outcome(
                repo="python-dotenv", subsystem="core", iteration=1,
                features={}, pass_rate=1.0, time_seconds=10.0,
            )
            store.log_regen_outcome(
                repo="colorama", subsystem="ansi", iteration=2,
                features={}, pass_rate=0.5, time_seconds=20.0,
            )
            patterns = store.get_patterns(repo_category="python")
            assert len(patterns) == 1
            assert patterns[0]["subsystem"] == "core"

    def test_log_multiple_subsystems(self):
        """Should handle multiple distinct subsystems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.log_regen_outcome(
                repo="myrepo", subsystem="alpha", iteration=1,
                features={}, pass_rate=1.0, time_seconds=5.0,
            )
            store.log_regen_outcome(
                repo="myrepo", subsystem="beta", iteration=3,
                features={}, pass_rate=0.6, time_seconds=15.0,
            )
            records = store.query_regen_outcomes()
            assert len(records) == 2
            patterns = store.get_patterns()
            assert len(patterns) == 2

    def test_existing_invocations_still_work(self):
        """Original invocations table should still work after schema update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.record(tool="architect_scan", repo="test", context_tokens=100, output_quality=90)
            records = store.query(tool="architect_scan")
            assert len(records) == 1
            assert records[0]["output_quality"] == 90

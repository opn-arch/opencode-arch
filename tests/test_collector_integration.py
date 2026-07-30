"""Test that MCP tools drain metrics from arch-std and store them."""
from opencode_arch.telemetry.collector import drain_and_store


def test_drain_and_store_writes_to_telemetry(tmp_path):
    """Simulate metrics in collector, drain and store."""
    from architecture_model.monitoring import get_collector, FunctionMetrics

    collector = get_collector()
    collector.drain()  # clear

    collector.record(FunctionMetrics(
        function="generate_manifest",
        module="manifest.generator",
        time_ms=55.0,
        quality_scores={},
        input_metrics={},
        output_metrics={"module_count": 15},
    ))
    collector.record(FunctionMetrics(
        function="validate_model",
        module="core.validator",
        time_ms=2.0,
        quality_scores={"score": 92},
        input_metrics={},
        output_metrics={},
    ))

    db_path = tmp_path / "test.db"
    count = drain_and_store(tool="architect_scan", repo="my-repo", db_path=str(db_path))
    assert count == 2

    from opencode_arch.telemetry.store import TelemetryStore
    store = TelemetryStore(db_path)
    rows = store.get_function_metrics(repo="my-repo")
    assert len(rows) == 2
    fns = [r["function"] for r in rows]
    assert "generate_manifest" in fns
    assert "validate_model" in fns


def test_drain_and_store_empty_returns_zero(tmp_path):
    from architecture_model.monitoring import get_collector
    get_collector().drain()  # ensure empty

    count = drain_and_store(tool="test", repo="r", db_path=str(tmp_path / "t.db"))
    assert count == 0


def test_drain_and_store_never_raises():
    """Even with bad db_path, should return 0 not raise."""
    from architecture_model.monitoring import get_collector, FunctionMetrics
    collector = get_collector()
    collector.drain()
    collector.record(FunctionMetrics(function="f", module="m", time_ms=1.0))

    # Pass invalid path that would fail — should swallow
    count = drain_and_store(tool="t", repo="r", db_path="/nonexistent/dir/impossible.db")
    assert count == 0

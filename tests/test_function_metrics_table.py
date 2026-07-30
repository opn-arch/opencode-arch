"""Test function_metrics table in telemetry store."""
from opencode_arch.telemetry.store import TelemetryStore


def test_record_function_metrics(tmp_path):
    db = tmp_path / "test.db"
    store = TelemetryStore(db)
    store.record_function_metric(
        tool="architect_extract",
        function="validate_model",
        module="core.validator",
        repo="test-repo",
        time_ms=42.5,
        quality_scores='{"score": 95}',
        input_metrics='{"strict": false}',
        output_metrics='{"entity_count": 10}',
    )
    rows = store.get_function_metrics(repo="test-repo")
    assert len(rows) == 1
    assert rows[0]["function"] == "validate_model"
    assert rows[0]["time_ms"] == 42.5


def test_get_function_metrics_filtered(tmp_path):
    db = tmp_path / "test.db"
    store = TelemetryStore(db)
    store.record_function_metric(tool="scan", function="generate_manifest", module="manifest.generator", repo="r1", time_ms=10.0)
    store.record_function_metric(tool="extract", function="validate_model", module="core.validator", repo="r1", time_ms=20.0)
    store.record_function_metric(tool="scan", function="generate_manifest", module="manifest.generator", repo="r2", time_ms=30.0)

    r1 = store.get_function_metrics(repo="r1")
    assert len(r1) == 2

    scans = store.get_function_metrics(function="generate_manifest")
    assert len(scans) == 2

    by_tool = store.get_function_metrics(tool="scan")
    assert len(by_tool) == 2


def test_get_function_metrics_last_n(tmp_path):
    db = tmp_path / "test.db"
    store = TelemetryStore(db)
    for i in range(10):
        store.record_function_metric(tool="t", function=f"fn_{i}", module="m", repo="r", time_ms=float(i))

    last5 = store.get_function_metrics(last=5)
    assert len(last5) == 5

"""Drain metrics from architecture-model-standard and store in telemetry.

Call drain_and_store() at the end of each MCP tool invocation to persist
all function-level metrics that were collected during the operation.
"""
from __future__ import annotations

import json
from pathlib import Path


def drain_and_store(tool: str, repo: str = "", db_path: str | None = None) -> int:
    """Drain the thread-local metrics collector and write to telemetry DB.

    Returns the number of metrics stored. Never raises — swallows all exceptions.
    """
    try:
        from architecture_model.monitoring import get_collector
        from opencode_arch.telemetry.store import TelemetryStore

        collector = get_collector()
        metrics = collector.drain()
        if not metrics:
            return 0

        store = TelemetryStore(Path(db_path)) if db_path else TelemetryStore()
        for m in metrics:
            store.record_function_metric(
                tool=tool,
                function=m.function,
                module=m.module,
                repo=repo,
                time_ms=m.time_ms,
                quality_scores=json.dumps(m.quality_scores),
                input_metrics=json.dumps(m.input_metrics),
                output_metrics=json.dumps(m.output_metrics),
            )
        return len(metrics)
    except Exception:
        return 0

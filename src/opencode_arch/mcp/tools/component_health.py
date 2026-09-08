"""architect_component_health MCP tool.

Returns the SI&L record for a single component plus a short 7-day trend
summary. Reads the shared SQLite store at ``<repo>/.architecture/sil.sqlite``
populated by the SI&L instrumentation (B2.1.x).
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented

_SIL_DB_REL = Path(".architecture") / "sil.sqlite"


@instrumented("mcp_tool:component_health")
@tool_result
async def component_health_tool(repo_path: str, component_id: str) -> dict:
    """Return SI&L record + short 7-day trend for a single component."""
    if not component_id or not isinstance(component_id, str):
        return err("INVALID_ARGUMENT", "component_id must be a non-empty string")

    repo = resolve_repo(repo_path)
    db_path = repo / _SIL_DB_REL
    if not db_path.is_file():
        return err(
            "NOT_FOUND",
            f"SI&L store not found: {db_path}",
            component_id=component_id,
        )

    from architecture_model.sil.record import Event, Metrics, SILRecord

    from opencode_arch.sil.store import SILStore

    store = SILStore(db_path)
    rows = store.recent(component_id)
    if not rows:
        return err(
            "NOT_FOUND",
            f"no SI&L events for component {component_id!r}",
            component_id=component_id,
        )

    invocations_7d = store.invocations_7d(component_id)
    failure_rate_7d = store.failure_rate_7d(component_id)
    avg_duration_ms = store.avg_duration_ms(component_id)

    metrics = Metrics(
        invocations_7d=invocations_7d,
        failure_rate_7d=failure_rate_7d,
        avg_duration_ms=avg_duration_ms,
    )
    events = [
        Event(
            ts=row["ts"],
            kind=row["kind"],
            outcome=row["outcome"],
            duration_ms=row["duration_ms"],
            ref=row["ref"],
        )
        for row in rows
    ]
    record = SILRecord(
        component_id=component_id,
        kind="runtime-component",
        name=component_id,
        metrics=metrics,
        events=events,
    )

    record_dict = {
        "component_id": record.component_id,
        "kind": record.kind,
        "name": record.name,
        "metrics": asdict(record.metrics),
        "recent_events": [asdict(e) for e in record.events],
    }
    trend = {
        "invocations_7d": invocations_7d,
        "failure_rate_7d": failure_rate_7d,
        "avg_duration_ms": avg_duration_ms,
    }
    return ok({"record": record_dict, "trend": trend})

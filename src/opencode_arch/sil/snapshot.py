"""B2.1.5 — write per-component SIL snapshot as YAML.

Serializes a :class:`opencode_arch.sil.store.SILStore` view for a given
component to a YAML file. The on-disk shape is decoupled from the AMS
``SILRecord`` YAML representation so we can use the ``recent_events`` key
even though :mod:`architecture_model.sil.record` uses ``events``.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

import yaml

from architecture_model.sil.record import Event, Metrics, SILRecord

from .store import SILStore


def write_snapshot(store: SILStore, component_id: str, out_path: Path) -> None:
    """Write a runtime-component SIL snapshot for ``component_id`` to ``out_path``."""
    rows = store.recent(component_id)

    metrics = Metrics(
        invocations_7d=store.invocations_7d(component_id),
        failure_rate_7d=store.failure_rate_7d(component_id),
        avg_duration_ms=store.avg_duration_ms(component_id),
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

    payload = {
        "component_id": record.component_id,
        "kind": record.kind,
        "name": record.name,
        "metrics": asdict(record.metrics),
        "recent_events": [asdict(e) for e in record.events],
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    os.replace(tmp_path, out_path)

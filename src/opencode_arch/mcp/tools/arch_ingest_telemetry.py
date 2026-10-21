"""arch_ingest_telemetry — B-ROUND manual/external observation WRITE tool.

The WRITE counterpart to the pure-read ``arch_observe``. Where the
decorator-based ``@observe`` instrumentation captures runtime IO
automatically, this tool is the MANUAL/EXTERNAL feed: a caller pushes
observation events (e.g. telemetry collected out-of-band) into the SAME
journal (``<repo_path>/.architecture/observations.jsonl``) so that
health / flags / history projections can see them.

Each supplied event's SHAPE is validated through the canonical
:class:`openag.observe.event.Observation` dataclass (required fields +
``io_kind`` / ``direction`` enums). Individual bad events are NOT tool
errors — they are counted in ``rejected`` and skipped; only a non-list
``events`` argument is a tool-level ``INVALID_ARGUMENT``.

We deliberately BYPASS ``journal.append`` on the write path for ONE
reason: external telemetry carries its own event time, and
``arch_observe``'s ``since`` filter keys on ``ts``. ``journal.append``
always stamps a FRESH ``ts`` and cannot carry a caller-supplied one, so
we build the record ourselves (preserving ``ev["ts"]`` when present) and
append it directly using the same fail-soft file-write semantics. Shape
validation still goes through the canonical ``Observation``.

NOTE: this tool is itself instrumented via ``observe_tool_call``, so each
call ALSO appends one ``oca:arch_ingest_telemetry`` ``tool_call`` record
to the journal. That self-entry is NOT counted in the returned
``{ingested, rejected}`` summary (which counts only the supplied events).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from opencode_arch.mcp.envelope import resolve_repo, tool_result
from opencode_arch.mcp.tools._observe import observe_tool_call

_REL = Path(".architecture/observations.jsonl")


def _now_iso() -> str:
    """Deterministic-aware UTC timestamp (mirrors journal._now_iso)."""
    override = os.environ.get("AMS_DETERMINISTIC_NOW")
    if override:
        return override
    return datetime.now(timezone.utc).isoformat()


def _append_record(repo: Path | str, record: dict) -> bool:
    """Append one record as a JSON line. Fail-soft: returns ``False`` on error.

    Mirrors ``openag.observe.journal.append``'s file-write semantics
    (``O_APPEND | O_CREAT | O_WRONLY`` + ``fsync``), but writes a
    caller-built record verbatim so an externally-supplied ``ts`` is
    preserved rather than overwritten.
    """
    try:
        path = Path(repo) / _REL
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record) + "\n"
        fd = os.open(str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        return True
    except Exception:
        return False


@tool_result
async def arch_ingest_telemetry(repo_path: str, events: list[dict]) -> dict:
    """Append externally-supplied observation events to the journal."""
    with observe_tool_call(repo_path, "arch_ingest_telemetry"):
        repo = resolve_repo(repo_path)

        if not isinstance(events, list):
            raise ValueError("events must be a list")

        from openag.observe.event import Observation

        ingested = 0
        rejected = 0

        for ev in events:
            if not isinstance(ev, dict):
                rejected += 1
                continue
            try:
                obs = Observation(
                    component_id=ev["component_id"],
                    io_kind=ev["io_kind"],
                    direction=ev["direction"],
                    name=ev["name"],
                    payload_digest=ev.get("payload_digest", ""),
                    meta=ev.get("meta", {}),
                )
            except Exception:
                rejected += 1
                continue

            record = obs.to_record()
            ts = ev.get("ts")
            if isinstance(ts, str) and ts:
                record["ts"] = ts
            else:
                record["ts"] = _now_iso()

            if _append_record(repo, record):
                ingested += 1
            else:
                rejected += 1

        return {"ingested": ingested, "rejected": rejected}

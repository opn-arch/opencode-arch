"""SQLite-backed SIL event store with per-component ring-buffer semantics."""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sil_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    outcome TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_sil_events_component_id ON sil_events(component_id);
CREATE INDEX IF NOT EXISTS idx_sil_events_ts ON sil_events(ts);
"""

_RING_LIMIT = 50


def _now_iso() -> str:
    """Return current UTC time as ISO 8601, honoring AMS_DETERMINISTIC_NOW."""
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()


class SILStore:
    """Thread-safe SQLite event log for SIL invocations."""

    def __init__(self, path: str | Path):
        self._lock = threading.Lock()
        if isinstance(path, Path):
            path_str = str(path)
        else:
            path_str = path
        self._path = path_str
        self._is_memory = path_str == ":memory:"

        # For :memory: we must keep a single connection alive; for file-backed
        # we still keep one connection (guarded by lock) for simplicity + WAL.
        self._conn = sqlite3.connect(
            path_str,
            check_same_thread=False,
            isolation_level=None,  # autocommit; we manage transactions explicitly
        )
        self._conn.row_factory = sqlite3.Row

        if not self._is_memory:
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=NORMAL")
            except sqlite3.DatabaseError:
                # Non-fatal: fall back to defaults if pragmas fail.
                pass

        self._conn.executescript(_SCHEMA)

    def emit(
        self,
        component_id: str,
        kind: str,
        outcome: str,
        duration_ms: int,
        ref: str | None = None,
    ) -> None:
        """Insert an event and trim the per-component ring to 50 rows."""
        ts = _now_iso()
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute("BEGIN")
                cur.execute(
                    "INSERT INTO sil_events "
                    "(component_id, ts, kind, outcome, duration_ms, ref) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (component_id, ts, kind, outcome, int(duration_ms), ref),
                )
                # Ring-buffer trim: keep newest _RING_LIMIT rows for this component.
                cur.execute(
                    "DELETE FROM sil_events WHERE component_id = ? AND id NOT IN ("
                    "SELECT id FROM sil_events WHERE component_id = ? "
                    "ORDER BY id DESC LIMIT ?)",
                    (component_id, component_id, _RING_LIMIT),
                )
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def recent(self, component_id: str, n: int = 50) -> list[dict[str, Any]]:
        """Return newest-first list of events for a component."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT component_id, ts, kind, outcome, duration_ms, ref "
                "FROM sil_events WHERE component_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (component_id, int(n)),
            )
            return [dict(row) for row in cur.fetchall()]

    # ---- Aggregations (7-day window) --------------------------------------

    def _since_7d_iso(self) -> str:
        # Use real UTC now for aggregation windows even under deterministic mode,
        # so tests emitting with a pinned ts still fall inside the window when
        # the pinned value is recent. For deterministic aggregation callers
        # should not rely on this window in fixture tests.
        return (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    def invocations_7d(self, component_id: str) -> int:
        since = self._since_7d_iso()
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM sil_events WHERE component_id = ? AND ts >= ?",
                (component_id, since),
            )
            return int(cur.fetchone()[0])

    def failure_rate_7d(self, component_id: str) -> float:
        since = self._since_7d_iso()
        with self._lock:
            cur = self._conn.execute(
                "SELECT "
                "SUM(CASE WHEN outcome = 'error' THEN 1 ELSE 0 END), "
                "COUNT(*) "
                "FROM sil_events WHERE component_id = ? AND ts >= ?",
                (component_id, since),
            )
            errors, total = cur.fetchone()
            if not total:
                return 0.0
            return float(errors or 0) / float(total)

    def avg_duration_ms(self, component_id: str) -> float:
        since = self._since_7d_iso()
        with self._lock:
            cur = self._conn.execute(
                "SELECT AVG(duration_ms) FROM sil_events "
                "WHERE component_id = ? AND ts >= ?",
                (component_id, since),
            )
            avg = cur.fetchone()[0]
            return float(avg) if avg is not None else 0.0

    # ---- AMS binding ------------------------------------------------------

    def bind_ams_decorator(self) -> bool:
        """Bind this store as the sink for AMS SIL decorators.

        Returns True if the binding succeeded, False if the AMS module is
        not importable (so OCA can start without AMS available).
        """
        try:
            from architecture_model.sil import decorators as _decorators
        except ImportError:
            return False
        bind_store = getattr(_decorators, "bind_store", None)
        if bind_store is None:
            return False
        bind_store(self)
        return True


def bind_ams_decorator(store: SILStore) -> bool:
    """Module-level convenience: bind an existing SILStore to AMS decorators."""
    return store.bind_ams_decorator()

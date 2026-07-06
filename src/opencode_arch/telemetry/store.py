"""SQLite-backed telemetry store for tool invocations."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any


class TelemetryStore:
    """Records tool invocations and outcomes for optimization."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".opencode-arch" / "telemetry.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                tool TEXT NOT NULL,
                repo TEXT,
                context_tokens INTEGER DEFAULT 0,
                output_quality INTEGER DEFAULT 0,
                iterations INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

    def record(self, tool: str, repo: str = "", context_tokens: int = 0,
               output_quality: int = 0, iterations: int = 1, metadata: str = ""):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO invocations (timestamp, tool, repo, context_tokens, output_quality, iterations, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), tool, repo, context_tokens, output_quality, iterations, metadata),
        )
        conn.commit()
        conn.close()

    def query(self, tool: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if tool:
            rows = conn.execute(
                "SELECT * FROM invocations WHERE tool = ? ORDER BY timestamp DESC LIMIT ?",
                (tool, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM invocations ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def averages(self, tool: str) -> dict[str, float]:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT AVG(context_tokens), AVG(output_quality), AVG(iterations) "
            "FROM invocations WHERE tool = ?",
            (tool,),
        ).fetchone()
        conn.close()
        return {
            "avg_context_tokens": row[0] or 0,
            "avg_output_quality": row[1] or 0,
            "avg_iterations": row[2] or 0,
        }

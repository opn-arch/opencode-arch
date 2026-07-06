"""SQLite-backed telemetry store for tool invocations."""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regen_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                subsystem TEXT NOT NULL,
                iteration INTEGER NOT NULL,
                constant_count INTEGER DEFAULT 0,
                signature_count INTEGER DEFAULT 0,
                contract_count INTEGER DEFAULT 0,
                pass_rate REAL DEFAULT 0.0,
                time_seconds REAL DEFAULT 0.0,
                timestamp TEXT
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

    # ------------------------------------------------------------------
    # Regen-loop learning store
    # ------------------------------------------------------------------

    def log_regen_outcome(
        self,
        repo: str,
        subsystem: str,
        iteration: int,
        features: dict[str, int],
        pass_rate: float,
        time_seconds: float,
    ):
        """Log a regeneration attempt outcome.

        Args:
            repo: Repository name.
            subsystem: Subsystem name.
            iteration: Which iteration converged (or max if didn't).
            features: Dict with constant_count, signature_count, contract_count.
            pass_rate: Final pass rate achieved.
            time_seconds: Wall-clock time for this subsystem.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO regen_outcomes "
            "(repo, subsystem, iteration, constant_count, signature_count, contract_count, "
            "pass_rate, time_seconds, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                repo,
                subsystem,
                iteration,
                features.get("constant_count", 0),
                features.get("signature_count", 0),
                features.get("contract_count", 0),
                pass_rate,
                time_seconds,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_patterns(self, repo_category: str | None = None) -> list[dict[str, Any]]:
        """Retrieve learned patterns from regen outcomes.

        Returns aggregated stats per subsystem showing average pass rates,
        iteration counts, and feature correlations.

        Args:
            repo_category: Optional filter by repo name pattern.

        Returns:
            List of dicts with pattern information.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if repo_category:
            rows = conn.execute(
                "SELECT subsystem, "
                "AVG(pass_rate) as avg_pass_rate, "
                "AVG(iteration) as avg_iterations, "
                "AVG(constant_count) as avg_constants, "
                "AVG(signature_count) as avg_signatures, "
                "AVG(contract_count) as avg_contracts, "
                "COUNT(*) as attempts "
                "FROM regen_outcomes WHERE repo LIKE ? "
                "GROUP BY subsystem ORDER BY avg_pass_rate DESC",
                (f"%{repo_category}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT subsystem, "
                "AVG(pass_rate) as avg_pass_rate, "
                "AVG(iteration) as avg_iterations, "
                "AVG(constant_count) as avg_constants, "
                "AVG(signature_count) as avg_signatures, "
                "AVG(contract_count) as avg_contracts, "
                "COUNT(*) as attempts "
                "FROM regen_outcomes "
                "GROUP BY subsystem ORDER BY avg_pass_rate DESC",
            ).fetchall()

        conn.close()
        return [dict(row) for row in rows]

    def query_regen_outcomes(self, repo: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Query raw regen outcome records.

        Args:
            repo: Optional filter by repo name.
            limit: Max records to return.

        Returns:
            List of outcome records as dicts.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if repo:
            rows = conn.execute(
                "SELECT * FROM regen_outcomes WHERE repo = ? ORDER BY timestamp DESC LIMIT ?",
                (repo, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM regen_outcomes ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

        conn.close()
        return [dict(row) for row in rows]

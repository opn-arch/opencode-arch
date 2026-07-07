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
                prompt_tokens INTEGER DEFAULT 0,
                source_equivalent_tokens INTEGER DEFAULT 0,
                compression_ratio REAL DEFAULT 0.0,
                mode TEXT DEFAULT 'normal',
                timestamp TEXT
            )
        """)
        # Migration: add token columns if they don't exist (for existing DBs)
        try:
            conn.execute("ALTER TABLE regen_outcomes ADD COLUMN prompt_tokens INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE regen_outcomes ADD COLUMN source_equivalent_tokens INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE regen_outcomes ADD COLUMN compression_ratio REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE regen_outcomes ADD COLUMN mode TEXT DEFAULT 'normal'")
        except sqlite3.OperationalError:
            pass  # columns already exist

        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_curve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                repo_sequence INTEGER NOT NULL,
                mode TEXT NOT NULL DEFAULT 'normal',
                total_subsystems INTEGER DEFAULT 0,
                converged_subsystems INTEGER DEFAULT 0,
                avg_pass_rate REAL DEFAULT 0.0,
                avg_iterations REAL DEFAULT 0.0,
                avg_prompt_tokens REAL DEFAULT 0.0,
                avg_source_equivalent REAL DEFAULT 0.0,
                avg_compression_ratio REAL DEFAULT 0.0,
                total_time_seconds REAL DEFAULT 0.0,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id TEXT UNIQUE NOT NULL,
                discovered_repo TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT DEFAULT '{}',
                applied_to TEXT DEFAULT '[]',
                impact REAL,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS report_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                mode TEXT NOT NULL,
                grade TEXT NOT NULL,
                fidelity REAL,
                compression_ratio REAL,
                failure_patterns TEXT DEFAULT '{}',
                novel_patterns INTEGER DEFAULT 0,
                improvement_actions TEXT DEFAULT '[]',
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drift_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT NOT NULL,
                issue TEXT NOT NULL,
                severity TEXT NOT NULL,
                auto_fixable INTEGER DEFAULT 0,
                suggested_fix TEXT DEFAULT '',
                resolved INTEGER DEFAULT 0,
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
        prompt_tokens: int = 0,
        source_equivalent_tokens: int = 0,
        compression_ratio: float = 0.0,
        mode: str = "normal",
    ):
        """Log a regeneration attempt outcome.

        Args:
            repo: Repository name.
            subsystem: Subsystem name.
            iteration: Which iteration converged (or max if didn't).
            features: Dict with constant_count, signature_count, contract_count.
            pass_rate: Final pass rate achieved.
            time_seconds: Wall-clock time for this subsystem.
            prompt_tokens: Tokens used in the prompt.
            source_equivalent_tokens: Tokens agent would need without extension.
            compression_ratio: source_equivalent / prompt_tokens.
            mode: Regen mode ('normal' or 'blind').
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO regen_outcomes "
            "(repo, subsystem, iteration, constant_count, signature_count, contract_count, "
            "pass_rate, time_seconds, prompt_tokens, source_equivalent_tokens, "
            "compression_ratio, mode, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                repo,
                subsystem,
                iteration,
                features.get("constant_count", 0),
                features.get("signature_count", 0),
                features.get("contract_count", 0),
                pass_rate,
                time_seconds,
                prompt_tokens,
                source_equivalent_tokens,
                compression_ratio,
                mode,
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

    # ------------------------------------------------------------------
    # Learning curve tracking
    # ------------------------------------------------------------------

    def record_learning_curve(
        self,
        repo: str,
        mode: str,
        total_subsystems: int,
        converged_subsystems: int,
        avg_pass_rate: float,
        avg_iterations: float,
        avg_prompt_tokens: float,
        avg_source_equivalent: float,
        avg_compression_ratio: float,
        total_time_seconds: float,
    ):
        """Record per-repo summary for learning curve trend analysis.

        repo_sequence is auto-computed as the count of previous entries + 1.
        This allows tracking: does the system get better with each new repo?
        """
        conn = sqlite3.connect(self.db_path)
        # Auto-compute sequence number
        row = conn.execute(
            "SELECT COALESCE(MAX(repo_sequence), 0) FROM learning_curve"
        ).fetchone()
        seq = (row[0] or 0) + 1

        conn.execute(
            "INSERT INTO learning_curve "
            "(repo, repo_sequence, mode, total_subsystems, converged_subsystems, "
            "avg_pass_rate, avg_iterations, avg_prompt_tokens, avg_source_equivalent, "
            "avg_compression_ratio, total_time_seconds, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (repo, seq, mode, total_subsystems, converged_subsystems,
             avg_pass_rate, avg_iterations, avg_prompt_tokens, avg_source_equivalent,
             avg_compression_ratio, total_time_seconds,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

    def get_learning_curve(self, mode: str | None = None) -> list[dict[str, Any]]:
        """Get learning curve data ordered by repo sequence.

        Shows how metrics improve with each successive repo processed.
        Key metrics that should IMPROVE (go down):
        - avg_iterations: fewer attempts needed
        - avg_prompt_tokens: more efficient prompts

        Key metrics that should IMPROVE (go up):
        - avg_pass_rate: higher fidelity
        - avg_compression_ratio: better token arbitrage
        - converged_subsystems / total_subsystems: higher success rate
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if mode:
            rows = conn.execute(
                "SELECT * FROM learning_curve WHERE mode = ? ORDER BY repo_sequence ASC",
                (mode,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM learning_curve ORDER BY repo_sequence ASC"
            ).fetchall()

        conn.close()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Report cards and lessons
    # ------------------------------------------------------------------

    def record_report_card(self, repo: str, mode: str, grade: str, fidelity: float,
                           compression_ratio: float, failure_patterns: str,
                           novel_patterns: int, improvement_actions: str):
        """Record a report card for a repo run."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO report_cards (repo, mode, grade, fidelity, compression_ratio, "
            "failure_patterns, novel_patterns, improvement_actions, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (repo, mode, grade, fidelity, compression_ratio, failure_patterns,
             novel_patterns, improvement_actions,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

    def get_report_cards(self, repo: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Query report cards, optionally filtered by repo."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if repo:
            rows = conn.execute(
                "SELECT * FROM report_cards WHERE repo = ? ORDER BY timestamp DESC LIMIT ?",
                (repo, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM report_cards ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def record_lesson(self, lesson_id: str, discovered_repo: str, category: str,
                      description: str, evidence: str = "{}"):
        """Record a new lesson learned. Ignores duplicates (same lesson_id)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO lessons (lesson_id, discovered_repo, category, "
                "description, evidence, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (lesson_id, discovered_repo, category, description, evidence,
                 datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_lessons(self, category: str | None = None) -> list[dict[str, Any]]:
        """Query all lessons, optionally filtered by category."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if category:
            rows = conn.execute(
                "SELECT * FROM lessons WHERE category = ? ORDER BY timestamp DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM lessons ORDER BY timestamp DESC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_lesson_applied(self, lesson_id: str, repo: str):
        """Mark a lesson as applied to a specific repo."""
        conn = sqlite3.connect(self.db_path)
        # Get current applied_to
        row = conn.execute(
            "SELECT applied_to FROM lessons WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()
        if row:
            import json
            current = json.loads(row[0] or "[]")
            if repo not in current:
                current.append(repo)
                conn.execute(
                    "UPDATE lessons SET applied_to = ? WHERE lesson_id = ?",
                    (json.dumps(current), lesson_id),
                )
                conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Drift flags
    # ------------------------------------------------------------------

    def record_drift_flag(self, file: str, issue: str, severity: str,
                          auto_fixable: bool = False, suggested_fix: str = ""):
        """Record a documentation drift flag."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO drift_flags (file, issue, severity, auto_fixable, suggested_fix, "
            "resolved, timestamp) VALUES (?, ?, ?, ?, ?, 0, ?)",
            (file, issue, severity, int(auto_fixable), suggested_fix,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

    def get_drift_flags(self, resolved: bool = False) -> list[dict[str, Any]]:
        """Get drift flags, optionally filtered by resolution status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM drift_flags WHERE resolved = ? ORDER BY timestamp DESC",
            (int(resolved),),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def resolve_drift_flag(self, flag_id: int):
        """Mark a drift flag as resolved."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE drift_flags SET resolved = 1 WHERE id = ?", (flag_id,))
        conn.commit()
        conn.close()

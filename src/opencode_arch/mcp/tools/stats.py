"""architect_stats MCP tool — aggregate session and historical quality metrics."""
from __future__ import annotations
from typing import Any


async def get_stats(repo_path: str = "", tool_filter: str = "") -> dict[str, Any]:
    """Aggregate quality and performance metrics.
    
    Returns session stats, historical telemetry summary, and actionable suggestions.
    
    Args:
        repo_path: Optional - filter stats to specific repo.
        tool_filter: Optional - filter to specific tool name.
    """
    result: dict[str, Any] = {}
    
    # Session stats from accumulator
    try:
        from opencode_arch.mcp.quality import SessionAccumulator
        acc = SessionAccumulator.instance()
        result["session"] = acc.summary()
    except Exception:
        result["session"] = {"error": "unavailable"}
    
    # Historical from telemetry DB
    try:
        from opencode_arch.telemetry.store import TelemetryStore
        store = TelemetryStore()
        
        # Recent invocations summary
        import sqlite3
        conn = sqlite3.connect(store.db_path)
        conn.row_factory = sqlite3.Row
        
        query = "SELECT tool, COUNT(*) as calls, AVG(output_quality) as avg_quality, AVG(context_tokens) as avg_tokens FROM invocations"
        params = []
        conditions = []
        if repo_path:
            conditions.append("repo = ?")
            params.append(repo_path.split("/")[-1] if "/" in repo_path else repo_path)
        if tool_filter:
            conditions.append("tool = ?")
            params.append(tool_filter)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY tool ORDER BY calls DESC"
        
        rows = conn.execute(query, params).fetchall()
        result["historical"] = [
            {"tool": r["tool"], "calls": r["calls"], "avg_quality": round(r["avg_quality"] or 0, 1), "avg_tokens": round(r["avg_tokens"] or 0)}
            for r in rows
        ]
        conn.close()
    except Exception as e:
        result["historical"] = {"error": str(e)}
    
    # Suggestions based on patterns
    suggestions = []
    session = result.get("session", {})
    if isinstance(session, dict) and session.get("total_calls", 0) > 0:
        warnings = session.get("all_warnings", [])
        if any("compression" in w.lower() for w in warnings):
            suggestions.append("High compression detected — try per-block slicing with focus parameter")
        if any("0 modules" in w for w in warnings):
            suggestions.append("Scan found 0 modules — check repo_path points to source root")
    result["suggestions"] = suggestions
    
    return result

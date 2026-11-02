"""Telemetry metrics drain (AMS monitoring removed in C6).

Historically this drained function-level metrics from
architecture-model-standard's monitoring collector. That dependency was
severed in C6; the drain is now a no-op retained for call-site stability.
"""
from __future__ import annotations


def drain_and_store(tool: str, repo: str = "", db_path: str | None = None) -> int:
    """No-op drain. Returns 0 (AMS monitoring removed in C6). Never raises."""
    return 0

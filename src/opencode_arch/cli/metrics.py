"""Metrics command - display recorded telemetry."""
from __future__ import annotations

import time

from opencode_arch.telemetry.store import TelemetryStore


def show_metrics(tool: str | None = None, last: int = 10):
    """Query and display metrics from the telemetry store."""
    store = TelemetryStore()
    records = store.query(tool=tool, limit=last)
    print(format_metrics_table(records))
    if tool and records:
        avgs = store.averages(tool=tool)
        print(f"\n  Averages for '{tool}':")
        print(f"    Tokens:     {avgs['avg_context_tokens']:.0f}")
        print(f"    Quality:    {avgs['avg_output_quality']:.0f}/100")
        print(f"    Iterations: {avgs['avg_iterations']:.1f}")


def format_metrics_table(records: list[dict]) -> str:
    """Format records as a readable table."""
    if not records:
        return "  No records found."
    lines = []
    lines.append(f"  {'Tool':<18} {'Repo':<25} {'Score':>5} {'Tokens':>6} {'Iter':>4} {'Time'}")
    lines.append("  " + "-" * 75)
    for r in records:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("timestamp", 0)))
        lines.append(
            f"  {r.get('tool', '?'):<18} {r.get('repo', '?'):<25} "
            f"{r.get('output_quality', 0):>5} {r.get('context_tokens', 0):>6} "
            f"{r.get('iterations', 0):>4} {ts}"
        )
    return "\n".join(lines)

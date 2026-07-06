"""Async recorder for tool invocations."""
from __future__ import annotations

from opencode_arch.telemetry.store import TelemetryStore


async def record_invocation(store: TelemetryStore, tool: str, repo: str = "",
                            context_tokens: int = 0, output_quality: int = 0,
                            iterations: int = 1, metadata: str = ""):
    """Record a tool invocation asynchronously."""
    store.record(tool=tool, repo=repo, context_tokens=context_tokens,
                 output_quality=output_quality, iterations=iterations, metadata=metadata)

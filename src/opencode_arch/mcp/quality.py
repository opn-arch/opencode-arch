"""Quality metadata module for MCP tools."""

import time
import functools
from contextvars import ContextVar
from typing import Any

# Context var for tools to inject additional quality fields
quality_context: ContextVar[dict] = ContextVar("quality_context", default={})

TOOL_WARNINGS = {
    "scan": [("modules", lambda r: r.get("modules") is not None and len(r.get("modules", [])) == 0, "0 modules found")],
    "group": [
        ("groups_high", lambda r: len(r.get("groups", [])) > 20, ">20 groups detected"),
        ("groups_low", lambda r: r.get("total_modules", 0) > 10 and len(r.get("groups", [])) < 2, "<2 groups for >10 modules"),
    ],
    "slice": [
        ("compression", lambda r: r.get("compression_ratio", 0) > 50, "compression >50x"),
        ("budget", lambda r: r.get("budget_exceeded", False), "budget exceeded"),
    ],
    "extract": [
        ("score_low", lambda r: r.get("score", 100) < 50, "score <50"),
        ("entities_dropped", lambda r: r.get("entities_dropped", False), "entities dropped"),
    ],
    "check": [
        ("file_coverage", lambda r: r.get("file_coverage", 100) < 50, "file_coverage <50%"),
        ("relationship_accuracy", lambda r: r.get("relationship_accuracy", 100) < 50, "relationship_accuracy <50%"),
    ],
    "ingest": [("no_relationships", lambda r: r.get("relationships_created", 1) == 0, "0 relationships created")],
}


def estimate_regenerability(compression_ratio: float, confidence: float, n_components: int, n_contracts: int) -> float:
    """Estimate regenerability based on compression ratio, confidence, components, and contracts."""
    if compression_ratio > 200:
        base = 0.19
    elif compression_ratio > 50:
        base = 0.44
    elif compression_ratio > 10:
        base = 0.55
    elif compression_ratio >= 2:
        base = 0.69
    else:
        base = 0.78

    contract_boost = min(0.2, n_contracts * 0.01)
    confidence_factor = confidence / 100
    return round(min(1.0, base + contract_boost) * confidence_factor, 2)


def check_fidelity(input_data: Any, output_data: Any) -> dict:
    """Count entities in input vs output and detect data loss."""
    def count_entities(data):
        if isinstance(data, dict):
            count = 0
            for v in data.values():
                if isinstance(v, list):
                    count += len(v)
                elif isinstance(v, dict):
                    count += count_entities(v)
                else:
                    count += 1
            return count
        elif isinstance(data, list):
            return len(data)
        return 1

    entities_in = count_entities(input_data)
    entities_out = count_entities(output_data)
    return {"entities_in": entities_in, "entities_out": entities_out, "data_loss": entities_out < entities_in}


class SessionAccumulator:
    """Singleton per-process session stats accumulator."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._reset()
        return cls._instance

    def _reset(self):
        self.total_calls = 0
        self.total_latency_ms = 0.0
        self.per_tool: dict[str, int] = {}
        self.warnings_issued = 0

    def record(self, tool_name: str, latency_ms: float, warnings: list):
        self.total_calls += 1
        self.total_latency_ms += latency_ms
        self.per_tool[tool_name] = self.per_tool.get(tool_name, 0) + 1
        self.warnings_issued += len(warnings)

    def summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_latency_ms": self.total_latency_ms,
            "per_tool": dict(self.per_tool),
            "warnings_issued": self.warnings_issued,
        }


def with_quality(func):
    """Decorator that appends _quality metadata to dict results."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if isinstance(result, dict):
            ctx = quality_context.get({})
            warnings = ctx.get("warnings", [])
            result["_quality"] = {"latency_ms": latency_ms, "warnings": warnings, **{k: v for k, v in ctx.items() if k != "warnings"}}

            # D2: Evaluate TOOL_WARNINGS rules
            # Map function names to TOOL_WARNINGS keys
            name_map = {
                "store_extraction": "extract",
                "scan_repository": "scan",
                "slice_context": "slice",
                "group_repository": "group",
                "check_representativeness": "check",
                "ingest_openapi": "ingest",
            }
            tool_key = name_map.get(func.__name__, func.__name__)
            if tool_key in TOOL_WARNINGS:
                for rule_name, check_fn, message in TOOL_WARNINGS[tool_key]:
                    try:
                        if check_fn(result):
                            result.setdefault("warnings", []).append({"rule": rule_name, "message": message})
                    except Exception:
                        pass  # Rule evaluation failures are non-fatal

        return result

    return wrapper

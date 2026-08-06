"""Tests for quality module."""

import asyncio
import pytest
from opencode_arch.mcp.quality import (
    estimate_regenerability,
    check_fidelity,
    SessionAccumulator,
    with_quality,
    quality_context,
)


class TestEstimateRegenerability:
    def test_low_compression(self):
        assert estimate_regenerability(1.5, 100, 5, 0) == 0.78

    def test_medium_compression(self):
        assert estimate_regenerability(5, 100, 5, 0) == 0.69

    def test_high_compression(self):
        assert estimate_regenerability(30, 100, 5, 0) == 0.55

    def test_very_high_compression(self):
        assert estimate_regenerability(100, 100, 5, 0) == 0.44

    def test_extreme_compression(self):
        assert estimate_regenerability(300, 100, 5, 0) == 0.19

    def test_contract_boost(self):
        assert estimate_regenerability(1.5, 100, 5, 10) == 0.88

    def test_contract_boost_capped(self):
        assert estimate_regenerability(1.5, 100, 5, 30) == 0.98

    def test_confidence_scales(self):
        assert estimate_regenerability(1.5, 50, 5, 0) == 0.39

    def test_boundary_2x(self):
        assert estimate_regenerability(2, 100, 5, 0) == 0.69

    def test_boundary_10x(self):
        assert estimate_regenerability(10.1, 100, 5, 0) == 0.55


class TestCheckFidelity:
    def test_no_loss(self):
        result = check_fidelity({"a": [1, 2, 3]}, {"b": [1, 2, 3]})
        assert result["data_loss"] is False
        assert result["entities_in"] == 3
        assert result["entities_out"] == 3

    def test_data_loss(self):
        result = check_fidelity({"a": [1, 2, 3]}, {"b": [1]})
        assert result["data_loss"] is True
        assert result["entities_in"] == 3
        assert result["entities_out"] == 1

    def test_no_loss_more_out(self):
        result = check_fidelity({"a": [1]}, {"b": [1, 2, 3]})
        assert result["data_loss"] is False


class TestSessionAccumulator:
    def setup_method(self):
        SessionAccumulator._instance = None

    def test_singleton(self):
        a = SessionAccumulator()
        b = SessionAccumulator()
        assert a is b

    def test_record_and_summary(self):
        acc = SessionAccumulator()
        acc.record("scan", 100.0, [])
        acc.record("scan", 50.0, ["warn1"])
        acc.record("slice", 200.0, [])
        s = acc.summary()
        assert s["total_calls"] == 3
        assert s["total_latency_ms"] == 350.0
        assert s["per_tool"] == {"scan": 2, "slice": 1}
        assert s["warnings_issued"] == 1


class TestWithQuality:
    def test_dict_result(self):
        @with_quality
        async def tool():
            return {"data": 42}

        result = asyncio.run(tool())
        assert "_quality" in result
        assert "latency_ms" in result["_quality"]
        assert result["data"] == 42

    def test_string_result(self):
        @with_quality
        async def tool():
            return "hello"

        result = asyncio.run(tool())
        assert result == "hello"

    def test_quality_context_warnings(self):
        @with_quality
        async def tool():
            quality_context.set({"warnings": ["something wrong"]})
            return {"ok": True}

        result = asyncio.run(tool())
        assert result["_quality"]["warnings"] == ["something wrong"]


class TestToolWarningsEvaluation:
    """D2: TOOL_WARNINGS rules are evaluated by with_quality."""

    def test_rule_triggers_warning(self):
        """A rule that triggers → warning appears in result."""
        @with_quality
        async def scan_repository():
            return {"modules": []}

        result = asyncio.run(scan_repository())
        assert "warnings" in result
        warnings = result["warnings"]
        assert any(w["rule"] == "modules" for w in warnings)

    def test_rule_does_not_trigger(self):
        """A rule that doesn't trigger → no warning."""
        @with_quality
        async def scan_repository():
            return {"modules": [{"name": "foo"}]}

        result = asyncio.run(scan_repository())
        warnings = result.get("warnings", [])
        assert not any(w.get("rule") == "modules" for w in warnings)

    def test_non_dict_result_untouched(self):
        """Rules work for dict results only (non-dict untouched)."""
        @with_quality
        async def scan_repository():
            return "just a string"

        result = asyncio.run(scan_repository())
        assert result == "just a string"

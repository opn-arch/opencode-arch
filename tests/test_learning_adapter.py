"""Tests for adaptive prompt optimization."""
import pytest

from opencode_arch.learning.adapter import get_adaptations, apply_adaptations
from opencode_arch.learning.patterns import Strategy


class TestGetAdaptations:
    """Test proactive adaptation rules."""

    def test_high_dep_count_triggers_expand_context(self):
        adaptations = get_adaptations(
            subsystem_name="stdlib",
            dependency_count=5,
            signature_count=20,
            contract_count=50,
            body_hint_coverage=0.8,
        )
        strategies = [a.strategy for a in adaptations]
        assert Strategy.EXPAND_DEP_CONTEXT in strategies

    def test_low_dep_count_no_expand(self):
        adaptations = get_adaptations(
            subsystem_name="utils",
            dependency_count=1,
            signature_count=10,
            contract_count=30,
            body_hint_coverage=0.9,
        )
        strategies = [a.strategy for a in adaptations]
        assert Strategy.EXPAND_DEP_CONTEXT not in strategies

    def test_low_contracts_increases_cap(self):
        adaptations = get_adaptations(
            subsystem_name="config",
            dependency_count=0,
            signature_count=5,
            contract_count=3,
            body_hint_coverage=1.0,
        )
        strategies = [a.strategy for a in adaptations]
        assert Strategy.INCREASE_CONTRACT_CAP in strategies

    def test_low_body_hint_coverage_triggers_source_excerpt(self):
        adaptations = get_adaptations(
            subsystem_name="processors",
            dependency_count=2,
            signature_count=15,
            contract_count=40,
            body_hint_coverage=0.3,
        )
        strategies = [a.strategy for a in adaptations]
        assert Strategy.INCLUDE_SOURCE_EXCERPT in strategies

    def test_historical_cross_dep_triggers_expand(self):
        history = [
            {"pattern": "cross_dep", "subsystem": "other_stdlib"},
            {"pattern": "cross_dep", "subsystem": "another"},
        ]
        adaptations = get_adaptations(
            subsystem_name="my_stdlib",
            dependency_count=1,  # below threshold
            signature_count=10,
            contract_count=20,
            body_hint_coverage=0.8,
            historical_patterns=history,
        )
        strategies = [a.strategy for a in adaptations]
        assert Strategy.EXPAND_DEP_CONTEXT in strategies

    def test_no_adaptations_for_simple_subsystem(self):
        adaptations = get_adaptations(
            subsystem_name="ansi",
            dependency_count=0,
            signature_count=5,
            contract_count=30,
            body_hint_coverage=1.0,
        )
        assert len(adaptations) == 0


class TestApplyAdaptations:
    """Test adaptation application to prompt params."""

    def test_apply_expand_dep_context(self):
        from opencode_arch.learning.patterns import Strategy
        from opencode_arch.learning.adapter import PromptAdaptation

        adaptations = [PromptAdaptation(
            strategy=Strategy.EXPAND_DEP_CONTEXT,
            reason="test",
            params={"include_body_hints": True},
        )]
        result = apply_adaptations(adaptations)
        assert result["include_dep_body_hints"] is True

    def test_apply_increase_contract_cap(self):
        from opencode_arch.learning.adapter import PromptAdaptation

        adaptations = [PromptAdaptation(
            strategy=Strategy.INCREASE_CONTRACT_CAP,
            reason="test",
            params={"new_cap": 150},
        )]
        result = apply_adaptations(adaptations, contract_cap=50)
        assert result["contract_cap"] == 150

    def test_adaptations_applied_tracked(self):
        from opencode_arch.learning.adapter import PromptAdaptation

        adaptations = [PromptAdaptation(
            strategy=Strategy.EXPAND_DEP_CONTEXT,
            reason="high dep count",
        )]
        result = apply_adaptations(adaptations)
        assert len(result["adaptations_applied"]) == 1
        assert "high dep count" in result["adaptations_applied"][0]

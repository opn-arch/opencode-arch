"""Tests for UncertaintyResolver."""
import pytest
from architecture_model.pipeline.protocol import Evidence, Uncertainty
from architecture_model.pipeline.learning import LearningStore
from opencode_arch.agent.resolution import UncertaintyResolver


class TestUncertaintyResolver:
    def test_resolve_with_handler(self):
        def search_handler(u: Uncertainty) -> Evidence:
            return Evidence(source="search_result", confidence=0.8, raw="Found in utils.py")

        resolver = UncertaintyResolver(handlers={"search": search_handler})
        uncertainty = Uncertainty(
            category="dynamic_import",
            description="importlib in loader.py",
            suggested_fallback="search",
            priority="informational",
        )
        outcome = resolver.resolve(uncertainty)
        assert outcome is not None
        assert outcome.method == "search"
        assert outcome.resolution.source == "search_result"

    def test_resolve_returns_none_without_handler(self):
        resolver = UncertaintyResolver(handlers={})
        uncertainty = Uncertainty(
            category="dynamic_import",
            description="test",
            suggested_fallback="search",
            priority="informational",
        )
        outcome = resolver.resolve(uncertainty)
        assert outcome is None

    def test_resolve_uses_prior_from_learning_store(self, tmp_path):
        store = LearningStore(tmp_path / "learning")
        # Pre-populate with a resolution
        from architecture_model.pipeline.learning import ResolutionOutcome
        prior = ResolutionOutcome(
            uncertainty=Uncertainty(
                category="orphan_file", description="old.py",
                suggested_fallback="", priority="",
            ),
            resolution=Evidence(source="user_confirmation", confidence=1.0, raw="It's a script"),
            method="ask_user", attempts=1, duration_ms=100,
        )
        store.add_resolution(prior)

        resolver = UncertaintyResolver(learning_store=store)
        uncertainty = Uncertainty(
            category="orphan_file", description="new.py",
            suggested_fallback="ask_user", priority="blocking",
        )
        outcome = resolver.resolve(uncertainty)
        assert outcome is not None
        assert outcome.method == "ask_user"

    def test_resolve_all_batch(self):
        def always_resolve(u: Uncertainty) -> Evidence:
            return Evidence(source="llm_analysis", confidence=0.7, raw="resolved")

        resolver = UncertaintyResolver(handlers={"llm_analysis": always_resolve})
        uncertainties = [
            Uncertainty(category="ambiguous_module", description="x.py",
                       suggested_fallback="llm_analysis", priority="informational"),
            Uncertainty(category="ambiguous_module", description="y.py",
                       suggested_fallback="llm_analysis", priority="informational"),
        ]
        results = resolver.resolve_all(uncertainties)
        assert len(results) == 2

    def test_register_handler(self):
        resolver = UncertaintyResolver()
        resolver.register_handler("custom", lambda u: Evidence(source="test", confidence=1.0, raw="ok"))
        assert "custom" in resolver._handlers

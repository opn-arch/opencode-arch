"""Uncertainty resolution — dispatches pipeline uncertainties to LLM/search/user.

This is the MCP layer's responsibility: when the deterministic pipeline
produces uncertainties, this resolver attempts to resolve them using
the tools available to the agent (LLM analysis, codebase search, user queries).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from architecture_model.pipeline.protocol import Evidence, Uncertainty
from architecture_model.pipeline.learning import LearningStore, ResolutionOutcome


@dataclass
class ResolutionStrategy:
    """A strategy for resolving a category of uncertainty."""
    category: str
    methods: list[str]  # ordered: try first method, then second, etc.


# Default strategies per uncertainty category
DEFAULT_STRATEGIES: dict[str, list[str]] = {
    "dynamic_import": ["search", "llm_analysis"],
    "ambiguous_module": ["llm_analysis", "ask_user"],
    "orphan_file": ["search", "ask_user"],
    "missing_capability": ["llm_analysis", "ask_user"],
    "unclear_boundary": ["llm_analysis", "ask_user"],
}


class UncertaintyResolver:
    """Resolves pipeline uncertainties using available agent tools.

    The resolver tries strategies in order:
    1. Check if a prior resolution exists in the learning store
    2. Try automated methods (search, llm_analysis)
    3. Escalate to user if needed

    Resolution outcomes are stored for future reference.
    """

    def __init__(
        self,
        learning_store: LearningStore | None = None,
        strategies: dict[str, list[str]] | None = None,
        handlers: dict[str, Callable] | None = None,
    ):
        self._learning = learning_store
        self._strategies = strategies or DEFAULT_STRATEGIES
        self._handlers: dict[str, Callable] = handlers or {}

    def register_handler(self, method: str, handler: Callable) -> None:
        """Register a resolution handler for a method type.

        Handler signature: (uncertainty: Uncertainty) -> Evidence | None
        """
        self._handlers[method] = handler

    def resolve(self, uncertainty: Uncertainty) -> ResolutionOutcome | None:
        """Attempt to resolve an uncertainty.

        Returns ResolutionOutcome if resolved, None if unresolvable.
        """
        import time

        start = time.time()
        attempts = 0

        # Check prior resolutions
        if self._learning:
            prior = self._learning.get_resolutions(category=uncertainty.category)
            if prior:
                # Use most recent resolution for same category
                return prior[-1]

        # Try strategies in order
        methods = self._strategies.get(uncertainty.category, ["ask_user"])

        for method in methods:
            attempts += 1
            handler = self._handlers.get(method)
            if handler:
                evidence = handler(uncertainty)
                if evidence:
                    duration_ms = int((time.time() - start) * 1000)
                    outcome = ResolutionOutcome(
                        uncertainty=uncertainty,
                        resolution=evidence,
                        method=method,
                        attempts=attempts,
                        duration_ms=duration_ms,
                    )
                    # Persist
                    if self._learning:
                        self._learning.add_resolution(outcome)
                    return outcome

        return None

    def resolve_all(self, uncertainties: list[Uncertainty]) -> list[ResolutionOutcome]:
        """Resolve a batch of uncertainties. Returns successful resolutions."""
        results = []
        for u in uncertainties:
            outcome = self.resolve(u)
            if outcome:
                results.append(outcome)
        return results

    @property
    def unresolvable_categories(self) -> set[str]:
        """Categories that have no handler registered."""
        all_methods = set()
        for methods in self._strategies.values():
            all_methods.update(methods)
        return all_methods - set(self._handlers.keys())

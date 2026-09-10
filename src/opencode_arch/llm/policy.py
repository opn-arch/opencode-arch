"""B1.2.5 — Policy loader, routing rules, budget enforcement, fallback wrapping."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from architecture_model.llm import Completion, LLMProvider

from opencode_arch.llm import registry


class BudgetExceeded(RuntimeError):
    pass


class TransientProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskClass:
    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", name)


@dataclass(frozen=True)
class RoutingRule:
    task_class: TaskClass
    provider: str
    model: str
    max_cost_usd_per_call: float
    fallback: tuple[str, ...]


@dataclass(frozen=True)
class ProjectorRule:
    """Per-projector routing override (Phase 4 Task 20).

    Only carries the two knobs the plan calls out: which task class to
    resolve, and the projector-specific cost cap. Callers combine
    ``task_class`` with :meth:`Policy.pick` to obtain the actual provider.
    """

    task_class: str
    max_cost_usd_per_call: float


class _FallbackProvider:
    """Wraps a primary provider + ordered fallbacks. Catches TransientProviderError."""

    def __init__(self, primary: LLMProvider, fallbacks: tuple[LLMProvider, ...]) -> None:
        self._primary = primary
        self._fallbacks = fallbacks
        self.name = primary.name

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Completion:
        last_err: Exception | None = None
        for p in (self._primary, *self._fallbacks):
            try:
                return p.complete(
                    prompt, model=model, max_tokens=max_tokens, temperature=temperature
                )
            except TransientProviderError as e:
                last_err = e
                continue
        raise last_err or TransientProviderError("all providers failed")

    def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        yield self.complete(
            prompt, model=model, max_tokens=max_tokens, temperature=temperature
        )["text"]

    def structured(self, prompt: str, schema: dict, *, model: str | None = None) -> dict:
        import json

        c = self.complete(prompt + "\n\nRespond in JSON only.", model=model)
        return json.loads(c["text"])

    def tokenize(self, text: str) -> int:
        return self._primary.tokenize(text)


@dataclass
class Policy:
    rules: dict[TaskClass, RoutingRule]
    global_budget_usd: float
    retry_backoff: tuple[float, ...]
    projector_rules: dict[str, ProjectorRule] = field(default_factory=dict)
    _spent: dict[str, float] = field(default_factory=dict)

    def spend(self, provider_name: str, amount_usd: float) -> None:
        # Semantics: raise if the pre-existing recorded total already exceeds
        # the global budget. Otherwise record and allow. This matches the plan
        # test where two calls (0.6 + 0.5) are allowed to record and the third
        # (0.01) raises because 1.1 >= 1.0.
        current_total = sum(self._spent.values())
        if current_total >= self.global_budget_usd:
            raise BudgetExceeded(
                f"budget {self.global_budget_usd} exhausted (spent {current_total})"
            )
        self._spent[provider_name] = self._spent.get(provider_name, 0.0) + amount_usd

    def pick(self, task: TaskClass) -> LLMProvider:
        rule = self.rules[task]
        primary = registry.get_provider(rule.provider)
        fallbacks = tuple(registry.get_provider(n) for n in rule.fallback)
        return _FallbackProvider(primary, fallbacks)

    def resolve_projector(self, projector_name: str) -> ProjectorRule | None:
        """Return the routing override for ``projector_name``.

        Lookup order: exact projector name → ``"default"`` entry → ``None``.
        Returning ``None`` signals to the caller that no per-projector rule
        applies and the caller-supplied task class should be used verbatim.
        """
        if projector_name in self.projector_rules:
            return self.projector_rules[projector_name]
        if "default" in self.projector_rules:
            return self.projector_rules["default"]
        return None


def load_policy(repo_path: Path) -> Policy:
    import yaml

    path = Path(repo_path) / ".architecture" / "llm" / "policy.yaml"
    data = yaml.safe_load(path.read_text()) or {}
    rules_raw = data.get("rules", {}) or {}
    rules: dict[TaskClass, RoutingRule] = {}
    for name, spec in rules_raw.items():
        tc = TaskClass(name)
        rules[tc] = RoutingRule(
            task_class=tc,
            provider=spec["provider"],
            model=spec["model"],
            max_cost_usd_per_call=float(spec["max_cost_usd_per_call"]),
            fallback=tuple(spec.get("fallback", []) or []),
        )
    return Policy(
        rules=rules,
        global_budget_usd=float(data.get("global_budget_usd", 0.0)),
        retry_backoff=tuple(data.get("retry_backoff", []) or []),
        projector_rules={
            name: ProjectorRule(
                task_class=str(spec["task_class"]),
                max_cost_usd_per_call=float(spec["max_cost_usd_per_call"]),
            )
            for name, spec in (data.get("projector_rules", {}) or {}).items()
        },
    )

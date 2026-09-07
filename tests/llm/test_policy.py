"""B1.2.5 — Policy loader, registry, fallback wrapper."""
from __future__ import annotations

import pytest


def test_policy_loads_yaml_and_picks_provider(tmp_path, monkeypatch):
    (tmp_path / ".architecture" / "llm").mkdir(parents=True)
    (tmp_path / ".architecture" / "llm" / "policy.yaml").write_text("""
rules:
  synthesis:
    provider: mcp
    model: opencode-default
    max_cost_usd_per_call: 0.10
    fallback: [frontier]
  classification:
    provider: frontier
    model: claude-4.7
    max_cost_usd_per_call: 0.02
    fallback: []
global_budget_usd: 10.0
retry_backoff: [0.5, 2.0, 8.0]
""")
    # Ensure FrontierProvider construction (used as fallback in synthesis) does not fail
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from opencode_arch.llm.policy import load_policy, TaskClass
    from opencode_arch.llm import registry
    registry.clear_cache()
    p = load_policy(tmp_path)
    prov = p.pick(TaskClass("synthesis"))
    assert prov.name == "mcp"
    registry.clear_cache()


def test_policy_budget_enforced():
    from opencode_arch.llm.policy import Policy, RoutingRule, TaskClass, BudgetExceeded
    tc = TaskClass("x")
    p = Policy(
        rules={tc: RoutingRule(tc, "mcp", "m", 0.5, ())},
        global_budget_usd=1.0,
        retry_backoff=(0.0,),
    )
    p.spend("mcp", 0.6)
    p.spend("mcp", 0.5)
    with pytest.raises(BudgetExceeded):
        p.spend("mcp", 0.01)


def test_policy_fallback_on_transient_error(monkeypatch):
    """Primary raises TransientProviderError; fallback succeeds."""
    from opencode_arch.llm.policy import (
        Policy,
        RoutingRule,
        TaskClass,
        TransientProviderError,
    )
    from opencode_arch.llm import registry
    from architecture_model.llm import LLMProvider

    registry.clear_cache()

    class _Primary:
        name = "primary"
        def complete(self, prompt, **kw):
            raise TransientProviderError("boom")
        def stream(self, prompt, **kw):
            yield ""
        def structured(self, prompt, schema, **kw):
            return {}
        def tokenize(self, t):
            return 0

    class _Fallback:
        name = "fallback"
        def complete(self, prompt, **kw):
            return {
                "text": "ok",
                "tokens_prompt": 1,
                "tokens_completion": 1,
                "model": "f",
                "finish_reason": "stop",
            }
        def stream(self, prompt, **kw):
            yield "ok"
        def structured(self, prompt, schema, **kw):
            return {}
        def tokenize(self, t):
            return 0

    registry._CACHE["primary"] = _Primary()
    registry._CACHE["fallback"] = _Fallback()

    tc = TaskClass("x")
    p = Policy(
        rules={tc: RoutingRule(tc, "primary", "m", 0.5, ("fallback",))},
        global_budget_usd=10.0,
        retry_backoff=(0.0,),
    )
    provider = p.pick(tc)
    assert isinstance(provider, LLMProvider)
    result = provider.complete("hi")
    assert result["text"] == "ok"
    registry.clear_cache()

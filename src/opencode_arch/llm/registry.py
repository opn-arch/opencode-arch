"""Provider registry with cached instantiation."""
from __future__ import annotations

from architecture_model.llm import LLMProvider

_CACHE: dict[str, LLMProvider] = {}


def get_provider(name: str) -> LLMProvider:
    if name in _CACHE:
        return _CACHE[name]
    if name == "mcp":
        from opencode_arch.llm.providers.mcp import MCPProvider
        p: LLMProvider = MCPProvider()
    elif name == "frontier":
        from opencode_arch.llm.providers.frontier import FrontierProvider
        p = FrontierProvider()
    elif name == "relay-ext":
        from opencode_arch.llm.providers.relay_ext import RelayExtProvider
        p = RelayExtProvider()
    else:
        raise KeyError(f"unknown provider: {name}")
    _CACHE[name] = p
    return p


def clear_cache() -> None:
    _CACHE.clear()

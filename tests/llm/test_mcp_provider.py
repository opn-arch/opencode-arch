def test_mcp_provider_name():
    from opencode_arch.llm.providers.mcp import MCPProvider
    assert MCPProvider().name == "mcp"


def test_mcp_provider_tokenize_uses_tiktoken_or_fallback():
    from opencode_arch.llm.providers.mcp import MCPProvider
    n = MCPProvider().tokenize("one two three")
    assert n >= 3

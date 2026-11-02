def test_mcp_provider_name():
    from opencode_arch.llm.providers.mcp import MCPProvider
    assert MCPProvider().name == "mcp"


def test_mcp_provider_tokenize_uses_tiktoken_or_fallback():
    from opencode_arch.llm.providers.mcp import MCPProvider
    n = MCPProvider().tokenize("one two three")
    assert n >= 3


def test_extract_json_plain():
    from opencode_arch.llm.providers.mcp import _extract_json
    assert _extract_json('{"ops": []}') == {"ops": []}


def test_extract_json_fenced():
    from opencode_arch.llm.providers.mcp import _extract_json
    text = 'Here is the patch:\n```json\n{"ops": [1]}\n```\nDone.'
    assert _extract_json(text) == {"ops": [1]}


def test_extract_json_prose_wrapped():
    from opencode_arch.llm.providers.mcp import _extract_json
    assert _extract_json('sure! {"ops": [2]} hope that helps') == {"ops": [2]}


def test_extract_json_no_object_raises():
    import pytest
    from opencode_arch.llm.providers.mcp import _extract_json
    with pytest.raises(ValueError):
        _extract_json("no json here")


def test_invoke_works_inside_running_event_loop(monkeypatch):
    """Regression: _invoke must not raise when a loop is already running.

    Reproduces the arch_learn_approve nesting bug where the proposer is
    reached transitively from inside an async MCP tool's event loop.
    """
    import asyncio
    import types

    from opencode_arch.llm.providers import mcp as mcp_mod

    class _FakeResult:
        success = True
        output = '{"ops": []}'

    class _FakeRunner:
        def __init__(self, *a, **k):
            pass

        async def run(self, prompt, repo_path="."):
            return _FakeResult()

    monkeypatch.setattr(
        mcp_mod,
        "OpencodeRunner",
        _FakeRunner,
        raising=False,
    )
    # Patch the lazily-imported symbol at its source module too.
    import opencode_arch.runner.opencode as runner_mod
    monkeypatch.setattr(runner_mod, "OpencodeRunner", _FakeRunner)

    async def _driver():
        # We are now inside a running event loop; the old asyncio.run()
        # path would raise RuntimeError here.
        return mcp_mod.MCPProvider().structured("prompt", {"ops": []})

    result = asyncio.run(_driver())
    assert result == {"ops": []}


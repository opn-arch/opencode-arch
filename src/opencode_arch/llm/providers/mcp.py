"""In-process LLMProvider adapter — default when no policy override."""
from __future__ import annotations

from typing import Iterator

from openag.llm import Completion, LLMProvider


def _run_coro_sync(coro):
    """Drive ``coro`` to completion from sync code, loop-context-safe.

    ``asyncio.run`` cannot be called while an event loop is already running
    (e.g. when this provider is reached transitively from an async MCP tool
    such as ``arch_learn_approve``). When a running loop is detected, the
    coroutine is executed to completion on a dedicated worker thread that owns
    its own event loop; otherwise it runs inline via ``asyncio.run``.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


def _extract_json(text: str) -> dict:
    """Parse a JSON object from raw model output, tolerating fences/prose.

    ``opencode run`` stdout commonly wraps JSON in ``` fences or surrounds it
    with prose. This tries a direct parse first, then a fenced-block parse,
    then a first-``{`` to last-``}`` slice. Raises ``ValueError`` if no JSON
    object can be recovered.
    """
    import json
    import re

    s = (text or "").strip()
    try:
        return json.loads(s)
    except Exception:
        pass

    fence = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass

    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except Exception:
            pass

    raise ValueError(f"no JSON object found in provider output: {s[:200]!r}")


class MCPProvider:
    name = "mcp"

    def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Completion:
        # Delegates to whatever runner is active in-session; for tests, the
        # fixture harness monkeypatches _invoke().
        return self._invoke(prompt, model, max_tokens, temperature)

    def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Iterator[str]:
        yield self.complete(
            prompt, model=model, max_tokens=max_tokens, temperature=temperature
        )["text"]

    def structured(self, prompt, schema, *, model=None) -> dict:
        c = self.complete(prompt + "\n\nRespond in JSON only.", model=model)
        return _extract_json(c["text"])

    def tokenize(self, text: str) -> int:
        try:
            import tiktoken  # type: ignore

            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text.split()))

    def _invoke(self, prompt, model, max_tokens, temperature) -> Completion:
        """Delegates to OpencodeRunner subprocess. May raise on runner failure."""
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(model=model)
        result = _run_coro_sync(runner.run(prompt, repo_path="."))
        if not result.success:
            from opencode_arch.llm.policy import TransientProviderError
            raise TransientProviderError(f"opencode run failed: {result.output[:200]}")
        text = result.output
        return {
            "text": text,
            "tokens_prompt": self.tokenize(prompt),
            "tokens_completion": self.tokenize(text),
            "model": model or "opencode-default",
            "finish_reason": "stop",
        }


# runtime-checkable Protocol satisfied by structural typing
assert isinstance(MCPProvider(), LLMProvider)

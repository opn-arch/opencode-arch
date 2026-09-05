"""In-process LLMProvider adapter — default when no policy override."""
from __future__ import annotations

from typing import Iterator

from architecture_model.llm import Completion, LLMProvider


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
        import json

        c = self.complete(prompt + "\n\nRespond in JSON only.", model=model)
        return json.loads(c["text"])

    def tokenize(self, text: str) -> int:
        try:
            import tiktoken  # type: ignore

            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text.split()))

    def _invoke(self, prompt, model, max_tokens, temperature) -> Completion:
        """Delegates to OpencodeRunner subprocess. May raise on runner failure."""
        import asyncio
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(model=model)
        result = asyncio.run(runner.run(prompt, repo_path="."))
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

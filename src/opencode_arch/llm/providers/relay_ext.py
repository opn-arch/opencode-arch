"""Relay-based LLMProvider adapter (new protocol shape).

Coexists with legacy ``opencode_arch.llm.relay`` module (SSE-based). This
adapter targets a simpler JSON POST /chat protocol and conforms to the
``LLMProvider`` Protocol.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Iterator

from architecture_model.llm import Completion, LLMProvider


class RelayExtProvider:
    name = "relay-ext"

    def __init__(self, *, base_url: str | None = None) -> None:
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = os.environ.get("OPENCODE_RELAY_URL", "http://localhost:8400")

    def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Completion:
        body = json.dumps({
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return {
            "text": resp["text"],
            "tokens_prompt": resp["tokens_prompt"],
            "tokens_completion": resp["tokens_completion"],
            "model": resp["model"],
            "finish_reason": resp["finish_reason"],
        }

    def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Iterator[str]:
        yield self.complete(
            prompt, model=model, max_tokens=max_tokens, temperature=temperature
        )["text"]

    def structured(self, prompt, schema, *, model=None) -> dict:
        c = self.complete(prompt + "\n\nRespond in JSON only.", model=model)
        return json.loads(c["text"])

    def tokenize(self, text: str) -> int:
        try:
            import tiktoken  # type: ignore

            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text.split()))


assert isinstance(RelayExtProvider(), LLMProvider)

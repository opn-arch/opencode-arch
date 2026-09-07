"""Frontier LLM provider (Anthropic + OpenAI) via urllib."""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Iterator

from architecture_model.llm import Completion


_ANTHROPIC_STOP_MAP = {
    "end_turn": "stop",
    "max_tokens": "length",
    "tool_use": "tool_use",
}


class FrontierProvider:
    name = "frontier"

    def __init__(self) -> None:
        anth = os.environ.get("ANTHROPIC_API_KEY")
        oai = os.environ.get("OPENAI_API_KEY")
        if anth:
            self.backend = "anthropic"
            self._api_key = anth
        elif oai:
            self.backend = "openai"
            self._api_key = oai
        else:
            raise RuntimeError("no available API key (set ANTHROPIC_API_KEY or OPENAI_API_KEY)")

    def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Completion:
        if self.backend == "anthropic":
            return self._complete_anthropic(prompt, model, max_tokens, temperature)
        return self._complete_openai(prompt, model, max_tokens, temperature)

    def _complete_anthropic(self, prompt, model, max_tokens, temperature) -> Completion:
        model_name = model or "claude-3-5-sonnet-latest"
        body = json.dumps({
            "model": model_name,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode("utf-8"))
        stop = resp.get("stop_reason", "")
        finish = _ANTHROPIC_STOP_MAP.get(stop, "content_filter")
        return {
            "text": resp["content"][0]["text"],
            "tokens_prompt": resp["usage"]["input_tokens"],
            "tokens_completion": resp["usage"]["output_tokens"],
            "model": resp.get("model", model_name),
            "finish_reason": finish,
        }

    def _complete_openai(self, prompt, model, max_tokens, temperature) -> Completion:
        model_name = model or "gpt-4o"
        body = json.dumps({
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return {
            "text": resp["choices"][0]["message"]["content"],
            "tokens_prompt": resp["usage"]["prompt_tokens"],
            "tokens_completion": resp["usage"]["completion_tokens"],
            "model": resp.get("model", model_name),
            "finish_reason": resp["choices"][0]["finish_reason"],
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


# Structural Protocol check skipped: instantiation requires API key in env.

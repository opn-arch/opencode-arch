"""MockProvider for write-back projector tests.

Matches prompts by SHA-256 hash and returns canned responses. Any
unregistered prompt raises ``KeyError`` — tests must be explicit about
which prompts they intend to send.

Response key conventions (deterministic, so tests can pre-compute):

* ``complete(prompt)``     → ``responses[sha256(prompt)]``  (dict → Completion)
* ``structured(prompt, …)``→ ``responses[sha256(prompt) + ":structured"]``  (dict)
* ``stream(prompt)``       → ``responses[sha256(prompt) + ":stream"]``  (iterable[str])
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterator


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class MockProvider:
    """Test-only LLMProvider with hash-keyed canned responses.

    Parameters
    ----------
    responses:
        Mapping of prompt-hash (optionally suffixed with ``":structured"``
        or ``":stream"``) to canned response payloads.
    """

    name = "mock"

    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses: dict[str, Any] = dict(responses)

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> dict:
        key = _sha(prompt)
        if key not in self._responses:
            raise KeyError(
                f"MockProvider: no canned response for prompt hash {key} "
                f"(prompt: {prompt[:60]!r}...)"
            )
        return dict(self._responses[key])

    def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        key = _sha(prompt) + ":stream"
        if key not in self._responses:
            raise KeyError(
                f"MockProvider: no canned stream for prompt hash {_sha(prompt)}"
            )
        yield from self._responses[key]

    def structured(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str | None = None,
    ) -> dict:
        key = _sha(prompt) + ":structured"
        if key not in self._responses:
            raise KeyError(
                f"MockProvider: no canned structured response for prompt hash "
                f"{_sha(prompt)}"
            )
        return dict(self._responses[key])

    def tokenize(self, text: str) -> int:
        return len(text.split())

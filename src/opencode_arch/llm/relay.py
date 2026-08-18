"""Copilot-relay LLM client for pipeline enrichment.

Calls the copilot-relay SSE endpoint (POST /chat) and collects
streamed chunks into a complete response string.
"""

from __future__ import annotations

import json
import logging
import os
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

DEFAULT_RELAY_URL = os.environ.get("COPILOT_RELAY_URL", "http://localhost:8400")


def _chat_sync(
    content: str,
    system_prompt: str | None = None,
    relay_url: str = DEFAULT_RELAY_URL,
    timeout: int = 30,
) -> str:
    """Synchronous call to copilot-relay /chat endpoint.

    Parses SSE stream and returns concatenated content chunks.
    """
    body: dict[str, str] = {"content": content}
    if system_prompt:
        body["system_prompt"] = system_prompt

    data = json.dumps(body).encode("utf-8")
    req = Request(
        f"{relay_url}/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            chunks: list[str] = []
            for line_bytes in resp:
                line = line_bytes.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "chunk":
                    chunks.append(event.get("content", ""))
                elif event.get("type") == "done":
                    break
            return "".join(chunks)
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("Copilot-relay call failed: %s", exc)
        return ""


async def relay_llm_callback(stage: str, prompt: str, context: dict | None = None) -> str | None:
    """Async LLM callback compatible with PipelineContext.llm_callback.

    Signature: async (stage: str, prompt: str, context: dict) -> str
    Wraps the synchronous relay call.
    """
    system_prompt = (
        "You are an expert software architect analyzing code structure. "
        "Respond with ONLY the requested output — no explanations, no markdown, "
        "no quotes, no prefixes. Just the raw answer."
    )
    result = _chat_sync(prompt, system_prompt=system_prompt)
    if result and result.strip():
        logger.info("LLM enrichment [%s]: %s → %s", stage, prompt[:60], result[:60])
        return result.strip()
    return None


def is_relay_available(relay_url: str = DEFAULT_RELAY_URL) -> bool:
    """Check if the copilot-relay is running and healthy."""
    try:
        req = Request(f"{relay_url}/health", method="GET")
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False

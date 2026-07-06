"""Copilot-relay SSE adapter for oracle scoring.

copilot-relay is a local SSE server at http://localhost:8400 that proxies
requests to a frontier model (e.g., Claude) via GitHub Copilot.

API:
    POST /chat  {"content": "user msg", "system": "system prompt"}
    Response: SSE stream with data: {"type": "chunk", "content": "..."} lines
              ending with data: {"type": "done"}
"""
from __future__ import annotations

import json
from typing import Any

import aiohttp


class CopilotRelayOracle:
    """Oracle that scores architecture extractions via copilot-relay."""

    def __init__(self, host: str = "http://localhost:8400", timeout: float = 180.0):
        self._host = host
        self._timeout = timeout

    async def generate(self, system: str, user: str) -> str:
        """Send a prompt to copilot-relay and return the full response.

        Compatible with Surrogate.generate_with_prompt(system, user) -> str.
        """
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {"content": user, "system": system}
            async with session.post(f"{self._host}/chat", json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"copilot-relay returned {resp.status}")

                chunks: list[str] = []
                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if not decoded.startswith("data: "):
                        continue
                    data = json.loads(decoded[6:])
                    if data.get("type") == "chunk":
                        chunks.append(data.get("content", ""))
                    elif data.get("type") == "done":
                        break
                    elif data.get("type") == "error":
                        raise RuntimeError(f"copilot-relay error: {data}")

                return "".join(chunks)

    async def score_extraction(
        self,
        model_yaml: str,
        source_code: str,
        scoring_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Score an architecture extraction against source code.

        Returns: {"score": int (0-100), "feedback": str}
        """
        system = scoring_prompt or (
            "You are an architecture extraction quality scorer. "
            "Score the given YAML architecture model against the source code on a scale of 0-100. "
            'Return ONLY a JSON object: {"score": <int>, "feedback": "<brief explanation>"}'
        )
        user_msg = (
            f"## Architecture Model (YAML)\n```yaml\n{model_yaml}\n```\n\n"
            f"## Source Code\n```python\n{source_code[:8000]}\n```\n\n"
            "Score this extraction for completeness, accuracy, and structural correctness."
        )

        raw = await self.generate(system, user_msg)

        # Parse JSON from response (may have markdown fences)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"score": 0, "feedback": f"Failed to parse oracle response: {text[:200]}"}

"""Tests for the copilot-relay oracle adapter."""
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from opencode_arch.oracle.copilot_relay import CopilotRelayOracle


class AsyncIterLines:
    """Helper to mock async iteration over response content lines."""

    def __init__(self, lines: list[bytes]):
        self._lines = lines
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._index]
        self._index += 1
        return line


@pytest.fixture
def oracle():
    return CopilotRelayOracle(host="http://localhost:8400")


class TestCopilotRelayOracle:
    def test_init_default_host(self):
        oracle = CopilotRelayOracle()
        assert oracle._host == "http://localhost:8400"

    def test_init_custom_host(self):
        oracle = CopilotRelayOracle(host="http://custom:9000")
        assert oracle._host == "http://custom:9000"

    @pytest.mark.asyncio
    async def test_generate_parses_sse_stream(self, oracle):
        """Oracle should parse SSE stream and concatenate chunk contents."""
        # Mock the aiohttp session and response
        mock_lines = [
            b'data: {"type": "chunk", "content": "Hello"}\n',
            b'data: {"type": "chunk", "content": " world"}\n',
            b'data: {"type": "done"}\n',
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content = AsyncIterLines(mock_lines)

        mock_session = AsyncMock()
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_ctx)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            result = await oracle.generate("system prompt", "user message")
            assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_handles_error_event(self, oracle):
        """Oracle should raise on error events."""
        mock_lines = [
            b'data: {"type": "error", "message": "rate limited"}\n',
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content = AsyncIterLines(mock_lines)

        mock_session = AsyncMock()
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_ctx)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            with pytest.raises(RuntimeError, match="copilot-relay error"):
                await oracle.generate("sys", "user")

    @pytest.mark.asyncio
    async def test_generate_handles_non_200(self, oracle):
        """Oracle should raise on non-200 status."""
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = AsyncMock()
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_post_ctx)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            with pytest.raises(RuntimeError, match="500"):
                await oracle.generate("sys", "user")

    @pytest.mark.asyncio
    async def test_score_extraction(self, oracle):
        """Score method should return a dict with score and feedback."""
        with patch.object(oracle, "generate", return_value='{"score": 85, "feedback": "Good coverage"}'):
            result = await oracle.score_extraction(
                model_yaml="entities: []",
                source_code="def foo(): pass"
            )
            assert result["score"] == 85
            assert "Good" in result["feedback"]

    @pytest.mark.asyncio
    async def test_score_extraction_strips_markdown_fences(self, oracle):
        """Score should handle markdown-wrapped JSON responses."""
        with patch.object(oracle, "generate", return_value='```json\n{"score": 90, "feedback": "Great"}\n```'):
            result = await oracle.score_extraction(
                model_yaml="entities: []",
                source_code="def foo(): pass"
            )
            assert result["score"] == 90

    @pytest.mark.asyncio
    async def test_score_extraction_handles_parse_error(self, oracle):
        """Score should return score=0 on unparseable oracle response."""
        with patch.object(oracle, "generate", return_value="This is not JSON"):
            result = await oracle.score_extraction(
                model_yaml="entities: []",
                source_code="def foo(): pass"
            )
            assert result["score"] == 0
            assert "Failed to parse" in result["feedback"]

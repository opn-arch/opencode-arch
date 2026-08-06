"""Tests for LLM-assisted requirement extraction."""
import json
from pathlib import Path

import pytest

from opencode_arch.requirements.llm_extractor import extract_requirements_llm
from opencode_arch.llm.cache import LLMCache
from opencode_arch.runner.base import RunResult


class MockRunner:
    def __init__(self, responses=None):
        self.responses = list(responses or ['{"requirements": []}'])
        self._idx = 0
        self.call_count = 0

    async def run(self, prompt, repo_path):
        self.call_count += 1
        resp = self.responses[min(self._idx, len(self.responses) - 1)]
        self._idx += 1
        return RunResult(output=resp, exit_code=0, success=True)


@pytest.fixture
def tmp_doc(tmp_path):
    def _write(content: str) -> Path:
        p = tmp_path / "reqs.md"
        p.write_text(content)
        return p
    return _write


class TestLLMExtraction:
    @pytest.mark.asyncio
    async def test_valid_json_parsed(self, tmp_doc):
        doc = tmp_doc("The system should handle authentication and logging.")
        response = json.dumps({"requirements": [
            {"id": "REQ-001", "text": "Handle authentication", "anchor": "L1"},
            {"id": "REQ-002", "text": "Handle logging", "anchor": "L1"},
        ]})
        runner = MockRunner([response])
        results = await extract_requirements_llm(doc, runner)
        assert len(results) == 2
        assert results[0].id == "REQ-001"
        assert results[0].extraction_method == "llm"
        assert runner.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_response(self, tmp_doc):
        doc = tmp_doc("Nothing here.")
        runner = MockRunner(['{"requirements": []}'])
        results = await extract_requirements_llm(doc, runner)
        assert results == []

    @pytest.mark.asyncio
    async def test_cached_skips_runner(self, tmp_doc, tmp_path):
        doc = tmp_doc("Some content for caching test.")
        response = json.dumps({"requirements": [
            {"id": "REQ-001", "text": "Cached req", "anchor": "L1"},
        ]})
        runner = MockRunner([response])
        cache = LLMCache(cache_dir=tmp_path / "cache")

        # First call populates cache
        r1 = await extract_requirements_llm(doc, runner, cache=cache)
        assert len(r1) == 1
        assert runner.call_count == 1

        # Second call uses cache
        r2 = await extract_requirements_llm(doc, runner, cache=cache)
        assert len(r2) == 1
        assert runner.call_count == 1  # Not incremented

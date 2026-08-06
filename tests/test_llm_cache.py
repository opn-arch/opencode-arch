"""Tests for LLM cache layer."""
import pytest
from opencode_arch.llm.cache import LLMCache, CachedResult, hash_content, cached_llm_call
from opencode_arch.runner.base import RunResult


class MockRunner:
    def __init__(self, output="mock output"):
        self.output = output
        self.call_count = 0

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        self.call_count += 1
        return RunResult(output=self.output, exit_code=0, success=True)


@pytest.mark.asyncio
async def test_cache_miss_calls_runner(tmp_path):
    cache = LLMCache(cache_dir=tmp_path / "cache")
    runner = MockRunner(output="llm response")
    result = await cached_llm_call(
        runner, "prompt", "ch1", "ph1", "/repo", cache=cache
    )
    assert runner.call_count == 1
    assert result.cached is False
    assert result.output == "llm response"


@pytest.mark.asyncio
async def test_cache_hit_skips_runner(tmp_path):
    cache = LLMCache(cache_dir=tmp_path / "cache")
    cache.put("ch1", "ph1", "cached response", "model-x")
    runner = MockRunner()
    result = await cached_llm_call(
        runner, "prompt", "ch1", "ph1", "/repo", cache=cache
    )
    assert runner.call_count == 0
    assert result.cached is True
    assert result.output == "cached response"


def test_different_prompt_hash_is_miss(tmp_path):
    cache = LLMCache(cache_dir=tmp_path / "cache")
    cache.put("ch1", "ph_A", "response A", "model")
    assert cache.get("ch1", "ph_B") is None


def test_clear_removes_files(tmp_path):
    cache = LLMCache(cache_dir=tmp_path / "cache")
    cache.put("c1", "p1", "out1", "m")
    cache.put("c2", "p2", "out2", "m")
    cache.put("c3", "p3", "out3", "m")
    assert cache.clear() == 3
    assert cache.get("c1", "p1") is None


def test_hash_content():
    h1 = hash_content("hello")
    h2 = hash_content("hello")
    h3 = hash_content("world")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64

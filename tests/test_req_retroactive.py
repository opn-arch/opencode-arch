"""Tests for retroactive requirement derivation."""
import json

import pytest

from opencode_arch.requirements.retroactive import derive_requirements_retroactive
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


MODEL_YAML = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  capabilities:
    - id: CAP-S1
      name: User Authentication
      status: ACTIVE
  components:
    - id: COMP-1
      name: AuthService
      status: ACTIVE
"""


class TestRetroactiveDerivation:
    @pytest.mark.asyncio
    async def test_model_with_capabilities(self):
        response = json.dumps({"requirements": [
            {"id": "REQ-001", "text": "System shall authenticate users", "source": "CAP-S1"},
            {"id": "REQ-002", "text": "System shall manage auth service", "source": "COMP-1"},
        ]})
        runner = MockRunner([response])
        results = await derive_requirements_retroactive(MODEL_YAML, runner)
        assert len(results) == 2
        assert results[0].id == "REQ-001"
        assert results[0].extraction_method == "retroactive"
        assert results[0].source_doc == "model"
        assert runner.call_count == 1

    @pytest.mark.asyncio
    async def test_cached_skips_runner(self, tmp_path):
        response = json.dumps({"requirements": [
            {"id": "REQ-001", "text": "Derived requirement", "source": "CAP-S1"},
        ]})
        runner = MockRunner([response])
        cache = LLMCache(cache_dir=tmp_path / "cache")

        r1 = await derive_requirements_retroactive(MODEL_YAML, runner, cache=cache)
        assert len(r1) == 1
        assert runner.call_count == 1

        r2 = await derive_requirements_retroactive(MODEL_YAML, runner, cache=cache)
        assert len(r2) == 1
        assert runner.call_count == 1  # Cached

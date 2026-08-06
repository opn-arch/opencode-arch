"""Tests for LLM functional-decomposition audit tool."""
import json
import pytest
from opencode_arch.runner.base import RunResult


STAGE1_RESPONSE = json.dumps({
    "blocks": [
        {"id": "LLM-A", "name": "Core Engine", "files": ["src/core.py", "src/engine.py"], "rationale": "Core processing logic"},
        {"id": "LLM-B", "name": "API Layer", "files": ["src/api.py", "src/routes.py"], "rationale": "HTTP interface"},
    ]
})

STAGE2_RESPONSE = json.dumps({
    "agreement_rate": 0.85,
    "matched_pairs": [
        {"tool_source_block": "S1", "llm_block": "LLM-A", "overlap": 0.9, "verdict": "agree"}
    ],
    "disagreements": [],
})


class MockRunner:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.call_count = 0

    async def run(self, prompt, repo_path):
        self.call_count += 1
        output = next(self.responses)
        return RunResult(output=output, exit_code=0, success=True)


def _make_repo(tmp_path):
    """Create a minimal repo with model and source files."""
    # Model YAML
    model_yaml = """meta:
  project: test-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Core
      status: ACTIVE
  capabilities:
    - id: CAP-S1
      name: Processing
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-S1
    type: realizes
"""
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)

    # Source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "core.py").write_text("def process(): pass\ndef transform(): pass\n")
    (src / "api.py").write_text("from src.core import process\ndef handle(): pass\n")

    # Context file
    (tmp_path / "CONTEXT.md").write_text("# Test Project\nA test project.")

    return model_yaml


@pytest.mark.asyncio
async def test_audit_produces_two_stages(tmp_path):
    _make_repo(tmp_path)
    runner = MockRunner([STAGE1_RESPONSE, STAGE2_RESPONSE])

    from opencode_arch.mcp.tools.llm_audit import run_llm_audit
    result = await run_llm_audit(repo_path=str(tmp_path), _runner=runner)

    assert "llm_decomposition" in result
    assert "comparison" in result
    assert result["llm_decomposition"]["blocks"][0]["id"] == "LLM-A"
    assert result["comparison"]["agreement_rate"] == 0.85


@pytest.mark.asyncio
async def test_audit_writes_output_file(tmp_path):
    _make_repo(tmp_path)
    runner = MockRunner([STAGE1_RESPONSE, STAGE2_RESPONSE])

    from opencode_arch.mcp.tools.llm_audit import run_llm_audit
    await run_llm_audit(repo_path=str(tmp_path), _runner=runner)

    output_file = tmp_path / ".architecture-models" / "llm-audit.json"
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert "llm_decomposition" in data
    assert "comparison" in data


@pytest.mark.asyncio
async def test_audit_cached_skips_runner(tmp_path):
    from opencode_arch.llm.cache import LLMCache, hash_content
    from opencode_arch.llm.prompts.audit import AUDIT_STAGE1_VERSION, AUDIT_STAGE2_VERSION

    _make_repo(tmp_path)
    runner = MockRunner([])  # Empty — should never be called

    cache = LLMCache(cache_dir=tmp_path / "llm-cache")

    # We need to pre-populate cache with the exact hashes the tool will compute.
    # To do that, run once without cache to see what happens, then pre-populate.
    # Instead, we'll just run with a fresh runner and cache, then run again.
    runner1 = MockRunner([STAGE1_RESPONSE, STAGE2_RESPONSE])

    from opencode_arch.mcp.tools.llm_audit import run_llm_audit
    await run_llm_audit(repo_path=str(tmp_path), _runner=runner1, _cache=cache)
    assert runner1.call_count == 2

    # Second run with same cache — should skip runner
    runner2 = MockRunner([])  # No responses needed
    result = await run_llm_audit(repo_path=str(tmp_path), _runner=runner2, _cache=cache)
    assert runner2.call_count == 0
    assert "llm_decomposition" in result


@pytest.mark.asyncio
async def test_audit_bad_path():
    from opencode_arch.mcp.tools.llm_audit import run_llm_audit
    runner = MockRunner([])
    result = await run_llm_audit(repo_path="/nonexistent/path/xyz", _runner=runner)
    assert "error" in result

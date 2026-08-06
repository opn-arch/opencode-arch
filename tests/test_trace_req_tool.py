"""Tests for architect_trace_requirements MCP tool."""
import json

import pytest

from opencode_arch.mcp.tools.trace_requirements import trace_requirements
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
  components:
    - id: COMP-1
      name: AuthService
      status: ACTIVE
  capabilities:
    - id: CAP-S1
      name: Authentication
      status: ACTIVE
"""


class TestWithStructuredDoc:
    @pytest.mark.asyncio
    async def test_structured_requirements_traced(self, tmp_path):
        # Write requirements doc
        req_doc = tmp_path / "requirements.md"
        req_doc.write_text("REQ-001: System shall authenticate users\nREQ-002: System shall log events\n")

        # Write model
        (tmp_path / ".architecture-model.yaml").write_text(MODEL_YAML)

        # Mock runner for matching step
        match_resp = json.dumps({"matches": [
            {"function_id": "COMP-1", "requirement_id": "REQ-001",
             "confidence": 0.9, "evidence": "Auth component"},
        ]})
        runner = MockRunner([match_resp])

        result = await trace_requirements(
            repo_path=str(tmp_path),
            requirements_doc=str(req_doc),
            _runner=runner,
        )
        assert result["extraction_mode"] == "structural"
        assert result["requirements_count"] == 2
        assert result["matches_count"] == 1

        # Verify output file
        out_file = tmp_path / ".architecture-models" / "requirements-trace.json"
        assert out_file.exists()


class TestRetroactiveMode:
    @pytest.mark.asyncio
    async def test_no_doc_uses_retroactive(self, tmp_path):
        retro_resp = json.dumps({"requirements": [
            {"id": "REQ-001", "text": "Derived from model", "source": "CAP-S1"},
        ]})
        match_resp = json.dumps({"matches": [
            {"function_id": "COMP-1", "requirement_id": "REQ-001",
             "confidence": 0.8, "evidence": "Model-derived"},
        ]})
        runner = MockRunner([retro_resp, match_resp])

        result = await trace_requirements(
            repo_path=str(tmp_path),
            model_yaml=MODEL_YAML,
            _runner=runner,
        )
        assert result["extraction_mode"] == "retroactive"
        assert result["requirements_count"] == 1


class TestBadPath:
    @pytest.mark.asyncio
    async def test_bad_path_returns_error(self):
        result = await trace_requirements(repo_path="/nonexistent/path")
        assert "error" in result


class TestOutputFile:
    @pytest.mark.asyncio
    async def test_output_written(self, tmp_path):
        req_doc = tmp_path / "reqs.md"
        req_doc.write_text("REQ-001: Test req\n")
        (tmp_path / ".architecture-model.yaml").write_text(MODEL_YAML)

        match_resp = json.dumps({"matches": []})
        runner = MockRunner([match_resp])

        await trace_requirements(
            repo_path=str(tmp_path),
            requirements_doc=str(req_doc),
            _runner=runner,
        )
        out_file = tmp_path / ".architecture-models" / "requirements-trace.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "requirements" in data
        assert "matches" in data

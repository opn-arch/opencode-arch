"""Tests for function-requirement matcher."""
import json

import pytest

from opencode_arch.requirements.matcher import match_functions_to_requirements
from opencode_arch.requirements.parser import ExtractedRequirement
from opencode_arch.runner.base import RunResult


class MockRunner:
    def __init__(self, responses=None):
        self.responses = list(responses or ['{"matches": []}'])
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
    - id: COMP-2
      name: LogService
      status: ACTIVE
  capabilities:
    - id: CAP-S1
      name: Authentication
      status: ACTIVE
"""

REQUIREMENTS = [
    ExtractedRequirement(id="REQ-001", text="System shall authenticate users",
                         source_doc="reqs.md", source_anchor="L1",
                         content_hash="abc123", extraction_method="structural"),
    ExtractedRequirement(id="REQ-002", text="System shall log events",
                         source_doc="reqs.md", source_anchor="L2",
                         content_hash="abc123", extraction_method="structural"),
]


class TestFunctionRequirementMatching:
    @pytest.mark.asyncio
    async def test_produces_matches(self):
        response = json.dumps({"matches": [
            {"function_id": "COMP-1", "requirement_id": "REQ-001",
             "confidence": 0.9, "evidence": "AuthService handles authentication"},
            {"function_id": "COMP-2", "requirement_id": "REQ-002",
             "confidence": 0.85, "evidence": "LogService handles logging"},
        ]})
        runner = MockRunner([response])
        matches = await match_functions_to_requirements(REQUIREMENTS, MODEL_YAML, runner)
        assert len(matches) == 2
        assert matches[0].function_id == "COMP-1"
        assert matches[0].requirement_id == "REQ-001"
        assert matches[0].confidence == 0.9
        assert matches[0].evidence == "AuthService handles authentication"
        assert matches[0].extraction_method == "llm_matched"

    @pytest.mark.asyncio
    async def test_each_match_has_confidence_and_evidence(self):
        response = json.dumps({"matches": [
            {"function_id": "COMP-1", "requirement_id": "REQ-001",
             "confidence": 0.75, "evidence": "Name similarity"},
        ]})
        runner = MockRunner([response])
        matches = await match_functions_to_requirements(REQUIREMENTS, MODEL_YAML, runner)
        assert len(matches) == 1
        assert isinstance(matches[0].confidence, float)
        assert matches[0].confidence > 0
        assert len(matches[0].evidence) > 0

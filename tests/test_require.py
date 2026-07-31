"""Tests for architect_require tool."""
import pytest
import yaml
from pathlib import Path

from opencode_arch.mcp.tools.require import capture_requirement


@pytest.mark.asyncio
class TestCaptureRequirement:
    async def test_creates_requirements_file(self, tmp_path):
        result = await capture_requirement(
            str(tmp_path), "Must handle 1000 req/s", component_id="COMP-1"
        )
        assert result["stored"] is True
        assert result["requirement_id"] == "REQ-1"
        assert result["component"] == "COMP-1"
        assert (tmp_path / ".architecture" / "requirements.yaml").exists()

    async def test_appends_to_existing(self, tmp_path):
        await capture_requirement(str(tmp_path), "First req")
        result = await capture_requirement(str(tmp_path), "Second req")
        assert result["requirement_id"] == "REQ-2"
        assert result["total_requirements"] == 2

    async def test_stores_all_fields(self, tmp_path):
        await capture_requirement(
            str(tmp_path), "Rate limit logins",
            component_id="COMP-3", priority="must", context="Auth discussion"
        )
        data = yaml.safe_load((tmp_path / ".architecture" / "requirements.yaml").read_text())
        req = data["requirements"][0]
        assert req["text"] == "Rate limit logins"
        assert req["component"] == "COMP-3"
        assert req["priority"] == "must"
        assert req["status"] == "proposed"
        assert req["context"] == "Auth discussion"

    async def test_unlinked_requirement(self, tmp_path):
        result = await capture_requirement(str(tmp_path), "General req")
        assert result["component"] == "unlinked"

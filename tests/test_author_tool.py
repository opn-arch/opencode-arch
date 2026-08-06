"""Tests for architect_author MCP tool."""
import pytest

from opencode_arch.mcp.tools.author import author_architecture


@pytest.mark.asyncio
async def test_author_creates_model(tmp_path):
    requirements = "# Actors\n- User: end user\n# Capabilities\n- CAP-1: Login"
    result = await author_architecture(str(tmp_path), requirements)
    assert "error" not in result
    assert result["actors"] == 1
    assert result["capabilities"] == 1
    assert result["lifecycle_phase"] == "concept"
    assert (tmp_path / ".architecture-model.yaml").exists()


@pytest.mark.asyncio
async def test_author_with_constraints(tmp_path):
    requirements = (
        "# Actors\n- Admin: administrator\n"
        "# Capabilities\n- CAP-1: Manage users\n"
        "# Constraints\n- CON-1: Must use TLS"
    )
    result = await author_architecture(str(tmp_path), requirements)
    assert "error" not in result
    assert result["actors"] == 1
    assert result["capabilities"] == 1
    assert result["constraints"] == 1


@pytest.mark.asyncio
async def test_author_invalid_path():
    result = await author_architecture("/nonexistent/path", "# Actors\n- User: test")
    assert "error" in result


@pytest.mark.asyncio
async def test_author_empty_requirements(tmp_path):
    result = await author_architecture(str(tmp_path), "")
    # Should still succeed (empty model)
    assert result["actors"] == 0
    assert result["capabilities"] == 0
    assert result["lifecycle_phase"] == "concept"

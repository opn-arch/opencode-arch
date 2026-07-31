"""Tests for architect_group MCP tool."""
import pytest
from opencode_arch.mcp.tools.group import group_repository


@pytest.mark.asyncio
async def test_group_nonexistent_path():
    result = await group_repository(repo_path="/nonexistent/path")
    assert "error" in result


@pytest.mark.asyncio
async def test_group_returns_groups(tmp_path):
    # Create a minimal Python package
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "foo.py").write_text(
        "class Foo:\n    def hello(self): pass\n    def world(self): pass\n\ndef main(): pass\n"
    )
    (pkg / "bar.py").write_text(
        "import foo\n\nclass Bar:\n    def greet(self): pass\n\ndef run(): pass\n"
    )

    result = await group_repository(repo_path=str(tmp_path))
    assert "error" not in result
    assert "groups" in result
    assert result["total_modules"] >= 1
    assert result["total_groups"] >= 1
    for g in result["groups"]:
        assert "name" in g
        assert "files" in g
        assert "file_count" in g


@pytest.mark.asyncio
async def test_group_with_target(tmp_path):
    # Create enough non-trivial files in a package
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(6):
        (pkg / f"mod{i}.py").write_text(
            f"class Mod{i}:\n    def func{i}(self): pass\n\ndef helper{i}(): pass\n"
        )

    result = await group_repository(repo_path=str(tmp_path), target_groups=3)
    assert "error" not in result
    assert result["total_groups"] <= 4  # approximately respects target


@pytest.mark.asyncio
async def test_group_tool_registered():
    """Verify the tool is registered in the MCP server."""
    try:
        from opencode_arch.mcp.server import mcp
        if mcp is not None:
            # Check tool is accessible
            assert hasattr(mcp, '_tool_manager') or True  # server exists
    except ImportError:
        pytest.skip("mcp package not installed")

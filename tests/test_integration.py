"""Integration test: extract → validate → score loop."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from opencode_arch.mcp.tools.extract import extract_architecture
from opencode_arch.mcp.tools.validate import validate_architecture


@pytest.mark.asyncio
async def test_extract_then_validate_loop():
    """Full loop: extract architecture from a repo, then validate it."""
    # Mock surrogate to return a valid architecture model
    mock_surrogate = AsyncMock()
    mock_surrogate.generate.return_value = (
        "meta:\n"
        "  schema_version: '1.3'\n"
        "  project: test-project\n"
        "entities:\n"
        "  capabilities:\n"
        "    - id: CAP-F1\n"
        "      name: Configuration\n"
        "      status: ACTIVE\n"
        "  components:\n"
        "    - id: COMP-1\n"
        "      name: ConfigLoader\n"
        "      status: ACTIVE\n"
        "relationships:\n"
        "  - type: realizes\n"
        "    from: COMP-1\n"
        "    to: CAP-F1\n"
    )

    with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "config.py").write_text("class ConfigLoader:\n    pass\n")

            # Step 1: Extract
            yaml_result = await extract_architecture(repo_path=tmpdir)
            assert "entities" in yaml_result or "components" in yaml_result

            # Step 2: Validate
            validation = await validate_architecture(model_yaml=yaml_result)
            assert "score" in validation
            assert validation["score"] >= 0  # Valid parse at minimum


@pytest.mark.asyncio
async def test_no_surrogate_fallback_still_validates():
    """When no surrogate, manifest-based extraction should still be validatable."""
    with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def main():\n    print('hello')\n")

            # Extract without surrogate (returns raw manifest YAML)
            yaml_result = await extract_architecture(repo_path=tmpdir)
            assert isinstance(yaml_result, str)
            assert len(yaml_result) > 0

            # Validate should handle this gracefully (may not score high
            # since it's not in architecture model format)
            validation = await validate_architecture(model_yaml=yaml_result)
            assert "score" in validation
            # Even if score is 0 (manifest format != architecture format),
            # it shouldn't crash

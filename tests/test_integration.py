# tests/test_integration.py
"""Integration tests: scan → slice → (agent reasons) → extract → validate."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.scan import scan_repository
from opencode_arch.mcp.tools.slice import slice_context
from opencode_arch.mcp.tools.validate import validate_architecture
from opencode_arch.mcp.tools.extract import store_extraction


@pytest.mark.asyncio
async def test_full_extraction_flow():
    """Simulate: scan → slice → validate agent output → store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a small project (proper package so scanner detects modules)
        pkg = Path(tmpdir, "myapp")
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "models.py").write_text("class User:\n    name: str\n")
        (pkg / "views.py").write_text("def index():\n    return 'hello'\n")

        # Step 1: Scan
        manifest = await scan_repository(repo_path=tmpdir)
        assert "modules" in manifest
        assert len(manifest["modules"]) >= 2

        # Step 2: Slice (get context for agent)
        context = await slice_context(repo_path=tmpdir, budget=2000)
        assert isinstance(context, str)
        assert len(context) > 0

        # Step 3: Simulate agent output (normally agent produces this)
        agent_yaml = (
            "meta:\n"
            "  project: test\n"
            "  schema_version: '1.3'\n"
            "entities:\n"
            "  components:\n"
            "    - id: COMP-1\n"
            "      name: Models\n"
            "      status: ACTIVE\n"
            "    - id: COMP-2\n"
            "      name: Views\n"
            "      status: ACTIVE\n"
            "  capabilities:\n"
            "    - id: CAP-F1\n"
            "      name: UserManagement\n"
            "      status: ACTIVE\n"
            "relationships:\n"
            "  - from: COMP-1\n"
            "    to: CAP-F1\n"
            "    type: realizes\n"
        )

        # Step 4: Validate
        validation = await validate_architecture(model_yaml=agent_yaml)
        assert validation["score"] >= 70
        assert validation["is_valid"] is True

        # Step 5: Store
        stored = await store_extraction(repo_path=tmpdir, model_yaml=agent_yaml, context_tokens=len(context) // 4)
        assert stored["stored"] is True
        assert Path(tmpdir, ".architecture-model.yaml").exists()


@pytest.mark.asyncio
async def test_slice_uses_stored_model():
    """After storing a model, slice should use it for richer context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "app.py").write_text("class App: pass\n")

        # Store a model
        model_yaml = (
            "meta:\n"
            "  project: test\n"
            "  schema_version: '1.3'\n"
            "entities:\n"
            "  components:\n"
            "    - id: COMP-1\n"
            "      name: App\n"
            "      status: ACTIVE\n"
        )
        Path(tmpdir, ".architecture-model.yaml").write_text(model_yaml)

        # Now slice should detect the model file and use rich path
        context = await slice_context(repo_path=tmpdir)
        assert isinstance(context, str)
        assert len(context) > 0

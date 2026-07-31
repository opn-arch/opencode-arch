"""Tests for architect_check hierarchical auto-F-block mode."""
import pytest
import asyncio

from opencode_arch.mcp.tools.check import check_representativeness


def _make_model_yaml(components: list[dict]) -> str:
    """Build a minimal model YAML with given components."""
    import yaml
    model = {
        "meta": {"project": "test", "schema_version": "1.3"},
        "entities": {
            "components": components,
        },
        "relationships": [],
    }
    return yaml.dump(model)


@pytest.fixture
def multi_pkg_repo(tmp_path):
    """Create a repo with multiple packages (enough for auto-F-blocks)."""
    # Package 1: core (3 files)
    core = tmp_path / "myapp" / "core"
    core.mkdir(parents=True)
    (core / "__init__.py").write_text("")
    (core / "engine.py").write_text("def run(): pass\ndef start(): pass\n")
    (core / "config.py").write_text("def load(): pass\n")
    (core / "types.py").write_text("class Base: pass\n")

    # Package 2: api (3 files)
    api = tmp_path / "myapp" / "api"
    api.mkdir(parents=True)
    (api / "__init__.py").write_text("")
    (api / "views.py").write_text("from myapp.core.engine import run\ndef index(): return run()\n")
    (api / "routes.py").write_text("def setup(): pass\n")
    (api / "middleware.py").write_text("def auth(): pass\n")

    # Package 3: utils (3 files)
    utils = tmp_path / "myapp" / "utils"
    utils.mkdir(parents=True)
    (utils / "__init__.py").write_text("")
    (utils / "helpers.py").write_text("def fmt(): pass\n")
    (utils / "cache.py").write_text("def get(): pass\n")
    (utils / "log.py").write_text("def info(): pass\n")

    (tmp_path / "myapp" / "__init__.py").write_text("")
    return tmp_path


class TestCheckAutoHierarchical:
    def test_auto_hierarchical_mode_triggered(self, multi_pkg_repo):
        """Without config, auto-F-blocks should trigger hierarchical mode."""
        components = [
            {"id": "COMP-1", "name": "Core", "status": "ACTIVE", "files": [
                "myapp/core/__init__.py", "myapp/core/engine.py", "myapp/core/config.py", "myapp/core/types.py"
            ]},
            {"id": "COMP-2", "name": "API", "status": "ACTIVE", "files": [
                "myapp/api/__init__.py", "myapp/api/views.py", "myapp/api/routes.py", "myapp/api/middleware.py"
            ]},
            {"id": "COMP-3", "name": "Utils", "status": "ACTIVE", "files": [
                "myapp/utils/__init__.py", "myapp/utils/helpers.py", "myapp/utils/cache.py", "myapp/utils/log.py"
            ]},
        ]
        model_yaml = _make_model_yaml(components)
        result = asyncio.run(check_representativeness(str(multi_pkg_repo), model_yaml))

        assert "error" not in result
        assert result.get("mode") in ("hierarchical_auto", "hierarchical")

    def test_auto_hierarchical_has_blocks(self, multi_pkg_repo):
        """Auto-hierarchical should report per-block scores."""
        components = [
            {"id": "COMP-1", "name": "Core", "status": "ACTIVE", "files": [
                "myapp/core/__init__.py", "myapp/core/engine.py", "myapp/core/config.py", "myapp/core/types.py"
            ]},
            {"id": "COMP-2", "name": "API", "status": "ACTIVE", "files": [
                "myapp/api/__init__.py", "myapp/api/views.py", "myapp/api/routes.py", "myapp/api/middleware.py"
            ]},
            {"id": "COMP-3", "name": "Utils", "status": "ACTIVE", "files": [
                "myapp/utils/__init__.py", "myapp/utils/helpers.py", "myapp/utils/cache.py", "myapp/utils/log.py"
            ]},
        ]
        model_yaml = _make_model_yaml(components)
        result = asyncio.run(check_representativeness(str(multi_pkg_repo), model_yaml))

        if result.get("mode") in ("hierarchical_auto", "hierarchical"):
            assert "blocks" in result
            assert "overall" in result

    def test_flat_fallback_for_small_repo(self, tmp_path):
        """Repo too small for auto-F-blocks should use flat mode."""
        pkg = tmp_path / "tiny"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text("def run(): pass\n")

        components = [
            {"id": "COMP-1", "name": "Tiny", "status": "ACTIVE", "files": ["tiny/__init__.py", "tiny/main.py"]},
        ]
        model_yaml = _make_model_yaml(components)
        result = asyncio.run(check_representativeness(str(tmp_path), model_yaml))

        assert "error" not in result
        assert result.get("mode") == "flat"

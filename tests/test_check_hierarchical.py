"""Tests for architect_check hierarchical auto-F-block mode."""
import pytest
import asyncio
from types import SimpleNamespace

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


def _write_hierarchy(tmp_path, child_refs):
    import yaml

    (tmp_path / "one.py").write_text("def one(): return 1\n")
    (tmp_path / "two.py").write_text("def two(): return 2\n")
    systems = []
    for block_id, ref in child_refs.items():
        systems.append({
            "id": f"SYS-{block_id}", "name": block_id, "status": "ACTIVE",
            "source_block": block_id, "sub_model_ref": ref,
        })
        if ref.startswith("models/") and "/missing/" not in ref:
            child_path = tmp_path / ref
            child_path.parent.mkdir(parents=True, exist_ok=True)
            filename = "one.py" if block_id == "S1" else "two.py"
            child_path.write_text(yaml.safe_dump({
                "meta": {"project": block_id, "schema_version": "1.3"},
                "entities": {"components": [{
                    "id": f"COMP-{block_id}", "name": block_id, "status": "ACTIVE", "files": [filename],
                }]},
                "relationships": [],
            }))
    root = {
        "meta": {"project": "root", "schema_version": "1.3"},
        "entities": {"systems": systems},
        "relationships": [],
    }
    (tmp_path / ".architecture-model.yaml").write_text(yaml.safe_dump(root))


def _recursive_manifests(tmp_path):
    from architecture_model.manifest.recursive import generate_block_manifest

    return {
        block_id: SimpleNamespace(manifest=generate_block_manifest(
            tmp_path, block_id, {"files": [filename]},
        ))
        for block_id, filename in {"S1": "one.py", "S2": "two.py"}.items()
    }


@pytest.mark.asyncio
async def test_hierarchical_check_populates_child_blocks_and_recursive_overall(tmp_path, monkeypatch):
    _write_hierarchy(tmp_path, {
        "S1": "models/one/.architecture-model.yaml",
        "S2": "models/two/.architecture-model.yaml",
    })
    manifests = _recursive_manifests(tmp_path)
    monkeypatch.setattr(
        "architecture_model.config.loader.get_config",
        lambda path: SimpleNamespace(source_block_dict={"S1": {}, "S2": {}}),
    )
    monkeypatch.setattr(
        "architecture_model.manifest.recursive.generate_recursive_manifests",
        lambda path: manifests,
    )

    result = await check_representativeness(str(tmp_path))

    assert set(result["blocks"]) == {"S1", "S2"}
    assert result["overall"] == 100.0


@pytest.mark.asyncio
async def test_hierarchical_check_surfaces_missing_child_and_lowers_score(tmp_path, monkeypatch):
    _write_hierarchy(tmp_path, {
        "S1": "models/one/.architecture-model.yaml",
        "S2": "models/missing/.architecture-model.yaml",
    })
    manifests = _recursive_manifests(tmp_path)
    monkeypatch.setattr(
        "architecture_model.config.loader.get_config",
        lambda path: SimpleNamespace(source_block_dict={"S1": {}, "S2": {}}),
    )
    monkeypatch.setattr(
        "architecture_model.manifest.recursive.generate_recursive_manifests",
        lambda path: manifests,
    )

    result = await check_representativeness(str(tmp_path))

    assert result["overall"] <= 75.0
    assert any("Missing sub-model" in issue for issue in result["hierarchy_issues"])


@pytest.mark.asyncio
async def test_hierarchical_check_rejects_traversal_reference(tmp_path, monkeypatch):
    _write_hierarchy(tmp_path, {"S1": "../outside.yaml", "S2": "models/two/.architecture-model.yaml"})
    manifests = _recursive_manifests(tmp_path)
    monkeypatch.setattr(
        "architecture_model.config.loader.get_config",
        lambda path: SimpleNamespace(source_block_dict={"S1": {}, "S2": {}}),
    )
    monkeypatch.setattr(
        "architecture_model.manifest.recursive.generate_recursive_manifests",
        lambda path: manifests,
    )

    result = await check_representativeness(str(tmp_path))

    assert result["overall"] <= 75.0
    assert any("Path traversal" in issue for issue in result["hierarchy_issues"])


@pytest.mark.asyncio
async def test_hierarchical_check_surfaces_cycle(tmp_path, monkeypatch):
    import yaml

    _write_hierarchy(tmp_path, {"S1": "models/one/.architecture-model.yaml", "S2": "models/two/.architecture-model.yaml"})
    child_path = tmp_path / "models" / "one" / ".architecture-model.yaml"
    child = yaml.safe_load(child_path.read_text())
    child["entities"]["systems"] = [{
        "id": "SYS-ROOT", "name": "Root", "status": "ACTIVE",
        "source_block": "ROOT", "sub_model_ref": "../../.architecture-model.yaml",
    }]
    child_path.write_text(yaml.safe_dump(child))
    manifests = _recursive_manifests(tmp_path)
    monkeypatch.setattr(
        "architecture_model.config.loader.get_config",
        lambda path: SimpleNamespace(source_block_dict={"S1": {}, "S2": {}}),
    )
    monkeypatch.setattr(
        "architecture_model.manifest.recursive.generate_recursive_manifests",
        lambda path: manifests,
    )

    result = await check_representativeness(str(tmp_path))

    assert result["overall"] <= 75.0
    assert any("cycle" in issue.lower() for issue in result["hierarchy_issues"])

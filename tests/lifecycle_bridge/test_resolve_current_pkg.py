"""Tests for the ``resolve_current_pkg`` helper in ``lifecycle_bridge``."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _write_root_pkg(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "architecture_id": "root-pkg",
                "name": "Root",
                "slug": "root-pkg",
                "contract_version": "1.0.0",
                "model_ref": "model/.architecture-model.yaml",
                "manifest_ref": "manifest/manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_raises_when_root_is_none():
    from opencode_arch.lifecycle_bridge import PackageDescriptor, resolve_current_pkg

    pkg = PackageDescriptor(
        architecture_id="x",
        name="X",
        slug="x",
        contract_version="1.0.0",
        model_ref="model/.architecture-model.yaml",
        manifest_ref="manifest/manifest.json",
    )
    assert pkg.root is None
    with pytest.raises(ValueError, match="pkg.root is None"):
        resolve_current_pkg(pkg)


def test_returns_pkg_unchanged_when_no_current(tmp_path: Path):
    from opencode_arch.lifecycle_bridge import PackageLoader, resolve_current_pkg

    _write_root_pkg(tmp_path)
    pkg = PackageLoader(tmp_path)
    result = resolve_current_pkg(pkg)
    assert result.root == pkg.root


def test_rebases_root_to_current_when_present(tmp_path: Path):
    from opencode_arch.lifecycle_bridge import PackageLoader, resolve_current_pkg

    _write_root_pkg(tmp_path)
    # Simulate a published generation with a CURRENT symlink.
    gen_dir = tmp_path / "generations" / "0000001"
    (gen_dir / "model").mkdir(parents=True)
    (gen_dir / "manifest").mkdir()
    current = tmp_path / "CURRENT"
    current.symlink_to(gen_dir, target_is_directory=True)

    pkg = PackageLoader(tmp_path)
    result = resolve_current_pkg(pkg)
    assert result.root == gen_dir.resolve()
    # Descriptor fields preserved.
    assert result.model_ref == "model/.architecture-model.yaml"
    assert result.manifest_ref == "manifest/manifest.json"
    assert result.architecture_id == pkg.architecture_id


def test_current_can_be_a_regular_directory(tmp_path: Path):
    """If CURRENT is a directory (not a symlink), still resolves."""
    from opencode_arch.lifecycle_bridge import PackageLoader, resolve_current_pkg

    _write_root_pkg(tmp_path)
    current = tmp_path / "CURRENT"
    current.mkdir()

    pkg = PackageLoader(tmp_path)
    result = resolve_current_pkg(pkg)
    assert result.root == current.resolve()

"""Autoinit root package.yaml for lifecycle_exec tests using tmp_path.

See ``tests/mcp/tools/lifecycle/conftest.py`` for rationale (N101).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


_ARCH_ID = "root-pkg"


@pytest.fixture(autouse=True)
def _autoinit_root_package(request, tmp_path: Path) -> None:
    if request.node.get_closest_marker("no_pkg_init") is not None:
        return
    from architecture_model.lifecycle.versions import SchemaVersions

    lifecycle = tmp_path / ".architecture" / "lifecycle"
    lifecycle.mkdir(parents=True, exist_ok=True)
    pkg_yaml = lifecycle / "package.yaml"
    if pkg_yaml.exists():
        return
    pkg_yaml.write_text(
        yaml.safe_dump(
            {
                "architecture_id": _ARCH_ID,
                "name": _ARCH_ID,
                "slug": _ARCH_ID,
                "contract_version": SchemaVersions.PACKAGE,
                "model_ref": "model/.architecture-model.yaml",
                "manifest_ref": "manifest/manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

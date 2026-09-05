"""Shared test fixtures for MCP lifecycle tool tests.

N101 removed the auto-create behaviour from ``package_publish``. Most
existing tests here were written before that fix and use ``tmp_path``
directly, relying on the tool to silently create the root package. This
autouse fixture restores that convenience for legacy tests by
pre-writing a minimal ``package.yaml``.

Tests that need to observe the "no package" state (e.g. the N101
regression) must use a *subdirectory* of ``tmp_path`` as the repo path
so this fixture doesn't reach them.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


_ARCH_ID = "root-pkg"


@pytest.fixture(autouse=True)
def _autoinit_root_package(request, tmp_path: Path) -> None:
    """Pre-write ``.architecture/lifecycle/package.yaml`` in tmp_path.

    Opt out with ``@pytest.mark.no_pkg_init`` on tests that need to
    observe the "no package" state.
    """
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

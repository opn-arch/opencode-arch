"""Fresh repo with a published root generation, for e2e tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.publication import PackageBundle, publish
from architecture_model.lifecycle.versions import SchemaVersions


_MODEL_YAML = (
    "meta:\n"
    "  schema_version: '1.3'\n"
    "  project: test\n"
    "entities:\n"
    "  components:\n"
    "    - id: COMP-1\n"
    "      name: Alpha\n"
    "      status: ACTIVE\n"
)


def fresh_repo_with_published_generation(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    lifecycle = repo / ".architecture" / "lifecycle"
    lifecycle.mkdir(parents=True, exist_ok=True)
    (lifecycle / "package.yaml").write_text(
        yaml.safe_dump({
            "architecture_id": "root",
            "name": "root",
            "slug": "root",
            "contract_version": SchemaVersions.PACKAGE,
            "model_ref": "model/.architecture-model.yaml",
            "manifest_ref": "manifest/manifest.json",
        }, sort_keys=True),
        encoding="utf-8",
    )
    pkg = load_package(lifecycle)
    res = publish(pkg, PackageBundle(model_bytes=_MODEL_YAML.encode(), manifest_bytes=b"{}"))

    ai_dir = repo / ".architecture" / "ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "proposer_config.yaml").write_text(
        "plugin: tests.fixtures.stub_proposer:noop_proposer\n",
        encoding="utf-8",
    )

    return repo, res.root_digest

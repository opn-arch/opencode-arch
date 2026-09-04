"""MCP tool: publish an architecture package.

Wraps ``architecture_model.lifecycle.publication.publish`` so an LLM can
publish a model (+ optional manifest) into the repo's lifecycle store
via a stable envelope-shaped API.

Deviation notes vs. the plan
----------------------------
* Phase 1 ``publish()`` requires an already-loaded
  :class:`architecture_model.lifecycle.package.ArchitecturePackage` (i.e.
  a ``package.yaml`` on disk). This tool auto-creates a minimal root
  ``package.yaml`` at ``<repo>/.architecture/lifecycle/package.yaml`` on
  first invocation and reuses it thereafter.
* ``PublicationResult`` exposes ``generation`` / ``root_digest`` /
  ``generation_dir`` — not ``package_id`` / ``revision`` / ``digest`` /
  ``index_path``. The tool maps them:
    - ``package_id``    <- ``pkg.architecture_id``
    - ``revision``      <- zero-padded ``generation``
    - ``digest``        <- ``result.root_digest``
    - ``index_path``    <- ``str(result.generation_dir)``
* Phase 1 does not have a ``parent_package_id`` concept on ``publish()``
  (parent linkage lives in ``package.yaml.children``). When provided,
  we resolve it against the on-disk package tree; if it does not match
  the root package's architecture_id, we return ``PRECONDITION_FAILED``.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result

_ROOT_ARCH_ID = "root-pkg"


def _package_yaml_template() -> dict:
    """Root package descriptor template.

    ``model_ref`` / ``manifest_ref`` point at paths INSIDE a generation
    directory (Phase 1 ``publish`` writes to
    ``generations/<n>/model/.architecture-model.yaml`` and
    ``generations/<n>/manifest/manifest.json``). Consumers of the model
    must rebase ``pkg.root`` to the current generation (see
    ``opencode_arch.lifecycle_bridge.resolve_current_pkg``) before
    ``pkg.root / pkg.model_ref`` resolves to a real file.

    ``contract_version`` is sourced from Phase 1's ``SchemaVersions.PACKAGE``
    to avoid drift when the schema bumps.
    """
    from architecture_model.lifecycle.versions import SchemaVersions

    return {
        "architecture_id": _ROOT_ARCH_ID,
        "name": "Root Package",
        "slug": _ROOT_ARCH_ID,
        "contract_version": SchemaVersions.PACKAGE,
        "model_ref": "model/.architecture-model.yaml",
        "manifest_ref": "manifest/manifest.json",
    }


def _ensure_root_package(lifecycle_root: Path):
    """Load or create the root ArchitecturePackage at ``lifecycle_root``."""
    from architecture_model.lifecycle.package import load_package

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        pkg_yaml.write_text(
            yaml.safe_dump(_package_yaml_template(), sort_keys=True),
            encoding="utf-8",
        )
    return load_package(lifecycle_root)


@tool_result
async def publish_package_tool(
    repo_path: str,
    model_yaml: str,
    manifest_json: str | None = None,
    parent_package_id: str | None = None,
) -> dict:
    """Publish a new architecture package to the repo's lifecycle store."""
    # 1. Import Phase 1 lazily so import errors surface as INTERNAL only when
    #    the tool is actually invoked.
    from architecture_model.core.parser import _parse_raw
    from architecture_model.lifecycle.publication import (
        PackageBundle,
        PublicationLockTimeout,
        publish,
    )
    from architecture_model.lifecycle.journal import Journal

    # 2. Validate + resolve repo.
    repo = resolve_repo(repo_path)

    # 3. Ensure lifecycle tree.
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    # 4. Validate model_yaml.
    if not isinstance(model_yaml, str) or not model_yaml.strip():
        raise ValueError("model_yaml must be a non-empty YAML string")
    try:
        raw = yaml.safe_load(model_yaml)
    except yaml.YAMLError as exc:
        raise ValueError(f"model_yaml is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("model_yaml must decode to a mapping at the top level")
    # Sanity-parse via architecture_model so bad shapes fail early.
    _parse_raw(raw)
    model_bytes = model_yaml.encode("utf-8")

    # 5. Validate manifest_json (optional).
    # Phase 1 ``publish()`` always writes ``manifest/manifest.json`` from
    # ``bundle.manifest_bytes``. There is no way to omit the file. To
    # disambiguate "no manifest supplied" from a legitimate ``'{}'``
    # payload we use empty bytes (0-byte file) as the sentinel — this is
    # unambiguous with ``b"{}"`` (2 bytes) on the load side.
    if manifest_json is None:
        manifest_bytes = b""
    else:
        if not isinstance(manifest_json, str):
            raise ValueError("manifest_json must be a JSON string or None")
        try:
            json.loads(manifest_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"manifest_json is not valid JSON: {exc}") from exc
        manifest_bytes = manifest_json.encode("utf-8")

    # 6. Load/create root package.
    pkg = _ensure_root_package(lifecycle_root)

    # 7. Enforce parent_package_id if provided.
    if parent_package_id is not None:
        if parent_package_id != pkg.architecture_id:
            return err(
                "PRECONDITION_FAILED",
                f"parent_package_id {parent_package_id!r} not found",
                parent_package_id=parent_package_id,
                known_ids=[pkg.architecture_id],
            )

    # 8. Publish via Phase 1 (journal at lifecycle_exec's location).
    journal_path = paths.journal_path(repo)
    bundle = PackageBundle(
        model_bytes=model_bytes,
        manifest_bytes=manifest_bytes,
    )
    try:
        result = publish(pkg, bundle, journal_path=journal_path)
    except PublicationLockTimeout as exc:
        return err("PRECONDITION_FAILED", f"publication lock timeout: {exc}")

    # 9. Record MCP-facing package.publish event.
    Journal(journal_path).record(
        "package.publish",
        {
            "package_id": pkg.architecture_id,
            "revision": f"{result.generation:07d}",
            "digest": result.root_digest,
            "actor": "mcp",
        },
    )

    # 10. Return envelope.
    return ok({
        "package_id": pkg.architecture_id,
        "revision": f"{result.generation:07d}",
        "digest": result.root_digest,
        "index_path": str(result.generation_dir),
    })

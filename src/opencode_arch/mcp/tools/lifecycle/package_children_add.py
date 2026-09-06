"""MCP tool: append a child package to the root ArchitecturePackage.

Registers a nested ``package.yaml`` in the root's ``children`` list.
The child file must already exist at
``<repo>/.architecture/lifecycle/<child_path>``.

Deviation notes vs. the plan
----------------------------
* Phase 1 :attr:`ArchitecturePackage.children` is a ``list[str]`` of
  POSIX-relative paths to child ``package.yaml`` files — not a list of
  dicts. This tool honors that shape.
* Duplicate registrations return ``PRECONDITION_FAILED`` per spec (no
  silent no-op).
* On post-write validation failure we return ``SCHEMA_VIOLATION`` without
  attempting an automatic rollback — the just-written descriptor is left
  on disk for inspection. Callers are expected to fix it manually or
  retry after correcting inputs.
"""
from __future__ import annotations

import yaml
from pydantic import ValidationError

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented


@instrumented("mcp_tool:package_children_add")
@tool_result
async def package_children_add_tool(
    repo_path: str,
    child_path: str,
) -> dict:
    """Append ``child_path`` to the root package's ``children`` list."""
    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.package import load_package

    if not isinstance(child_path, str) or not child_path.strip():
        raise ValueError("child_path must be a non-empty string")

    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", "package.yaml not found")

    child_file = lifecycle_root / child_path
    if not child_file.is_file():
        return err(
            "NOT_FOUND",
            "child package.yaml not found",
            child_path=child_path,
        )

    text = pkg_yaml.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return err("SCHEMA_VIOLATION", "root package.yaml is not a mapping")

    children = data.get("children") or []
    if not isinstance(children, list):
        return err("SCHEMA_VIOLATION", "children field is not a list")

    if child_path in children:
        return err(
            "PRECONDITION_FAILED",
            "child already present",
            child_path=child_path,
        )

    children.append(child_path)
    data["children"] = children

    new_bytes = yaml.safe_dump(data, sort_keys=False).encode("utf-8")
    write_atomic(pkg_yaml, new_bytes)

    # Re-load to validate the resulting descriptor. No automatic rollback:
    # the just-written file is left on disk (see module docstring).
    try:
        pkg = load_package(lifecycle_root)
    except ValidationError as exc:
        return err(
            "SCHEMA_VIOLATION",
            "resulting descriptor invalid",
            detail=str(exc),
        )

    return ok({
        "parent_architecture_id": pkg.architecture_id,
        "children": list(pkg.children),
    })

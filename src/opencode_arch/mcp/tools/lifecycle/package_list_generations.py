"""MCP tool: list published generations of the root architecture package."""
from __future__ import annotations

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result


@tool_result
async def package_list_generations_tool(repo_path: str) -> dict:
    """List all committed generations of the root package."""
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.publication import (
        list_generations,
        read_current_generation,
    )

    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", f"no package at {pkg_yaml}")

    pkg = load_package(lifecycle_root)
    gens = list_generations(pkg)
    current = read_current_generation(pkg)

    return ok({
        "package_id": pkg.architecture_id,
        "current": f"{current:07d}" if current is not None else None,
        "generations": [f"{g:07d}" for g in gens],
    })

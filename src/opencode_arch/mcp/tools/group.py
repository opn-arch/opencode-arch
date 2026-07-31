"""architect_group MCP tool — group repository modules into logical components."""
from __future__ import annotations

from pathlib import Path
from typing import Any


async def group_repository(repo_path: str, target_groups: int = 0) -> dict[str, Any]:
    """Group repository modules into logical architecture components.

    Uses multi-signal affinity (subdirectory, name-prefix, imports) to
    cluster source files into coherent component groups. This provides
    suggested component boundaries for architecture extraction.

    Args:
        repo_path: Absolute path to the repository root.
        target_groups: Desired number of groups. 0 = auto-calculate.

    Returns:
        Dict with keys: groups, total_modules, total_groups, filtered_trivial.
        Each group has: name, files, file_count, locked.
        Returns {"error": "..."} on failure.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.manifest.generator import generate_manifest
        from architecture_model.manifest.grouping import group_modules

        manifest = generate_manifest(path)
        target = target_groups if target_groups > 0 else None
        groups = group_modules(
            manifest.modules,
            manifest.interfaces,
            target_groups=target,
        )

        result_groups = []
        for g in groups:
            result_groups.append({
                "name": g.name,
                "files": g.modules,
                "file_count": len(g.modules),
                "primary_file": g.primary_file,
            })

        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_group", repo=path.name)
        except Exception:
            pass

        return {
            "groups": result_groups,
            "total_modules": len(manifest.modules),
            "total_groups": len(groups),
        }

    except Exception as e:
        return {"error": f"Grouping failed: {e}"}

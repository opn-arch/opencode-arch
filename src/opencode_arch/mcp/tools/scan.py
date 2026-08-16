"""architect_scan MCP tool — generate reality manifest via AST scanning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
async def scan_repository(repo_path: str, mode: str = "full") -> dict[str, Any]:
    """Scan a repository and generate its reality manifest.

    STOP and call this tool when you need to understand a codebase's structure.

    Performs AST analysis on all source files to produce a ground-truth
    inventory of modules, functions, classes, imports, and metrics.

    Args:
        repo_path: Absolute path to the repository root.
        mode: "full" (default) - full AST scan
              "schema" - output format description without scanning
              "summary" - quick metrics only (module count, file count)

    Returns:
        Manifest dict with keys: generated_at, project_root, metrics,
        functional_blocks, modules, interfaces.
        Returns {"error": "..."} on failure.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    if mode == "schema":
        return {
            "description": "architect_scan output schema",
            "keys": {
                "generated_at": "ISO timestamp",
                "project_root": "Absolute path scanned",
                "metrics": {
                    "total_modules": "int — number of source files",
                    "total_functions": "int — total functions/methods",
                    "total_classes": "int — total class definitions",
                    "total_imports": "int — import edge count",
                },
                "functional_blocks": "dict[block_name, {sub_functions, primary_file}]",
                "modules": "list[{path, functions, classes, imports}]",
                "interfaces": "list[{source, target, symbols}] — import edges",
                "suggested_components": "list[{name, files, file_count}] — grouped modules",
            },
            "usage": "Call with mode='full' to get actual data. Use architect_group for component boundaries.",
        }

    if mode == "summary":
        try:
            from architecture_model.manifest.generator import generate_manifest

            manifest = generate_manifest(path)
            metrics = manifest.to_dict().get("metrics", {})
            return {
                "project_root": str(path),
                "metrics": metrics,
                "module_count": len(manifest.modules),
            }
        except Exception as e:
            return {"error": f"Summary scan failed: {e}"}

    try:
        from architecture_model.manifest.generator import generate_manifest

        manifest = generate_manifest(path)

        # Include suggested component groupings
        suggested = None
        try:
            from architecture_model.manifest.grouping import group_modules

            groups = group_modules(manifest.modules, manifest.interfaces)
            suggested = [
                {"name": g.name, "files": g.modules, "file_count": len(g.modules)} for g in groups
            ]
        except Exception:
            pass

        try:
            from opencode_arch.telemetry.collector import drain_and_store

            drain_and_store(tool="architect_scan", repo=path.name)
        except Exception:
            pass

        result = manifest.to_dict()
        if suggested:
            result["suggested_components"] = suggested
        return result
    except Exception as e:
        return {"error": f"Scan failed: {e}"}

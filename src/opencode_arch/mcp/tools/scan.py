"""architect_scan MCP tool — generate reality manifest via AST scanning."""
from __future__ import annotations

from pathlib import Path
from typing import Any


async def scan_repository(repo_path: str) -> dict[str, Any]:
    """Scan a repository and generate its reality manifest.

    Performs AST analysis on all source files to produce a ground-truth
    inventory of modules, functions, classes, imports, and metrics.

    Args:
        repo_path: Absolute path to the repository root.

    Returns:
        Manifest dict with keys: generated_at, project_root, metrics,
        functional_blocks, modules, interfaces.
        Returns {"error": "..."} on failure.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(path)
        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_scan", repo=path.name)
        except Exception:
            pass
        return manifest
    except Exception as e:
        return {"error": f"Scan failed: {e}"}

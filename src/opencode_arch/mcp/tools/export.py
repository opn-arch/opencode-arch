"""architect_export MCP tool — export flat files for mobile AI consumption."""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
async def export_repository(
    repo_path: str,
    output_dir: str = "",
    output_format: str = "dir",
    prefix: str = "",
) -> dict[str, Any]:
    """Export repository architecture as flat files for mobile AI.

    Builds a set of flat files (model, sub-models, docs, manifests, specs,
    diagrams, skills, reference docs) suitable for use in token-limited
    AI environments.

    Args:
        repo_path: Absolute path to the repository.
        output_dir: Where to write output. Default: {repo_path}/.architecture-export/
        output_format: "dir" (flat directory) or "zip" (single zip file).
        prefix: File prefix override. Default: auto-derived from repo name.

    Returns:
        Dict with file list, sizes, and output location.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.export.flatfiles import build_flat_export

        result = build_flat_export(
            repo_path=path,
            prefix=prefix or None,
        )

        # Determine output location
        if output_dir:
            out_path = Path(output_dir)
        else:
            out_path = path / ".architecture-export"

        if output_format == "zip":
            # Write zip file
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname, content in result.files.items():
                    zf.writestr(fname, content)
        else:
            # Write flat directory
            out_path.mkdir(parents=True, exist_ok=True)
            for fname, content in result.files.items():
                (out_path / fname).write_text(content)

        return {
            "files": list(result.files.keys()),
            "file_count": len(result.files),
            "total_size_bytes": result.total_size_bytes,
            "prefix": result.prefix,
            "output": str(out_path),
            "format": output_format,
        }

    except Exception as e:
        return {"error": f"Export failed: {e}"}

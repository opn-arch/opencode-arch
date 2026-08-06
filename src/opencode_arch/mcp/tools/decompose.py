"""architect_decompose MCP tool — decompose model into sub-models and recursive manifests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
async def decompose_repository(repo_path: str) -> dict[str, Any]:
    """Decompose architecture model into per-block sub-models and recursive manifests.

    Reads .architecture-model.yaml, traces relationships per F-block,
    writes sub-models to .architecture-models/ and per-block manifests
    to .architecture/manifests/.

    Args:
        repo_path: Absolute path to the repository.

    Returns:
        Dict with sub_models, recursive_manifests, and paths.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    model_file = path / ".architecture-model.yaml"
    if not model_file.exists():
        return {"error": "No .architecture-model.yaml found. Run architect_extract first."}

    result: dict[str, Any] = {}

    # Step 1: Decompose into sub-models
    try:
        from architecture_model.orchestration.decompose import decompose_model, write_sub_models

        sub_models = decompose_model(path)
        if sub_models:
            out_dir = path / ".architecture-models"
            written = write_sub_models(sub_models, out_dir)
            result["sub_models"] = list(sub_models.keys())
            result["sub_model_dir"] = str(out_dir.relative_to(path))
            result["sub_model_details"] = [
                {
                    "block_id": bid,
                    "components": len(m.entities.components),
                    "relationships": len(m.relationships),
                }
                for bid, m in sub_models.items()
            ]
        else:
            result["sub_models"] = []
            result["sub_model_note"] = "No sub-models generated (no F-blocks with matching components)"
    except Exception as e:
        result["sub_model_error"] = str(e)

    # Step 2: Generate recursive per-block manifests
    try:
        from architecture_model.manifest.recursive import generate_recursive_manifests
        from architecture_model.config.loader import get_config

        # Use manifest F-blocks as fallback if config doesn't have them
        source_block_override = None
        try:
            cfg = get_config(path)
            if not cfg.source_block_dict:
                from architecture_model.manifest.generator import generate_manifest
                manifest = generate_manifest(path)
                if manifest.functional_blocks:
                    source_block_override = manifest.functional_blocks
        except Exception:
            pass

        recursive = generate_recursive_manifests(path, source_block_override=source_block_override)
        if recursive:
            manifests_dir = path / ".architecture" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            for block_id, rm in recursive.items():
                out = manifests_dir / f"{block_id}.json"
                out.write_text(json.dumps(rm.manifest.to_dict(), indent=2))
            result["recursive_manifests"] = list(recursive.keys())
            result["manifests_dir"] = str(manifests_dir.relative_to(path))
            result["manifest_details"] = [
                {
                    "block_id": bid,
                    "block_name": rm.block_name,
                    "modules": len(rm.manifest.modules),
                    "interfaces": len(rm.manifest.interfaces) if hasattr(rm.manifest, 'interfaces') else 0,
                }
                for bid, rm in recursive.items()
            ]
        else:
            result["recursive_manifests"] = []
            result["manifest_note"] = "No recursive manifests generated (no F-blocks found)"
    except Exception as e:
        result["manifest_error"] = str(e)

    return result

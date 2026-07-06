"""architect_extract MCP tool — extract architecture from source code."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def _get_surrogate():
    """Get the configured surrogate model for extraction.

    Tries arch-agent Surrogate (Ollama) first, returns None if unavailable.
    """
    try:
        from arch_agent.training.surrogate import Surrogate
        return Surrogate(model="qwen2.5:7b")
    except (ImportError, Exception):
        return None


async def extract_architecture(
    repo_path: str,
    focus: str = "all",
) -> str:
    """Extract architecture model from a repository.

    Args:
        repo_path: Path to the repository root.
        focus: Focus scope - "all", a layer name, or a component pattern.

    Returns:
        YAML string of the extracted architecture model.
    """
    path = Path(repo_path)
    if not path.exists():
        return f"Error: Repository path does not exist: {repo_path}"

    try:
        # Step 1: Generate reality manifest (AST scan)
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(path)

        # Step 2: Use surrogate model to synthesize architecture from manifest
        surrogate = await _get_surrogate()
        if surrogate is None:
            # Fallback: return manifest as basic YAML structure
            return yaml.dump(manifest, default_flow_style=False, sort_keys=False)

        # Build prompt from manifest
        system = (
            "You are an architecture extraction engine. Given a code manifest, "
            "produce a YAML architecture model following the 7-entity, 8-relationship schema. "
            "Entities: actors, capabilities, behaviors, interfaces, constraints, layers, components. "
            "Output ONLY valid YAML."
        )

        manifest_text = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        user = f"Extract architecture from this manifest:\n\n```yaml\n{manifest_text[:12000]}\n```"

        if focus != "all":
            user += f"\n\nFocus specifically on: {focus}"

        result = await surrogate.generate(system, user)

        # Strip markdown fences if present
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]

        return result.strip()

    except Exception as e:
        return f"Error during extraction: {e}"

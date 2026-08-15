# src/opencode_arch/mcp/tools/validate.py
"""architect_validate MCP tool — validate architecture model quality."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def validate_architecture(
    model_yaml: str,
    repo_path: str = "",
) -> dict[str, Any]:
    """Validate an architecture model for structural correctness.

    Args:
        model_yaml: The YAML architecture model string to validate.
            If empty and repo_path is provided, reads from .architecture-model.yaml.
        repo_path: Optional repository path to read model from disk.

    Returns:
        Dict with: score (0-100), issues (list), entity_count, relationship_count, is_valid.
    """
    try:
        # V1: Read from disk if model_yaml is empty/looks like a file path
        if not model_yaml or not model_yaml.strip():
            if repo_path:
                model_file = Path(repo_path) / ".architecture-model.yaml"
                if model_file.exists():
                    model_yaml = model_file.read_text()
                else:
                    return {
                        "score": 0,
                        "issues": [f"No model found at {model_file}. Run architect_extract first."],
                        "entity_count": 0,
                        "relationship_count": 0,
                        "is_valid": False,
                    }
            else:
                return {
                    "score": 0,
                    "issues": [
                        "Empty model_yaml. Pass inline YAML content or provide repo_path to read from disk."
                    ],
                    "entity_count": 0,
                    "relationship_count": 0,
                    "is_valid": False,
                }

        # V6: Detect file path passed instead of YAML content
        stripped = model_yaml.strip()
        if (
            not stripped.startswith(("{", "[", "-", "#"))
            and "\n" not in stripped
            and (
                stripped.startswith("/")
                or stripped.startswith("~")
                or stripped.endswith(".yaml")
                or stripped.endswith(".yml")
            )
        ):
            # Looks like a file path, try to read it
            candidate = Path(stripped).expanduser()
            if candidate.exists():
                model_yaml = candidate.read_text()
            else:
                return {
                    "score": 0,
                    "issues": [
                        f"'{stripped}' looks like a file path but doesn't exist. "
                        "Pass inline YAML content, not a file path. "
                        "Or use repo_path parameter to read from .architecture-model.yaml."
                    ],
                    "entity_count": 0,
                    "relationship_count": 0,
                    "is_valid": False,
                }

        raw = yaml.safe_load(model_yaml)
        if raw is None:
            return {
                "score": 0,
                "issues": ["Empty YAML document"],
                "entity_count": 0,
                "relationship_count": 0,
                "is_valid": False,
            }

        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        model = _parse_raw(raw)
        validation_result = validate_model(model)

        try:
            from opencode_arch.telemetry.collector import drain_and_store

            drain_and_store(tool="architect_validate", repo="")
        except Exception:
            pass

        return {
            "score": validation_result.score,
            "issues": [str(issue) for issue in validation_result.issues],
            "entity_count": model.entity_count,
            "relationship_count": model.relationship_count,
            "is_valid": validation_result.is_valid,
        }

    except Exception as e:
        return {
            "score": 0,
            "issues": [f"Parse/validation error: {e}"],
            "entity_count": 0,
            "relationship_count": 0,
            "is_valid": False,
        }

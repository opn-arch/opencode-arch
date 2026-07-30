# src/opencode_arch/mcp/tools/validate.py
"""architect_validate MCP tool — validate architecture model quality."""
from __future__ import annotations

from typing import Any

import yaml


async def validate_architecture(
    model_yaml: str,
) -> dict[str, Any]:
    """Validate an architecture model for structural correctness.

    Args:
        model_yaml: The YAML architecture model string to validate.

    Returns:
        Dict with: score (0-100), issues (list), entity_count, relationship_count, is_valid.
    """
    try:
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

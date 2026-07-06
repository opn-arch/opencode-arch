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
        Dict with score (0-100), issues list, entity_count, relationship_count.
    """
    try:
        # Parse YAML string into raw dict
        raw = yaml.safe_load(model_yaml)
        if raw is None:
            return {
                "score": 0,
                "issues": ["Empty YAML document"],
                "entity_count": 0,
                "relationship_count": 0,
            }

        # Parse raw dict into typed ArchitectureModel
        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        model = _parse_raw(raw)
        validation_result = validate_model(model)

        result: dict[str, Any] = {
            "score": validation_result.score,
            "issues": [str(issue) for issue in validation_result.issues],
            "entity_count": model.entity_count,
            "relationship_count": model.relationship_count,
        }

        return result

    except Exception as e:
        return {
            "score": 0,
            "issues": [f"Parse/validation error: {e}"],
            "entity_count": 0,
            "relationship_count": 0,
        }

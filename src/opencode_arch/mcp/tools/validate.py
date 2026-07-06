"""architect_validate MCP tool — validate architecture model quality."""
from __future__ import annotations

from typing import Any

import yaml


async def _get_oracle():
    """Get the oracle for quality scoring (optional)."""
    try:
        from opencode_arch.oracle.copilot_relay import CopilotRelayOracle
        return CopilotRelayOracle()
    except Exception:
        return None


async def validate_architecture(
    model_yaml: str,
    source_code: str | None = None,
    use_oracle: bool = False,
) -> dict[str, Any]:
    """Validate an architecture model for structural correctness.

    Args:
        model_yaml: The YAML architecture model string to validate.
        source_code: Optional source code to validate against (enables oracle scoring).
        use_oracle: Whether to use frontier model for quality scoring.

    Returns:
        Dict with score (0-100), issues list, and optionally oracle_score.
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

        # Optional oracle scoring against source code
        if use_oracle and source_code:
            oracle = await _get_oracle()
            if oracle:
                oracle_result = await oracle.score_extraction(
                    model_yaml=model_yaml,
                    source_code=source_code,
                )
                result["oracle_score"] = oracle_result.get("score", 0)
                result["oracle_feedback"] = oracle_result.get("feedback", "")

        return result

    except Exception as e:
        return {
            "score": 0,
            "issues": [f"Parse/validation error: {e}"],
            "entity_count": 0,
            "relationship_count": 0,
        }

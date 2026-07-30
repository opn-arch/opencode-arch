"""architect_extract MCP tool — validate and store an architecture extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def store_extraction(
    repo_path: str,
    model_yaml: str,
    context_tokens: int = 0,
) -> dict[str, Any]:
    """Validate and store an architecture model extraction.

    Called AFTER the agent has produced a YAML architecture model.
    Validates the model, writes it to .architecture-model.yaml,
    and records telemetry.

    Args:
        repo_path: Path to the repository root (where to save the model).
        model_yaml: The YAML architecture model produced by the agent.
        context_tokens: How many tokens of context the agent used (for telemetry).

    Returns:
        Dict with: stored (bool), score (int), issues (list), telemetry_recorded (bool).
    """
    path = Path(repo_path)

    try:
        # Parse the YAML
        raw = yaml.safe_load(model_yaml)
        if not isinstance(raw, dict):
            return {"stored": False, "error": "YAML did not parse to a dict", "score": 0}

        # Validate using architecture_model
        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        model = _parse_raw(raw)
        validation = validate_model(model)

        score = validation.score
        issues = [str(issue) for issue in validation.issues]

        # Write to repo
        output_path = path / ".architecture-model.yaml"
        output_path.write_text(model_yaml)

        # Record telemetry
        telemetry_recorded = False
        try:
            from opencode_arch.telemetry.store import TelemetryStore
            store = TelemetryStore()
            store.record(
                tool="architect_extract",
                repo=str(path.name),
                context_tokens=context_tokens,
                output_quality=score,
                iterations=1,
            )
            telemetry_recorded = True
        except Exception:
            pass  # Telemetry failure shouldn't block the tool

        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_extract", repo=path.name)
        except Exception:
            pass

        return {
            "stored": True,
            "score": score,
            "issues": issues,
            "path": str(output_path),
            "telemetry_recorded": telemetry_recorded,
        }

    except yaml.YAMLError as e:
        return {"stored": False, "error": f"Invalid YAML: {e}", "score": 0}
    except Exception as e:
        return {"stored": False, "error": f"Validation failed: {e}", "score": 0}

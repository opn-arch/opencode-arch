"""architect_extract post-processing — store an architecture extraction.

C6 severance: the AMS validation / manifest / decompose / docs pipeline that
previously ran here was removed. This now simply persists the agent-produced
YAML model (with a snapshot of any prior model) and records telemetry. The
openAG LLM extraction path in ``opencode_arch.cli.extract`` is unchanged.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from opencode_arch.mcp.quality import with_quality


# Lazy import to allow patching in tests
def _get_telemetry_store():
    from opencode_arch.telemetry.store import TelemetryStore

    return TelemetryStore


@with_quality
async def store_extraction(
    repo_path: str,
    model_yaml: str,
    context_tokens: int = 0,
) -> dict[str, Any]:
    """Store an architecture model extraction (no AMS post-processing).

    Parses the YAML, snapshots any prior ``.architecture-model.yaml``, writes
    the new model, and records telemetry.

    Args:
        repo_path: Path to the repository root (where to save the model).
        model_yaml: The YAML architecture model produced by the agent.
        context_tokens: How many tokens of context the agent used (for telemetry).

    Returns:
        Dict with: stored (bool), score (int), issues (list), path (str),
        telemetry_recorded (bool), pipeline (dict), warnings (list).
    """
    path = Path(repo_path)
    pipeline: dict[str, Any] = {}
    warnings: list[str] = []

    # Parse the YAML
    try:
        raw = yaml.safe_load(model_yaml)
    except Exception as e:
        return {
            "stored": False,
            "error": f"YAML did not parse: {e}",
            "score": 0,
            "path": "",
            "pipeline": pipeline,
            "warnings": warnings,
        }
    if not isinstance(raw, dict):
        return {
            "stored": False,
            "error": "YAML did not parse to a dict",
            "score": 0,
            "path": "",
            "pipeline": pipeline,
            "warnings": warnings,
        }

    model_file = path / ".architecture-model.yaml"

    # Snapshot existing model before overwrite (cap at 10)
    try:
        if model_file.exists():
            snapshot_dir = path / ".architecture" / "snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().isoformat().replace(":", "-")
            snapshot_path = snapshot_dir / f"{timestamp}.yaml"
            shutil.copy2(model_file, snapshot_path)
            snapshots = sorted(snapshot_dir.glob("*.yaml"))
            for old in snapshots[:-10]:
                old.unlink()
            pipeline["snapshot"] = {"status": "ok", "detail": str(snapshot_path)}
        else:
            pipeline["snapshot"] = {"status": "ok", "detail": "no prior model"}
    except Exception as e:
        pipeline["snapshot"] = {"status": "error", "error": str(e)}

    # Write the model
    try:
        model_file.write_text(model_yaml)
    except Exception as e:
        return {
            "stored": False,
            "error": f"Failed to write model: {e}",
            "score": 0,
            "path": "",
            "pipeline": pipeline,
            "warnings": warnings,
        }

    # Record telemetry
    telemetry_recorded = False
    try:
        TelemetryStore = _get_telemetry_store()
        store = TelemetryStore()
        store.record(
            tool="architect_extract",
            repo=str(path.name),
            context_tokens=context_tokens,
            output_quality=0,
            iterations=1,
        )
        telemetry_recorded = True
        pipeline["telemetry"] = {"status": "ok"}
    except Exception as e:
        pipeline["telemetry"] = {"status": "error", "error": str(e)}

    return {
        "stored": True,
        "score": 0,
        "issues": [],
        "path": str(model_file),
        "telemetry_recorded": telemetry_recorded,
        "pipeline": pipeline,
        "warnings": warnings,
    }

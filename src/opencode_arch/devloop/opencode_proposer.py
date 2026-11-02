"""Real-OpenCode proposer plugin for the self-improvement dev-loop.

Converts an openAG :class:`~openag.ai.work_order.WorkOrder` into an openAG
ModelPatch dict (``{"ops": [...]}``) by asking a REAL OpenCode-backed LLM
provider to author the patch.

Import-safe: importing this module does NOT spawn OpenCode or import any
heavy/live-runner dependency. The provider is only instantiated and called
INSIDE :func:`propose`. Config the dev-loop to use it via::

    plugin: "opencode_arch.devloop.opencode_proposer:propose"
"""
from __future__ import annotations

from typing import Any

# Minimal ModelPatch shape used only to steer the structured instruction.
_PATCH_SCHEMA: dict[str, Any] = {
    "ops": [
        {
            "kind": "add",
            "target": "entity",
            "entity_kind": "components",
            "value": {"id": "COMP-X", "name": "X", "kind": "Component"},
        }
    ]
}


def _build_prompt(wo) -> str:
    """Build an authoring prompt from the WorkOrder intent + parameters."""
    lines = [
        "You are an architecture model editor.",
        "Produce an openAG ModelPatch that satisfies the following intent.",
        "",
        f"Intent: {wo.intent}",
    ]
    params = getattr(wo, "parameters", None)
    if params:
        lines.append(f"Parameters: {params}")
    lines += [
        "",
        "The patch MUST be a JSON object of the form:",
        '{"ops": [{"kind": "add", "target": "entity", '
        '"entity_kind": "components", "value": {"id": "COMP-OPENCODE-LIVE", '
        '"name": "OpenCode Live", "kind": "Component"}}]}',
        "",
        "Add exactly one new component with id 'COMP-OPENCODE-LIVE'.",
    ]
    return "\n".join(lines)


def propose(wo) -> dict:
    """Author a ModelPatch for ``wo`` via a real OpenCode-backed provider.

    Returns the structured ModelPatch dict. An invalid result is returned
    as-is so the openAG worker can reject it — no silent fabrication.
    """
    from opencode_arch.llm.providers.mcp import MCPProvider

    prompt = _build_prompt(wo)
    return MCPProvider().structured(prompt, _PATCH_SCHEMA)

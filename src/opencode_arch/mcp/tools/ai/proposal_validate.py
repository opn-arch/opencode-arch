"""MCP tool: validate an AI Proposal against its WorkOrder + input slices (T17).

Envelope
--------
Success: ``{"ok": True, "report": {"passed": bool, "findings": [...]}}``.

Errors
------
* ``INVALID_ARGUMENT`` — ``proposal`` not a dict; ``work_order_id`` empty
  / non-string; ``slice_ids`` not a list; any ``slice_id`` empty / non-string.
* ``NOT_FOUND`` — repo missing, or ``details.reason`` in
  ``{"workorder_missing", "slice_missing"}``.
* ``SCHEMA_VIOLATION`` — proposal parse failure (``details.errors``); or
  ``details.reason`` in ``{"workorder_malformed", "slice_malformed"}``.
* ``INTERNAL`` — unexpected fallthrough.
"""
from __future__ import annotations

import yaml

from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented


@instrumented("mcp_tool:architect_proposal_validate")
@tool_result
async def architect_proposal_validate_tool(
    repo_path: str,
    proposal: dict,
    work_order_id: str,
    slice_ids: list[str],
) -> dict:
    """Validate a proposal against a persisted WorkOrder and input slices."""
    if not isinstance(proposal, dict):
        return err("INVALID_ARGUMENT", "proposal must be a dict")
    if not isinstance(work_order_id, str) or not work_order_id:
        return err(
            "INVALID_ARGUMENT", "work_order_id must be a non-empty string"
        )
    if not isinstance(slice_ids, list):
        return err("INVALID_ARGUMENT", "slice_ids must be a list")
    for sid in slice_ids:
        if not isinstance(sid, str) or not sid:
            return err(
                "INVALID_ARGUMENT",
                "each slice_id must be a non-empty string",
            )

    repo = resolve_repo(repo_path)

    from architecture_model.ai.proposals import proposal_from_dict
    from architecture_model.ai.validators import validate
    from architecture_model.ai.work_order import WorkOrder

    # Parse proposal.
    try:
        parsed_proposal = proposal_from_dict(proposal)
    except Exception as exc:  # noqa: BLE001
        return err(
            "SCHEMA_VIOLATION",
            f"proposal parse failed: {exc}",
            errors=[str(exc)],
        )

    # Load WorkOrder.
    wo_path = (
        repo / ".architecture" / "ai" / "workorders" / f"{work_order_id}.yaml"
    )
    if not wo_path.exists():
        return err(
            "NOT_FOUND",
            f"work order {work_order_id!r} not found",
            reason="workorder_missing",
            work_order_id=work_order_id,
        )
    try:
        wo_data = yaml.safe_load(wo_path.read_text(encoding="utf-8"))
        wo = WorkOrder.from_dict(wo_data)
    except Exception as exc:  # noqa: BLE001
        return err(
            "SCHEMA_VIOLATION",
            f"work order malformed: {exc}",
            reason="workorder_malformed",
            work_order_id=work_order_id,
        )

    # Load slices.
    input_slices: dict[str, dict] = {}
    slices_dir = repo / ".architecture" / "lifecycle" / "slices"
    for sid in slice_ids:
        sp = slices_dir / f"{sid}.yaml"
        if not sp.exists():
            return err(
                "NOT_FOUND",
                f"slice {sid!r} not found",
                reason="slice_missing",
                slice_id=sid,
            )
        try:
            data = yaml.safe_load(sp.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            return err(
                "SCHEMA_VIOLATION",
                f"slice {sid!r} malformed: {exc}",
                reason="slice_malformed",
                slice_id=sid,
            )
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return err(
                "SCHEMA_VIOLATION",
                f"slice {sid!r} must be a mapping",
                reason="slice_malformed",
                slice_id=sid,
            )
        input_slices[sid] = data

    report = validate(
        parsed_proposal, work_order=wo, input_slices=input_slices
    )
    return ok(
        {
            "report": {
                "passed": report.passed,
                "findings": [f.to_dict() for f in report.findings],
            }
        }
    )


__all__ = ["architect_proposal_validate_tool"]

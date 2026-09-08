"""MCP tool: submit an AI WorkOrder and create its tracking Job.

Envelope
--------
Success: ``{"ok": True, "work_order_id": <str>, "job_id": <str>}``

Errors
------
* ``INVALID_ARGUMENT`` — ``work_order`` is not a dict.
* ``NOT_FOUND`` — ``repo_path`` does not exist.
* ``SCHEMA_VIOLATION`` — WorkOrder.from_dict raises OR
  ``validate_schema()`` returns errors. ``details.errors`` is a
  ``list[str]``.
* ``PRECONDITION_FAILED`` — a WorkOrder with the same id already exists
  on disk (idempotency guard). ``details.work_order_id``,
  ``details.reason == "already_exists"``.
* ``INTERNAL`` — unexpected exceptions.
"""
from __future__ import annotations

from datetime import datetime, timezone

import yaml

from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented


@instrumented("mcp_tool:architect_workorder_submit")
@tool_result
async def architect_workorder_submit_tool(
    repo_path: str,
    work_order: dict,
) -> dict:
    """Persist a WorkOrder, create its Job, and journal the event."""
    if not isinstance(work_order, dict):
        return err("INVALID_ARGUMENT", "work_order must be a dict")

    repo = resolve_repo(repo_path)

    from architecture_model.ai.jobs import JobStore
    from architecture_model.ai.work_order import WorkOrder
    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.journal import Journal

    # Parse.
    try:
        wo = WorkOrder.from_dict(work_order)
    except (KeyError, TypeError, ValueError) as exc:
        return err(
            "SCHEMA_VIOLATION",
            f"work_order parse failed: {exc}",
            errors=[str(exc)],
        )

    # Schema validation.
    schema_errors = wo.validate_schema()
    if schema_errors:
        return err(
            "SCHEMA_VIOLATION",
            "work_order failed schema validation",
            errors=list(schema_errors),
        )

    # Persist WorkOrder atomically (idempotency guard).
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_path = wo_dir / f"{wo.id}.yaml"
    if wo_path.exists():
        return err(
            "PRECONDITION_FAILED",
            f"work_order {wo.id!r} already exists",
            work_order_id=wo.id,
            reason="already_exists",
        )
    wo_dir.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        wo.to_dict(),
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )
    write_atomic(wo_path, text.encode("utf-8"))

    # Create Job.
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo.id, actor=wo.requested_by)

    # Journal the submission.
    journal = Journal(repo / ".architecture" / "ai" / "workorders.journal.jsonl")
    journal.record(
        "ai.workorder.submit",
        {
            "kind": "ai.workorder.submit",
            "work_order_id": wo.id,
            "job_id": job.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requested_by": wo.requested_by,
        },
    )

    return ok({"work_order_id": wo.id, "job_id": job.id})


__all__ = ["architect_workorder_submit_tool"]

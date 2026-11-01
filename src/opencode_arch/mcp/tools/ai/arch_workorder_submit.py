"""arch_workorder_submit — persist an AI WorkOrder + create its tracking Job (openAG-native).

openAG-native replacement for the AMS workorder-submit tool. Parses + schema-validates
the WorkOrder via ``openag.ai.work_order``, persists it atomically under
``<repo>/.architecture/ai/workorders/<id>.yaml`` with an idempotency guard, creates a draft
Job via ``openag.ai.jobs.JobStore``, and fail-soft journals the submission. No AMS dependency.

Envelope
--------
Success: ``{"ok": True, "work_order_id": <str>, "job_id": <str>}``

Errors
------
* ``INVALID_ARGUMENT`` — ``work_order`` is not a dict; or ``repo_path`` invalid.
* ``NOT_FOUND`` — ``repo_path`` does not exist.
* ``SCHEMA_VIOLATION`` — WorkOrder.from_dict raises OR ``validate_schema()`` returns errors
  (``details.errors`` is ``list[str]``).
* ``PRECONDITION_FAILED`` — a WorkOrder with the same id already exists
  (``details.work_order_id``, ``details.reason == "already_exists"``).
* ``INTERNAL`` — unexpected exceptions.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_workorder_submit(repo_path: str = "", work_order: dict | None = None) -> dict:
    """Persist a WorkOrder, create its Job, journal the submission. See module docstring."""
    import json
    import os

    import yaml

    from opencode_arch.mcp.envelope import err, ok, resolve_repo
    from openag.ai.jobs import JobStore
    from openag.ai.work_order import WorkOrder
    from openag.observe._fields import now_iso

    if not isinstance(work_order, dict):
        return err("INVALID_ARGUMENT", "work_order must be a dict")

    repo = resolve_repo(repo_path)

    # Parse.
    try:
        wo = WorkOrder.from_dict(work_order)
    except (KeyError, TypeError, ValueError) as exc:
        return err("SCHEMA_VIOLATION", f"work_order parse failed: {exc}", errors=[str(exc)])

    # Schema validation.
    schema_errors = wo.validate_schema()
    if schema_errors:
        return err("SCHEMA_VIOLATION", "work_order failed schema validation", errors=list(schema_errors))

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
    text = yaml.safe_dump(wo.to_dict(), sort_keys=True, default_flow_style=False, allow_unicode=True)
    tmp = wo_dir / f".{wo.id}.yaml.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, wo_path)

    # Create Job (draft).
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo.id, actor=wo.requested_by)

    # Journal the submission (fail-soft).
    try:
        jp = repo / ".architecture" / "ai" / "workorders.journal.jsonl"
        jp.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "type": "ai.workorder.submit",
                "work_order_id": wo.id,
                "job_id": job.id,
                "timestamp": now_iso(),
                "requested_by": wo.requested_by,
            }
        )
        with open(jp, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass

    return ok({"work_order_id": wo.id, "job_id": job.id})


__all__ = ["arch_workorder_submit"]

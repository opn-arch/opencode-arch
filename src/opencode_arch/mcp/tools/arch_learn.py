"""arch_learn — B-ROUND lesson-materialization gate MCP tool.

Where ``arch_lessons`` is the proprioception READ surface ("what keeps
going wrong"), ``arch_learn`` is the first WRITE join of the learning
loop: it mines lessons with the SAME four-signal assembly, selects the
highest-ranked lesson (or a caller-targeted one via ``subject`` /
``lesson_type``), builds a :class:`~openag.ai.work_order.WorkOrder` via
``lesson_to_work_order``, persists it, and creates a Job that STOPS at
``draft`` — the review gate.

This tool materializes a draft WorkOrder + Job only. It does NOT submit,
run, or apply anything: the draft job is routed through the existing
``proposal_validate → proposal_apply`` review pipeline downstream. Heavy
``openag.*`` imports are lazy so the module stays importable without the
dependency present.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.envelope import err, ok, resolve_repo
from opencode_arch.mcp.tools._generations import generation_store
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc

# Real entity node kinds — only these are valid targets for owed-promise gap
# emission (mirrors arch_lessons._REAL_ENTITY_KINDS exactly).
_REAL_ENTITY_KINDS = frozenset({
    "Component", "Capability", "Behavior", "Interface",
    "Constraint", "Actor", "Layer", "System",
})


def _current_revision(resolved) -> str:
    """Return the current generation id, or ``"0000000"`` if none published."""
    from openag.lifecycle.package import list_generations, load_generation

    if list_generations(str(resolved))["count"] == 0:
        return "0000000"
    return load_generation(str(resolved))["gen_id"]


@arch_tool
async def arch_learn(
    repo_path: str,
    subject: str | None = None,
    lesson_type: str | None = None,
) -> dict:
    """Materialize a draft WorkOrder from the top mined lesson (gated)."""
    doc = load_doc(repo_path)
    g = build_graph(doc)

    from openag.kernel.gate import emit_gaps_graph
    from openag.kernel.lessons import LessonStore, derive_lessons, digest
    from openag.observe import journal
    from openag.observe.audit import audit_observations

    resolved = resolve_repo(repo_path)

    # --- lesson assembly (mirrors arch_lessons exactly) ------------------
    observations = journal.read(resolved)
    history = generation_store(repo_path).all()
    flags = audit_observations(g, observations, history)

    gaps: list[dict] = []
    for eid in g.entity_nodes():
        if g.node(eid).get("kind") in _REAL_ENTITY_KINDS:
            gaps += emit_gaps_graph(g, eid)

    lessons = derive_lessons(history, observations, gaps, flags)
    store = LessonStore(resolved)
    store.extend(lessons)

    ranked = digest(store, g)["lessons"]

    # --- select target lesson --------------------------------------------
    if subject is not None or lesson_type is not None:
        top = next(
            (
                r
                for r in ranked
                if (subject is None or r.get("subject") == subject)
                and (lesson_type is None or r.get("lesson_type") == lesson_type)
            ),
            None,
        )
        if top is None:
            return err("NOT_FOUND", "no matching lesson", reason="no_lessons")
    else:
        if not ranked:
            return err("NOT_FOUND", "no lessons mined", reason="no_lessons")
        top = ranked[0]

    # --- build + persist WorkOrder, create draft Job (the gate) ----------
    import yaml

    from openag.ai.jobs import JobStore
    from openag.kernel.lesson_bridge import lesson_to_work_order
    from openag.lifecycle.atomic_store import write_atomic

    current_rev = _current_revision(resolved)
    wo = lesson_to_work_order(top, model_revision=current_rev)

    wo_dir = resolved / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(
        wo_dir / f"{wo.id}.yaml",
        yaml.safe_dump(wo.to_dict(), sort_keys=True).encode("utf-8"),
    )

    job = JobStore(root=resolved).create(work_order_id=wo.id, actor="arch_learn")

    return ok({
        "work_order_id": wo.id,
        "job_id": job.id,
        "job_state": job.state.value,
        "intent": wo.intent,
    })

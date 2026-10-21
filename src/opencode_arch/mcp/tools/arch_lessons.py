"""arch_lessons — B-ROUND proprioception lesson-mining read MCP tool.

A thin OCA read-surface over the openAG kernel ``openag.kernel.lessons`` miner
(the health/flags/history layer answers "what is wrong NOW"; this answers
"what keeps going wrong"). It assembles the four proprioception signal streams
— generation history, runtime observations, owed-promise gaps, and audit
flags — mines them into lessons, persists them to the append-only
``<repo>/.architecture/lessons.jsonl`` store, and returns the ranked digest
plus reviewable proposal STUBS.

This tool EMITS proposal payloads + guidance only. It does NOT mutate the
model and does NOT submit any workorder itself — the stubs are routed through
the existing ``architect_workorder_submit → proposal_validate →
proposal_apply`` review pipeline downstream.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a directory
of ``*.v3.yaml`` fragments. Observations and generations are read from
``<repo_path>/.architecture/``. Heavy ``openag.*`` imports are lazy so the
module stays importable without the dependency present.
"""
from __future__ import annotations

import os

from opencode_arch.mcp.envelope import resolve_repo, tool_result
from opencode_arch.mcp.tools._observe import observe_tool_call
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc

# Generation ledger location (mirrors arch_history.py's duplicated constant;
# the duplication is pre-existing and acceptable per the task brief).
_GENERATIONS_REL = os.path.join(".architecture", "generations")

# Real entity node kinds — only these are valid targets for owed-promise gap
# emission. Promise / evidence scaffolding nodes are excluded.
_REAL_ENTITY_KINDS = frozenset({
    "Component", "Capability", "Behavior", "Interface",
    "Constraint", "Actor", "Layer", "System",
})


@tool_result
async def arch_lessons(repo_path: str) -> dict:
    """Return mined lessons + reviewable proposal stubs (proprioception)."""
    with observe_tool_call(repo_path, "arch_lessons"):
        doc = load_doc(repo_path)
        g = build_graph(doc)

        from openag.kernel.gate import emit_gaps_graph
        from openag.kernel.generations import GenerationStore
        from openag.kernel.lessons import LessonStore, derive_lessons, digest
        from openag.observe import journal
        from openag.observe.audit import audit_observations

        resolved = resolve_repo(repo_path)

        # 1. runtime observations (model-independent journal).
        observations = journal.read(resolved)

        # 2. generation history (health-enriched ledger).
        gen_root = os.path.join(str(resolved), _GENERATIONS_REL)
        history = GenerationStore(root=gen_root).all()

        # 3. audit flags — history MUST be passed so the obs:unreplayable flag
        #    (consumed by the persistent-unreplayable miner) is produced.
        flags = audit_observations(g, observations, history)

        # 4. owed-promise gaps, flattened across all real entity nodes.
        gaps: list[dict] = []
        for eid in g.entity_nodes():
            if g.node(eid).get("kind") in _REAL_ENTITY_KINDS:
                gaps += emit_gaps_graph(g, eid)

        lessons = derive_lessons(history, observations, gaps, flags)

        # Persist to the append-only ledger via extend(), which skips lessons
        # already present (by ts-free content key). This keeps repeat calls on
        # an unchanged model from bloating the ledger with identical duplicates
        # while still recording genuinely new lessons. extend() is fail-soft
        # per append (a persistence failure is simply not counted) — a write
        # failure must never fail the read.
        store = LessonStore(resolved)
        store.extend(lessons)

        result = digest(store, g)
        return {"digest": result, "proposals": result["proposals"]}

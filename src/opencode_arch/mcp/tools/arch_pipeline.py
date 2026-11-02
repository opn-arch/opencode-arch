"""arch_pipeline — native openAG pipeline-orchestration MCP writer tool.

Behavioral replacement for the legacy AMS ``architect_pipeline`` tool. Where
the legacy tool ran a 10-stage cached extraction pipeline
(observe -> ... -> emit) with stage-by-stage LLM enrichment and
``architecture_model`` validation, this native writer scans the repo's source
tree, builds the gen-0 seed graph, runs the openAG B-ROUND fixpoint via
:func:`openag.kernel.pipeline.run_pipeline`, and commits the result as a new
generation in the repo's diachronic ledger.

Flow:

1. :func:`openag.graph.ground.scan_ground_graph` scans ``<repo>/src`` (or the
   repo root when there is no ``src/``) into a deterministic AST ground graph.
2. :func:`openag.extract.pipeline._seed_doc` derives the gen-0 top-down seed
   doc (one System + one Component claiming every scanned file); it is built
   into a :class:`~openag.graph.model_graph.ModelGraph`.
3. :func:`openag.kernel.pipeline.run_pipeline` runs the B-ROUND least-fixpoint
   (deterministic under a pinned clock, no provider).
4. The grounded graph's entities are committed as a new generation through
   :class:`openag.kernel.generations.GenerationStore`.

No ``architecture_model`` dependency.

Legacy-compatible params ``stage`` / ``recursive`` / ``resolutions`` /
``clear_cache`` / ``scope`` are accepted for call-site compatibility.
``stage`` is threaded to ``run_pipeline`` (which echoes it; the first cut runs
the full fixpoint — see ``run_pipeline``). The remaining legacy params
(``recursive`` / ``resolutions`` / ``clear_cache`` / ``scope``) are accepted
and intentionally ignored — the native B-ROUND path has no cached-stage /
scoped-subsystem / enrichment-resolution surface.
"""

from __future__ import annotations

from opencode_arch.mcp.envelope import resolve_repo
from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_pipeline(
    repo_path: str,
    stage: str = "",
    recursive: bool = True,
    resolutions: list[dict] | None = None,
    clear_cache: bool = False,
    scope: str = "",
) -> dict:
    """Run the openAG B-ROUND pipeline over the repo and commit a generation."""
    resolved = resolve_repo(repo_path)

    from openag.graph.ground import scan_ground_graph
    from openag.graph.model_graph import ModelGraph
    from openag.extract.pipeline import _seed_doc
    from openag.kernel.pipeline import run_pipeline
    from openag.kernel.generations import GenerationStore
    from openag.model_io import save_model_dir
    from openag.observe._fields import now_iso

    src_root = resolved / "src"
    if not src_root.is_dir():
        src_root = resolved

    now = now_iso()
    ground = scan_ground_graph(src_root)
    g = ModelGraph.from_doc(_seed_doc(ground, now))
    summary = run_pipeline(g, stage=stage, ground=ground, now=now)

    entities = g.entities_flat()
    gen_root = str(resolved / ".architecture" / "generations" / "openAG-tool")
    store = GenerationStore(root=gen_root)
    gen_id = store.record(entities, reason="arch_pipeline")

    model_dir = save_model_dir(
        str(resolved / ".architecture" / "model"), g.to_doc()
    )

    grounding = summary["grounding"]
    return {
        "generation": gen_id,
        "model_dir": model_dir,
        "stage": summary["stage"],
        "iterations": summary["iterations"],
        "converged": grounding["converged"],
        "grounded": len(grounding["grounded"]),
        "ungrounded": len(grounding["ungrounded"]),
        "gaps": len(summary["gaps"]),
        "entities": len(entities),
    }

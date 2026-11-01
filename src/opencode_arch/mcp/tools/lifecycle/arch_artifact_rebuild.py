"""arch_artifact_rebuild — render openAG artifacts over the live model doc.

openAG-native replacement for the AMS artifact rebuild executor. Loads the live
merged model doc, renders each artifact spec via the openAG viewer (``html`` ->
self-contained viewer HTML; ``overview``/``components``/``promises`` -> markdown
docs), and writes them atomically under ``<repo>/.architecture/artifacts/<id>.<ext>``.
The current generation id (``GenerationStore.latest()``) is stamped onto the
report as the provenance anchor. No legacy AMS dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_artifact_rebuild(
    repo_path: str = "",
    artifact_specs: list[dict] | None = None,
    force: bool = False,
) -> dict:
    """Render + write openAG artifacts over the live model doc. See module docstring."""
    from opencode_arch.mcp.envelope import err, resolve_repo
    from opencode_arch.mcp.tools._openag_loader import load_doc
    from openag.lifecycle import store_root
    from openag.lifecycle.artifacts import ArtifactCycle, UnknownRef, rebuild
    from openag.kernel.generations import GenerationStore

    doc = load_doc(repo_path)  # FileNotFoundError -> NOT_FOUND (missing repo/model)
    repo = resolve_repo(repo_path)

    gen = GenerationStore(store_root(str(repo))).latest()
    generation = gen["gen_id"] if gen else None

    if artifact_specs is None:
        artifact_specs = []

    try:
        report = rebuild(str(repo), doc, artifact_specs, generation=generation, force=force)
    except (ArtifactCycle, UnknownRef) as exc:
        return err("PRECONDITION_FAILED", str(exc))

    return {"ok": True, **report}

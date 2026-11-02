"""arch_extract — native openAG extract-and-commit MCP writer tool.

Behavioral replacement for the legacy AMS ``architect_extract`` store tool.
Where the legacy tool parsed an agent-authored YAML model, validated it via
``architecture_model``, and cascaded a pile of derived AMS artifacts, this
native writer runs the openAG extract pipeline over the repo's source tree
and commits the result as a new generation in the repo's diachronic ledger.

Flow:

1. :func:`openag.extract.pipeline.extract_model` scans ``<repo>/src`` (or the
   repo root when there is no ``src/``) into a v3 model doc via the
   scan -> B-ROUND pipeline (deterministic under a pinned clock).
2. The doc's entities are committed as a new generation through
   :class:`openag.kernel.generations.GenerationStore`, persisted under
   ``<repo>/.architecture/generations/openAG-tool``.

No ``architecture_model`` dependency. The legacy-compatible ``model_yaml`` /
``context_tokens`` params are accepted for call-site compatibility and
intentionally ignored — the native pipeline derives the model from source,
not from an agent-supplied YAML blob.
"""

from __future__ import annotations

from opencode_arch.mcp.envelope import resolve_repo
from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_extract(
    repo_path: str,
    model_yaml: str = "",
    context_tokens: int = 0,
) -> dict:
    """Extract a v3 model from the repo source and commit a generation."""
    resolved = resolve_repo(repo_path)

    from openag.extract.pipeline import extract_model
    from openag.kernel.generations import GenerationStore
    from openag.model_io import save_model_dir

    src_root = resolved / "src"
    if not src_root.is_dir():
        src_root = resolved

    doc = extract_model(src_root)
    entities = [
        e
        for items in (doc.get("entities") or {}).values()
        for e in items
    ]

    gen_root = str(resolved / ".architecture" / "generations" / "openAG-tool")
    store = GenerationStore(root=gen_root)
    gen_id = store.record(entities, reason="arch_extract")

    model_dir = save_model_dir(
        str(resolved / ".architecture" / "model"), doc
    )

    return {
        "generation": gen_id,
        "model_dir": model_dir,
        "entities": len(entities),
        "relationships": len(doc.get("relationships") or []),
    }

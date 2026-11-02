"""``arch_grow`` — standalone scoped forward-GROW operator (openAG-native).

Mirrors ``openag.mcp.tools.grow_tool`` behind the OCA envelope. Grows the
declared ``root`` System's subtree to a structural promise-fixpoint, then
runs ``b_round`` with the provider + budget so the neural VoI scheduler is
active. With ``no_provider=True`` the run is pure-symbolic (``provider=None``
threaded through ``b_round``) and therefore deterministic — the default-off
flag keeps real runs provider-backed while tests stay LLM-free.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a directory
of ``*.v3.yaml`` fragments, loaded via the shared ``_openag_loader.load_doc``.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.tools._openag_loader import load_doc


@arch_tool
async def arch_grow(
    repo_path: str = "",
    *,
    root: str = "",
    budget: float = 100.0,
    max_iterations: int = 8,
    model: str | None = None,
    no_provider: bool = False,
) -> dict:
    """Run the standalone scoped forward-GROW operator.

    When ``no_provider`` is ``True`` the run is pure-symbolic and
    deterministic; otherwise a real provider is constructed via
    ``make_provider``.
    """
    if not isinstance(root, str) or not root.strip():
        raise ValueError("root must be a non-empty entity id")

    from openag.kernel.forward_grow import forward_grow
    from openag.kernel.gap_report import grounding_residue
    from openag.kernel.provider_factory import make_provider

    doc = load_doc(repo_path)

    provider = None if no_provider else make_provider(model=model)
    g, report = forward_grow(
        doc, root, provider=provider, budget=budget,
        max_iterations=max_iterations,
    )
    promises = {
        p["id"]: p
        for e in g.entities_flat()
        for p in (e.get("promises") or [])
        if p.get("id")
    }
    return {
        "root": root,
        "gaps": report.get("gaps", []),
        "residue": grounding_residue(report, promises),
        "a4_grounded": report.get("a4_grounded", []),
        "identity_gaps": report.get("identity_gaps", []),
    }


__all__ = ["arch_grow"]

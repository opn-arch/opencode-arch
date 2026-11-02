"""``arch_compliance`` — openAG compliance reports (openAG-native).

A thin OCA read-surface over openAG's ``openag.compliance`` package. Exposes
three reports behind the OCA envelope, selected by the ``report`` param:

* ``matrix``  — ``compliance.matrix.compliance_matrix()``: static standard-
  mandate -> valence coverage rows (model-independent).
* ``axes``    — ``compliance.axes_report.axis_exploration(doc)``: per-axis
  relationship-type exploration over the model doc.
* ``scoring`` — ``compliance.scoring.score_from_gaps(gaps)``: a bounded
  0-100 projection of the owed-promise gaps emitted over the real entity
  nodes (same gap-emission shape as ``arch_lessons``).

The openAG model lives at ``<repo_path>/.architecture/model/`` as a directory
of ``*.v3.yaml`` fragments, loaded via the shared ``_openag_loader``. Heavy
``openag.*`` imports are lazy so the module stays importable without the
dependency present. ``report`` is validated BEFORE the model is loaded, so a
bad report value on a repo with no model still yields INVALID_ARGUMENT.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc

# Real entity node kinds — only these are valid targets for owed-promise gap
# emission. Promise / evidence scaffolding nodes are excluded.
_REAL_ENTITY_KINDS = frozenset({
    "Component", "Capability", "Behavior", "Interface",
    "Constraint", "Actor", "Layer", "System",
})


@arch_tool
async def arch_compliance(repo_path: str = "", *, report: str = "matrix") -> dict:
    """Return one of openAG's compliance reports (matrix | axes | scoring)."""
    if report not in ("matrix", "axes", "scoring"):
        raise ValueError("report must be matrix|axes|scoring")

    if report == "matrix":
        from openag.compliance.matrix import compliance_matrix

        return {"matrix": compliance_matrix()}

    doc = load_doc(repo_path)

    if report == "axes":
        from openag.compliance.axes_report import axis_exploration

        return {"axes": axis_exploration(doc)}

    # scoring
    from openag.compliance.scoring import score_from_gaps
    from openag.kernel.gate import emit_gaps_graph

    g = build_graph(doc)
    gaps: list[dict] = []
    for eid in g.entity_nodes():
        if g.node(eid).get("kind") in _REAL_ENTITY_KINDS:
            gaps += emit_gaps_graph(g, eid)
    return {"score": score_from_gaps(gaps)}


__all__ = ["arch_compliance"]

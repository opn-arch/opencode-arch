"""arch_gate — native L2 development-gate MCP tool over openAG.

Behavioral replacement for the legacy AMS ``architect_gate`` tool. Builds the
openAG model graph (from inline ``model_yaml`` or the repo's merged model dir),
best-effort scans the repo source tree into a ground graph, and layers an L2
go/no-go decision over the owed-promise + structural-completeness gaps via
:func:`openag.kernel.gate.gate_report`. No legacy ``architecture_model``
dependency.

Accepts either an inline ``model_yaml`` string or (when empty) loads the
repo's merged openAG model doc from ``<repo_path>/.architecture/model/``.
"""

from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_gate(repo_path: str = "", model_yaml: str = "") -> dict:
    """Run the L2 development gate (owed+completeness gaps, scored)."""
    if model_yaml and model_yaml.strip():
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("empty model_yaml document")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc

        doc = load_doc(repo_path)

    from openag.graph.model_graph import ModelGraph

    g = ModelGraph.from_doc(doc)

    ground = None
    if repo_path and repo_path.strip():
        try:
            from opencode_arch.mcp.envelope import resolve_repo
            from openag.graph.ground import scan_ground_graph

            resolved = resolve_repo(repo_path)
            src_root = resolved / "src"
            if not src_root.is_dir():
                src_root = resolved
            ground = scan_ground_graph(src_root)
        except Exception:
            ground = None

    from openag.kernel.gate import gate_report

    return gate_report(g, ground=ground)

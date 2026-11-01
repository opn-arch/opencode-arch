"""arch_check — native model-representativeness MCP tool over openAG.

Behavioral replacement for the legacy AMS ``architect_check`` tool. Builds the
openAG model graph (from inline ``model_yaml`` or the repo's merged model dir),
scans the repo source tree into a ground graph, and scores how well the model's
component partition covers that ground graph via
:func:`openag.kernel.representativeness.check_representativeness`. No legacy
``architecture_model`` dependency.

Unlike ``arch_gate``, ``repo_path`` is REQUIRED — representativeness needs the
source tree to build a ground graph.
"""

from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_check(repo_path: str = "", model_yaml: str = "") -> dict:
    """Check model representativeness against the code ground graph."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolved = resolve_repo(repo_path)

    if model_yaml and model_yaml.strip():
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("empty model_yaml document")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc

        doc = load_doc(repo_path)

    from openag.graph.model_graph import ModelGraph

    g = ModelGraph.from_doc(doc)

    from openag.graph.ground import scan_ground_graph

    src_root = resolved / "src"
    if not src_root.is_dir():
        src_root = resolved
    ground = scan_ground_graph(src_root)

    from openag.kernel.representativeness import check_representativeness

    return check_representativeness(g, ground)

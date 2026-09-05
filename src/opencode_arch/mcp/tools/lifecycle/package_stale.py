"""MCP tool: report stale lifecycle nodes for a set of changed paths.

Wraps ``architecture_model.lifecycle.stale.build_graph`` +
``mark_stale`` to return the set of nodes that would become stale if
the given paths changed. Does NOT write ``.architecture/stale.yaml``
(that side effect is exclusive to Phase 1's ``stale_report`` helper).

The result records include ``node_id``, ``kind``, ``owned_paths``,
``inputs``, ``digest`` and ``reason``. Records are sorted by
``(kind, node_id)`` for determinism.
"""
from __future__ import annotations

from pathlib import Path

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result


@tool_result
async def package_stale_tool(
    repo_path: str,
    changed_paths: list[str],
) -> dict:
    """Return the set of nodes made stale by ``changed_paths``."""
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.stale import build_graph, mark_stale

    if not isinstance(changed_paths, list):
        raise ValueError("changed_paths must be a list of strings")
    for p in changed_paths:
        if not isinstance(p, str):
            raise ValueError("changed_paths must be a list of strings")

    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", "package.yaml not found")

    root_pkg = load_package(lifecycle_root)
    assert root_pkg.root is not None

    path_list = [Path(root_pkg.root) / p for p in changed_paths]

    graph = build_graph(root_pkg)
    ss = mark_stale(graph, path_list, package_root=root_pkg.root)

    id_to_node = {n.node_id: n for n in graph.nodes()}
    records = []
    for nid in ss.nodes:
        n = id_to_node.get(nid)
        if n is None:
            continue
        records.append({
            "node_id": n.node_id,
            "kind": n.kind,
            "owned_paths": list(n.owned_paths),
            "inputs": list(n.inputs),
            "digest": n.digest,
            "reason": ss.reasons.get(n.node_id, ""),
        })
    records.sort(key=lambda r: (r["kind"], r["node_id"]))

    return ok({"stale": records})

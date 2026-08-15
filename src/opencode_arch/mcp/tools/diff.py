"""architect_diff MCP tool — compare two architecture model versions."""

from __future__ import annotations

from pathlib import Path

import yaml


async def diff_models(
    repo_path: str,
    model_a_yaml: str = "",
    model_b_yaml: str = "",
) -> str:
    """Compare two architecture model versions and return a structured diff.

    If model_a_yaml is empty, reads the current .architecture-model.yaml.
    If model_b_yaml is empty, reads the last git-committed version.

    Returns a structured diff showing added/removed/changed components and relationships.
    """
    path = Path(repo_path)
    if not path.exists():
        return f"Error: Repository path does not exist: {repo_path}"

    try:
        # Load model A (current)
        if not model_a_yaml:
            model_a_path = path / ".architecture-model.yaml"
            if not model_a_path.exists():
                return "Error: No .architecture-model.yaml found. Run architect_extract first."
            model_a_yaml = model_a_path.read_text()

        # Load model B (comparison target — git HEAD or provided)
        if not model_b_yaml:
            import subprocess

            try:
                result = subprocess.run(
                    ["git", "show", "HEAD:.architecture-model.yaml"],
                    capture_output=True,
                    text=True,
                    cwd=str(path),
                )
                if result.returncode == 0:
                    model_b_yaml = result.stdout
                else:
                    return (
                        "Error: No previous model version in git. Provide model_b_yaml explicitly."
                    )
            except FileNotFoundError:
                return "Error: git not available."

        model_a = yaml.safe_load(model_a_yaml) or {}
        model_b = yaml.safe_load(model_b_yaml) or {}

        return _compute_diff(model_a, model_b)

    except Exception as e:
        return f"Error computing diff: {e}"


def _compute_diff(current: dict, previous: dict) -> str:
    """Compute structural diff between two model dicts."""
    lines: list[str] = ["# Architecture Model Diff\n"]

    # Extract components
    curr_comps = {c.get("id", c.get("name", "")): c for c in _get_components(current)}
    prev_comps = {c.get("id", c.get("name", "")): c for c in _get_components(previous)}

    added = set(curr_comps) - set(prev_comps)
    removed = set(prev_comps) - set(curr_comps)
    common = set(curr_comps) & set(prev_comps)

    if added:
        lines.append(f"## Added Components ({len(added)})")
        for cid in sorted(added):
            c = curr_comps[cid]
            lines.append(f"+ {cid}: {c.get('name', cid)} ({len(c.get('files', []))} files)")
        lines.append("")

    if removed:
        lines.append(f"## Removed Components ({len(removed)})")
        for cid in sorted(removed):
            c = prev_comps[cid]
            lines.append(f"- {cid}: {c.get('name', cid)}")
        lines.append("")

    # Changed components
    changed = []
    for cid in sorted(common):
        diffs = _diff_component(curr_comps[cid], prev_comps[cid])
        if diffs:
            changed.append((cid, diffs))

    if changed:
        lines.append(f"## Changed Components ({len(changed)})")
        for cid, diffs in changed:
            lines.append(f"~ {cid}:")
            for d in diffs:
                lines.append(f"  {d}")
        lines.append("")

    # Relationships diff
    curr_rels = set(_get_rel_keys(current))
    prev_rels = set(_get_rel_keys(previous))
    added_rels = curr_rels - prev_rels
    removed_rels = prev_rels - curr_rels

    if added_rels or removed_rels:
        lines.append("## Relationship Changes")
        for r in sorted(added_rels):
            lines.append(f"+ {r}")
        for r in sorted(removed_rels):
            lines.append(f"- {r}")
        lines.append("")

    if not added and not removed and not changed and not added_rels and not removed_rels:
        lines.append("No structural changes detected.")

    # Summary
    lines.append(f"\n## Summary")
    lines.append(
        f"Components: {len(prev_comps)} → {len(curr_comps)} (+{len(added)}, -{len(removed)}, ~{len(changed)})"
    )
    lines.append(
        f"Relationships: {len(prev_rels)} → {len(curr_rels)} (+{len(added_rels)}, -{len(removed_rels)})"
    )

    return "\n".join(lines)


def _get_components(model: dict) -> list[dict]:
    """Extract components from model dict (handles both flat and nested formats)."""
    entities = model.get("entities", model)
    comps = entities.get("components", [])
    if isinstance(comps, list):
        return comps
    return []


def _get_rel_keys(model: dict) -> list[str]:
    """Extract relationship keys as 'source->target(type)' strings."""
    rels = model.get("relationships", [])
    keys = []
    for r in rels:
        src = r.get("source", "?")
        tgt = r.get("target", "?")
        rtype = r.get("type", "?")
        keys.append(f"{src}->{tgt}({rtype})")
    return keys


def _diff_component(curr: dict, prev: dict) -> list[str]:
    """Find differences between two versions of the same component."""
    diffs = []
    # Check files
    curr_files = set(curr.get("files", []))
    prev_files = set(prev.get("files", []))
    if curr_files != prev_files:
        added = curr_files - prev_files
        removed = prev_files - curr_files
        if added:
            diffs.append(f"files +{len(added)}: {', '.join(sorted(added)[:5])}")
        if removed:
            diffs.append(f"files -{len(removed)}: {', '.join(sorted(removed)[:5])}")

    # Check signatures
    curr_sigs = set(
        s if isinstance(s, str) else s.get("name", "") for s in curr.get("signatures", [])
    )
    prev_sigs = set(
        s if isinstance(s, str) else s.get("name", "") for s in prev.get("signatures", [])
    )
    if curr_sigs != prev_sigs:
        added = curr_sigs - prev_sigs
        removed = prev_sigs - curr_sigs
        if added:
            diffs.append(f"signatures +{len(added)}")
        if removed:
            diffs.append(f"signatures -{len(removed)}")

    # Check name/description changes
    if curr.get("name") != prev.get("name"):
        diffs.append(f"name: '{prev.get('name')}' → '{curr.get('name')}'")
    if curr.get("description") != prev.get("description"):
        diffs.append("description changed")

    return diffs

"""
LLM Context Formatter: Produce compact model representations for LLM prompt injection.

Implements the LLM Integration Protocol:
- LOAD: Serialize model (or slice) into compact text for system prompt
- QUERY: Answer structural questions from model data
- IMPACT: Determine what entities are affected by a proposed change

The key constraint is TOKEN BUDGET — we need maximum information density.
Format: structured YAML-like text, ~25:1 compression vs full artifact markdown.
"""

from __future__ import annotations

from typing import Optional

from architecture_model.core.types import (
    ArchitectureModel,
    Actor,
    Behavior,
    Capability,
    Component,
    Constraint,
    Interface,
    Layer,
    Relationship,
    Status,
)
from architecture_model.core.slicer import slice_by_fblock, slice_for_artifact


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_model_context(
    model: ArchitectureModel,
    max_tokens: int = 4000,
    detail_level: str = "standard",
) -> str:
    """
    Format the full model as compact LLM context.

    Args:
        model: Architecture model to format.
        max_tokens: Approximate token budget (1 token ~ 4 chars).
        detail_level: "minimal", "standard", or "full".

    Returns:
        Formatted text suitable for LLM system prompt injection.
    """
    char_budget = max_tokens * 4

    # Progressive summarization: add sections by priority, stop before exceeding budget
    priority_1: list[str] = []
    priority_2: list[str] = []
    priority_3: list[str] = []
    priority_4: list[str] = []

    # Priority 1: Header + component names (always included)
    priority_1.append(_format_header(model))
    if model.entities.components:
        lines = [f"\n## Components ({len(model.entities.components)})"]
        for comp in model.entities.components:
            file_count = len(comp.files) if comp.files else 0
            lines.append(f"  {comp.id}: {comp.name} ({file_count} files)")
            # Include interface contracts at full detail
            if detail_level == "full" and hasattr(comp, "interfaces") and comp.interfaces:
                for iface in comp.interfaces:
                    sym_str = f" [{', '.join(iface.symbols[:5])}]" if iface.symbols else ""
                    lines.append(f"    {iface.kind}: {iface.target_component}{sym_str}")
        priority_1.append("\n".join(lines))

    # Priority 2: Key relationships (grouped by type, top connections)
    if model.relationships:
        priority_2.append(_format_relationships_compact(model))

    # Priority 3: Capabilities + behaviors (compact)
    if detail_level in ("standard", "full"):
        priority_3.append(_format_capabilities(model))
        priority_3.append(_format_actors(model))
        if detail_level == "full":
            priority_3.append(_format_behaviors(model))
        else:
            priority_3.append(_format_behaviors_compact(model))

    # Priority 4: Full detail (interfaces, layers, constraints)
    if detail_level == "full":
        priority_4.append(_format_interfaces(model))
        priority_4.append(_format_layers(model))
        priority_4.append(_format_constraints(model))
    elif detail_level == "standard":
        priority_4.append(_format_interfaces_compact(model))
        priority_4.append(_format_layers_compact(model))

    # Progressively add sections until budget is reached
    result_parts: list[str] = []
    used = 0

    for section_group in [priority_1, priority_2, priority_3, priority_4]:
        for section in section_group:
            if not section:
                continue
            section_len = len(section)
            if used + section_len <= char_budget:
                result_parts.append(section)
                used += section_len
            else:
                # Don't truncate mid-section; stop here
                break
        else:
            continue
        break

    return "\n".join(result_parts)


def format_fblock_context(
    model: ArchitectureModel,
    f_block: str,
    max_tokens: int = 2000,
    project_root: "Path | None" = None,
) -> str:
    """
    Format context for a single F-block (for artifact section regeneration).

    Produces: capability description, related UCs, components, interfaces.
    If *project_root* is given, sub-models are auto-loaded for richer detail,
    and per-block manifests are consumed for function-level context.
    """
    sliced = slice_by_fblock(model, f_block, project_root=project_root)
    base_context = format_model_context(sliced, max_tokens=max_tokens, detail_level="full")

    # Consume per-block manifest if available (reduces compression ratio)
    if project_root:
        block_manifest = _load_block_manifest(project_root, f_block)
        if block_manifest:
            char_budget = max_tokens * 4
            remaining = char_budget - len(base_context)
            if remaining > 200:
                manifest_section = _format_block_manifest(block_manifest, remaining)
                if manifest_section:
                    base_context += "\n" + manifest_section

    return base_context


def format_artifact_context(
    model: ArchitectureModel,
    artifact_name: str,
    max_tokens: int = 3000,
) -> str:
    """
    Format context appropriate for regenerating a specific artifact.

    Uses artifact-specific slicing then formats at appropriate detail level.
    """
    sliced = slice_for_artifact(model, artifact_name)

    detail_map = {
        "functional-architecture": "full",
        "logical-architecture": "full",
        "use-cases": "full",
        "icd": "full",
        "requirements-analysis": "standard",
        "readme": "minimal",
    }
    detail = detail_map.get(artifact_name, "standard")

    return format_model_context(sliced, max_tokens=max_tokens, detail_level=detail)


def query_model(model: ArchitectureModel, question: str) -> str:
    """
    Answer a structural question from model data.

    Supports questions like:
    - "What realizes F3?" → list behaviors with tag F3
    - "What does UC-14 depend on?" → follow depends-on relationships
    - "What interfaces does F4 expose?" → filter interfaces by provider
    """
    q = question.lower().strip()

    # Pattern: "what realizes <X>?"
    if "realizes" in q:
        import re

        m = re.search(r"(f\d+|cap-\w+)", q, re.IGNORECASE)
        if m:
            target = m.group(1).upper()
            realizers = [
                r.from_id
                for r in model.relationships
                if r.type.value == "realizes" and target in r.to_id.upper()
            ]
            if realizers:
                lines = [f"Entities realizing {target}:"]
                for rid in realizers:
                    beh = next((b for b in model.entities.behaviors if b.id == rid), None)
                    if beh:
                        lines.append(f"  - {beh.id}: {beh.name} [{beh.status.value}]")
                    else:
                        lines.append(f"  - {rid}")
                return "\n".join(lines)
            return f"No entities realize {target}"

    # Pattern: "what does <X> depend on?"
    if "depend" in q:
        import re

        m = re.search(r"(uc-\d+|[a-z][\w-]+)", q, re.IGNORECASE)
        if m:
            source = m.group(1)
            deps = [
                r.to_id
                for r in model.relationships
                if r.from_id.lower() == source.lower() and r.type.value == "depends-on"
            ]
            if deps:
                return f"{source} depends on: {', '.join(deps)}"
            return f"{source} has no recorded dependencies"

    # Pattern: count/summary
    if "how many" in q or "count" in q:
        return (
            f"Model contains: {model.entity_count} entities, {model.relationship_count} relationships\n"
            f"  Actors: {len(model.entities.actors)}\n"
            f"  Capabilities: {len(model.entities.capabilities)}\n"
            f"  Behaviors: {len(model.entities.behaviors)}\n"
            f"  Interfaces: {len(model.entities.interfaces)}\n"
            f"  Constraints: {len(model.entities.constraints)}\n"
            f"  Layers: {len(model.entities.layers)}\n"
            f"  Components: {len(model.entities.components)}"
        )

    return f"Unable to answer: {question}\nTry: 'what realizes F3?', 'what does UC-14 depend on?', 'how many entities?'"


def impact_analysis(model: ArchitectureModel, entity_id: str, depth: int = 2) -> str:
    """
    Determine what entities are affected if a given entity changes.

    Traces relationships transitively up to `depth` levels.
    """
    affected: dict[str, int] = {}  # entity_id -> distance
    frontier = {entity_id}
    current_depth = 0

    while frontier and current_depth < depth:
        next_frontier: set[str] = set()
        for eid in frontier:
            for rel in model.relationships:
                # Forward direction: what depends on this?
                if rel.to_id == eid and rel.from_id not in affected and rel.from_id != entity_id:
                    affected[rel.from_id] = current_depth + 1
                    next_frontier.add(rel.from_id)
                # Reverse for 'realizes': if this behavior changes, its capability is affected
                if rel.from_id == eid and rel.to_id not in affected and rel.to_id != entity_id:
                    if rel.type.value in ("realizes", "contains", "exposes"):
                        affected[rel.to_id] = current_depth + 1
                        next_frontier.add(rel.to_id)
        frontier = next_frontier
        current_depth += 1

    if not affected:
        return f"No entities are directly affected by changes to {entity_id}"

    lines = [f"Impact analysis for {entity_id} (depth={depth}):"]
    for eid, dist in sorted(affected.items(), key=lambda x: x[1]):
        # Try to find name
        name = _find_entity_name(model, eid)
        lines.append(f"  {'  ' * dist}[depth {dist}] {eid}: {name}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _format_header(model: ArchitectureModel) -> str:
    return (
        f"# Architecture Model: {model.meta.project}\n"
        f"System: {model.meta.system} | Schema: {model.meta.schema_version}\n"
        f"Entities: {model.entity_count} | Relationships: {model.relationship_count}\n"
        f"Sources: {', '.join(model.meta.source_artifacts)}"
    )


def _format_capabilities(model: ArchitectureModel) -> str:
    if not model.entities.capabilities:
        return ""
    lines = ["\n## Capabilities (F-blocks)"]
    for cap in model.entities.capabilities:
        lines.append(f"  {cap.id} ({cap.f_block}): {cap.name} [{cap.status.value}]")
    return "\n".join(lines)


def _format_actors(model: ArchitectureModel) -> str:
    if not model.entities.actors:
        return ""
    lines = ["\n## Actors"]
    for actor in model.entities.actors:
        goals = "; ".join(actor.goals[:3]) if actor.goals else ""
        lines.append(f"  {actor.id}: {actor.name} ({actor.type.value}) — {goals}")
    return "\n".join(lines)


def _format_behaviors(model: ArchitectureModel) -> str:
    if not model.entities.behaviors:
        return ""
    lines = ["\n## Behaviors (Use Cases)"]
    for beh in model.entities.behaviors:
        post = beh.postconditions[0][:60] if beh.postconditions else ""
        lines.append(
            f"  {beh.id}: {beh.name} [{beh.status.value}] "
            f"actor={beh.actor} freq={beh.frequency} pri={beh.priority.value}"
        )
        if post:
            lines.append(f"    acceptance: {post}")
    return "\n".join(lines)


def _format_behaviors_compact(model: ArchitectureModel) -> str:
    if not model.entities.behaviors:
        return ""
    lines = ["\n## Behaviors (30 UCs)"]
    for beh in model.entities.behaviors:
        tag = beh.tags[0] if beh.tags else "?"
        lines.append(f"  {beh.id}: {beh.name} [{beh.status.value}] {tag} pri={beh.priority.value}")
    return "\n".join(lines)


def _format_interfaces(model: ArchitectureModel) -> str:
    if not model.entities.interfaces:
        return ""
    lines = ["\n## Interfaces"]
    for iface in model.entities.interfaces:
        lines.append(
            f"  {iface.id}: {iface.type.value} | {iface.provider} -> {iface.consumer} "
            f"via {iface.protocol} [{iface.status.value}]"
        )
    return "\n".join(lines)


def _format_interfaces_compact(model: ArchitectureModel) -> str:
    if not model.entities.interfaces:
        return ""
    lines = [f"\n## Interfaces ({len(model.entities.interfaces)})"]
    for iface in model.entities.interfaces:
        lines.append(f"  {iface.id}: {iface.provider} -> {iface.consumer} ({iface.type.value})")
    return "\n".join(lines)


def _format_layers(model: ArchitectureModel) -> str:
    if not model.entities.layers:
        return ""
    lines = ["\n## Layers"]
    for layer in model.entities.layers:
        comp_count = sum(1 for c in model.entities.components if c.layer == layer.id)
        lines.append(f"  {layer.id}: {layer.name} (order={layer.order}, {comp_count} components)")
        if layer.directories:
            lines.append(f"    dirs: {', '.join(layer.directories)}")
    return "\n".join(lines)


def _format_layers_compact(model: ArchitectureModel) -> str:
    if not model.entities.layers:
        return ""
    lines = [f"\n## Layers ({len(model.entities.layers)})"]
    for layer in model.entities.layers:
        lines.append(f"  {layer.id}: {layer.name}")
    return "\n".join(lines)


def _format_components(model: ArchitectureModel) -> str:
    if not model.entities.components:
        return ""
    lines = [f"\n## Components ({len(model.entities.components)})"]
    for comp in model.entities.components:
        files = ", ".join(comp.files[:2]) if comp.files else ""
        lines.append(f"  {comp.id}: {comp.name} (layer={comp.layer}, {comp.f_block}) [{files}]")
    return "\n".join(lines)


def _format_constraints(model: ArchitectureModel) -> str:
    if not model.entities.constraints:
        return ""
    lines = [f"\n## Constraints ({len(model.entities.constraints)})"]
    for con in model.entities.constraints:
        lines.append(f"  {con.id}: {con.name} ({con.type.value}) threshold={con.threshold}")
    return "\n".join(lines)


def _format_relationships_compact(model: ArchitectureModel) -> str:
    if not model.relationships:
        return ""
    # Group by type
    by_type: dict[str, list[Relationship]] = {}
    for rel in model.relationships:
        by_type.setdefault(rel.type.value, []).append(rel)

    lines = [f"\n## Relationships ({len(model.relationships)})"]
    for rtype, rels in by_type.items():
        lines.append(f"  {rtype} ({len(rels)}):")
        for rel in rels[:10]:  # Limit per type
            lines.append(f"    {rel.from_id} -> {rel.to_id}")
        if len(rels) > 10:
            lines.append(f"    ... +{len(rels) - 10} more")
    return "\n".join(lines)


def _find_entity_name(model: ArchitectureModel, entity_id: str) -> str:
    """Find the human-readable name for an entity ID."""
    for lst in [
        model.entities.actors,
        model.entities.capabilities,
        model.entities.behaviors,
        model.entities.interfaces,
        model.entities.constraints,
        model.entities.layers,
        model.entities.components,
    ]:
        for e in lst:
            if e.id == entity_id:
                return e.name
    return entity_id


# ---------------------------------------------------------------------------
# Block manifest consumption
# ---------------------------------------------------------------------------


def _load_block_manifest(project_root: "Path", f_block: str) -> dict | None:
    """Load per-block manifest.json if it exists."""
    import json
    from pathlib import Path

    # Try common locations
    for subdir in (f_block, f_block.lower(), f"block_{f_block}"):
        manifest_path = Path(project_root) / ".architecture-models" / subdir / "manifest.json"
        if manifest_path.exists():
            try:
                return json.loads(manifest_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _format_block_manifest(manifest: dict, char_budget: int) -> str:
    """Format block manifest data as compact context.

    Includes: module names, key function signatures, imports.
    This fills the semantic gap that causes cross_dep failures.
    """
    lines = ["\n## Block Manifest (function-level detail)"]

    modules = manifest.get("modules", [])
    for mod in modules:
        file_path = mod.get("file", mod.get("path", "unknown"))
        lines.append(f"  {file_path}:")

        # Functions with signatures (critical for cross_dep)
        functions = mod.get("functions", [])
        for fn in functions[:10]:
            name = fn.get("name", "") if isinstance(fn, dict) else fn
            sig = fn.get("signature", "") if isinstance(fn, dict) else ""
            if name.startswith("_"):
                continue
            if sig:
                lines.append(f"    {name}{sig}")
            else:
                lines.append(f"    {name}()")

        # Classes
        classes = mod.get("classes", [])
        for cls in classes[:5]:
            name = cls.get("name", "") if isinstance(cls, dict) else cls
            if not name.startswith("_"):
                lines.append(f"    class {name}")

        # Check budget
        current = "\n".join(lines)
        if len(current) >= char_budget * 0.9:
            lines.append("    ... (truncated)")
            break

    result = "\n".join(lines)
    return result[:char_budget]

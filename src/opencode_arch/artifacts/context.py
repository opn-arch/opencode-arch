"""Context assembler for artifact generation.

Given an artifact template + architecture model + optional manifest,
assembles the formatted context string included in the LLM prompt.

Extracts relevant model/manifest data for each template section and
formats it concisely for LLM consumption.
"""

from __future__ import annotations

from opencode_arch.artifacts.diagrams import (
    generate_component_diagram,
    generate_dependency_diagram,
    generate_sequence_diagram,
)
from opencode_arch.artifacts.templates import ArtifactTemplate
from architecture_model.core.types import ArchitectureModel


def assemble_artifact_context(
    template: ArtifactTemplate,
    model: ArchitectureModel,
    manifest: dict | None = None,
    max_tokens: int = 4000,
) -> str:
    """Assemble formatted context for artifact generation.

    Returns a structured prompt string containing:
    1. System prompt from template
    2. For each section: heading + extracted data + instructions

    Token budget is approximate (1 token ~ 4 chars). If total exceeds budget,
    truncate section data (not instructions).
    """
    max_chars = max_tokens * 4

    # Build header
    header = f"SYSTEM: {template.system_prompt}\n"

    # Build sections
    sections: list[str] = []
    for section in template.sections:
        data = _extract_section_data(section.source, model, manifest)
        section_text = (
            f"\n{section.heading}\n"
            f"DATA:\n{data}\n"
            f"INSTRUCTIONS: {section.instructions}\n"
        )
        sections.append(section_text)

    # Assemble full output
    full_output = header + "".join(sections)

    # Truncate if over budget
    if len(full_output) <= max_chars:
        return full_output

    # Truncate strategy: rebuild with trimmed section data
    # Keep header + instructions intact, trim data
    remaining = max_chars - len(header)
    truncated_sections: list[str] = []

    for section in template.sections:
        # Fixed overhead per section (heading + DATA: + INSTRUCTIONS:)
        frame = (
            f"\n{section.heading}\n"
            f"DATA:\n"
        )
        tail = f"\nINSTRUCTIONS: {section.instructions}\n"
        frame_cost = len(frame) + len(tail)

        if remaining <= frame_cost:
            # Not enough room for even the frame — skip section
            break

        data = _extract_section_data(section.source, model, manifest)
        available_for_data = remaining - frame_cost
        if len(data) > available_for_data:
            data = data[:available_for_data].rstrip() + "\n[truncated]"

        section_text = frame + data + tail
        truncated_sections.append(section_text)
        remaining -= len(section_text)

    return header + "".join(truncated_sections)


def _extract_section_data(
    source: str, model: ArchitectureModel, manifest: dict | None
) -> str:
    """Route to appropriate extractor based on source string."""
    extractors = {
        "meta": lambda: _format_meta(model),
        "components": lambda: _format_components(model),
        "interfaces": lambda: _format_interfaces(model),
        "capabilities": lambda: _format_capabilities(model),
        "behaviors": lambda: _format_behaviors(model),
        "constraints": lambda: _format_constraints(model),
        "layers": lambda: _format_layers(model),
        "relationships": lambda: _format_relationships(model),
        "manifest.tests": lambda: _format_manifest_tests(manifest),
        "manifest.metrics": lambda: _format_manifest_metrics(manifest),
    }

    extractor = extractors.get(source)
    if extractor is None:
        return "No data available for this section."
    return extractor()


def _format_meta(model: ArchitectureModel) -> str:
    """Format project metadata."""
    lines = [
        f"Project: {model.meta.project}",
        f"System: {model.meta.system}",
        f"Schema: {model.meta.schema_version}",
    ]
    if model.meta.generated_at:
        lines.append(f"Generated: {model.meta.generated_at}")
    return "\n".join(lines)


def _format_components(model: ArchitectureModel) -> str:
    """Format components list with component diagram."""
    components = model.entities.components
    if not components:
        return "No data available for this section."

    lines = []
    for c in components:
        line = f"- {c.id}: {c.name} [{c.kind.value}] layer={c.layer} status={c.status.value}"
        if c.files:
            line += f"\n  files: {', '.join(c.files)}"
        if c.responsibilities:
            line += f"\n  responsibilities: {', '.join(c.responsibilities)}"
        lines.append(line)

    # Append component diagram if there are enough components
    if len(components) >= 2:
        diagram = generate_component_diagram(model)
        lines.append(f"\nDIAGRAM:\n```plantuml\n{diagram}\n```")

    return "\n".join(lines)


def _format_interfaces(model: ArchitectureModel) -> str:
    """Format interfaces list."""
    interfaces = model.entities.interfaces
    if not interfaces:
        return "No data available for this section."

    lines = []
    for i in interfaces:
        line = f"- {i.id}: {i.name} [{i.type.value}] protocol={i.protocol}"
        line += f"\n  provider={i.provider} consumer={i.consumer}"
        line += f"\n  endpoints: {len(i.endpoints)}"
        lines.append(line)
    return "\n".join(lines)


def _format_capabilities(model: ArchitectureModel) -> str:
    """Format capabilities list."""
    capabilities = model.entities.capabilities
    if not capabilities:
        return "No data available for this section."

    lines = []
    for cap in capabilities:
        line = f"- {cap.id}: {cap.name} [priority={cap.priority.value}] f_block={cap.f_block}"
        lines.append(line)
    return "\n".join(lines)


def _format_behaviors(model: ArchitectureModel) -> str:
    """Format behaviors list with sequence diagrams."""
    behaviors = model.entities.behaviors
    if not behaviors:
        return "No data available for this section."

    lines = []
    for b in behaviors:
        line = f"- {b.id}: {b.name} trigger={b.trigger} pattern={b.pattern.value}"
        if b.steps:
            line += f"\n  steps: {', '.join(b.steps)}"
        lines.append(line)

    # Append sequence diagrams for behaviors with steps
    diagrams_added = 0
    for b in behaviors:
        if b.steps and diagrams_added < 3:  # cap at 3 to control token usage
            diagram = generate_sequence_diagram(b, model)
            if diagram:
                lines.append(f"\nSEQUENCE ({b.name}):\n```plantuml\n{diagram}\n```")
                diagrams_added += 1

    return "\n".join(lines)


def _format_constraints(model: ArchitectureModel) -> str:
    """Format constraints list."""
    constraints = model.entities.constraints
    if not constraints:
        return "No data available for this section."

    lines = []
    for c in constraints:
        line = f"- {c.id}: {c.name} [{c.type.value}] metric={c.metric} threshold={c.threshold}"
        lines.append(line)
    return "\n".join(lines)


def _format_layers(model: ArchitectureModel) -> str:
    """Format layers list."""
    layers = model.entities.layers
    if not layers:
        return "No data available for this section."

    lines = []
    for layer in layers:
        tech = ", ".join(layer.technology) if layer.technology else "none"
        line = f"- {layer.id}: {layer.name} [order={layer.order}] tech={tech}"
        lines.append(line)
    return "\n".join(lines)


def _format_relationships(model: ArchitectureModel) -> str:
    """Format relationship list with dependency diagram."""
    relationships = model.relationships
    if not relationships:
        return "No data available for this section."

    lines = []
    for r in relationships:
        line = f"- {r.from_id} --{r.type.value}--> {r.to_id}"
        lines.append(line)

    # Append dependency diagram if there are relationships
    diagram = generate_dependency_diagram(model)
    if "@startuml" in diagram and "rectangle" in diagram:
        lines.append(f"\nDIAGRAM:\n```plantuml\n{diagram}\n```")

    return "\n".join(lines)


def _format_manifest_tests(manifest: dict | None) -> str:
    """Format test data from manifest."""
    if manifest is None or "test_files" not in manifest:
        return "No data available for this section."

    test_files = manifest["test_files"]
    lines = [f"Test files: {len(test_files)}"]
    for f in test_files:
        lines.append(f"- {f}")
    return "\n".join(lines)


def _format_manifest_metrics(manifest: dict | None) -> str:
    """Format metrics from manifest."""
    if manifest is None or "metrics" not in manifest:
        return "No data available for this section."

    metrics = manifest["metrics"]
    lines = []
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-Capability Detail Context
# ---------------------------------------------------------------------------


def format_capability_detail_context(
    cap_id: str,
    model: ArchitectureModel,
    manifest: dict | None = None,
) -> str:
    """Assemble rich context for generating a per-capability API detail doc.

    Extracts the full neighborhood of a single capability:
    - The capability entity itself
    - Realizing component(s) and their files/signatures/constants
    - Related behaviors (steps, triggers, pre/postconditions)
    - Exposed interfaces (endpoints, protocol)
    - Applicable constraints
    - Upstream/downstream relationships

    Returns a structured text block suitable for LLM prompt injection.
    """
    from architecture_model.core.types import RelationType

    # Find the capability
    cap = None
    for c in model.entities.capabilities:
        if c.id == cap_id:
            cap = c
            break
    if cap is None:
        return f"Capability {cap_id} not found in model."

    lines: list[str] = []

    # --- Capability identity ---
    lines.append("## Capability")
    lines.append(f"ID: {cap.id}")
    lines.append(f"Name: {cap.name}")
    lines.append(f"Status: {cap.status.value}")
    lines.append(f"F-Block: {cap.f_block}")
    lines.append(f"Priority: {cap.priority.value}")
    if cap.requirements:
        lines.append(f"Requirements: {'; '.join(cap.requirements)}")

    # --- Realizing components ---
    realizing_comp_ids: list[str] = []
    for rel in model.relationships:
        if rel.type == RelationType.REALIZES and rel.to_id == cap_id:
            realizing_comp_ids.append(rel.from_id)

    realizing_comps = [
        comp for comp in model.entities.components
        if comp.id in realizing_comp_ids
    ]

    if realizing_comps:
        lines.append("\n## Realizing Components")
        for comp in realizing_comps:
            lines.append(f"\n### {comp.id}: {comp.name}")
            lines.append(f"Kind: {comp.kind.value}")
            lines.append(f"Layer: {comp.layer}")
            lines.append(f"Status: {comp.status.value}")
            if comp.files:
                lines.append(f"Files: {', '.join(comp.files)}")
            if comp.responsibilities:
                lines.append(f"Responsibilities: {'; '.join(comp.responsibilities)}")
            if comp.technology:
                lines.append(f"Technology: {comp.technology}")

            # Signatures (enriched model v1.4)
            if comp.signatures:
                lines.append(f"\nFunction Signatures ({len(comp.signatures)}):")
                for sig in comp.signatures:
                    sig_line = f"  - {sig.name}({', '.join(sig.params)}) -> {sig.returns}"
                    if sig.body_hint:
                        sig_line += f"  # {sig.body_hint}"
                    lines.append(sig_line)

            # Constants (enriched model v1.4)
            if comp.constants:
                lines.append(f"\nConstants ({len(comp.constants)}):")
                for const in comp.constants:
                    lines.append(f"  - {const.name} = {const.value}")

            # Test contracts (enriched model v1.4)
            if comp.test_contracts:
                lines.append(f"\nTest Contracts ({len(comp.test_contracts)}):")
                for tc in comp.test_contracts[:20]:  # cap for token budget
                    lines.append(f"  - [{tc.test_file}::{tc.test_method}] {tc.assertion}")

    # --- Related behaviors ---
    # Find behaviors linked to realizing components via 'traces-to' or matching actor
    behavior_ids: set[str] = set()
    for rel in model.relationships:
        if rel.type == RelationType.TRACES_TO and rel.from_id in realizing_comp_ids:
            behavior_ids.add(rel.to_id)
        elif rel.type == RelationType.TRACES_TO and rel.to_id in realizing_comp_ids:
            behavior_ids.add(rel.from_id)

    behaviors = [b for b in model.entities.behaviors if b.id in behavior_ids]
    if behaviors:
        lines.append("\n## Behavioral Views")
        for beh in behaviors:
            lines.append(f"\n### {beh.id}: {beh.name}")
            lines.append(f"Trigger: {beh.trigger}")
            lines.append(f"Pattern: {beh.pattern.value}")
            if beh.actor:
                lines.append(f"Actor: {beh.actor}")
            if beh.steps:
                lines.append("Steps:")
                for i, step in enumerate(beh.steps, 1):
                    lines.append(f"  {i}. {step}")

    # --- Exposed interfaces ---
    interface_ids: set[str] = set()
    for rel in model.relationships:
        if rel.type == RelationType.EXPOSES and rel.from_id in realizing_comp_ids:
            interface_ids.add(rel.to_id)

    interfaces = [iface for iface in model.entities.interfaces if iface.id in interface_ids]
    if interfaces:
        lines.append("\n## Exposed Interfaces")
        for iface in interfaces:
            lines.append(f"\n### {iface.id}: {iface.name}")
            lines.append(f"Protocol: {iface.protocol}")
            lines.append(f"Provider: {iface.provider}")
            lines.append(f"Consumer: {iface.consumer}")
            if iface.endpoints:
                lines.append("Endpoints:")
                for ep in iface.endpoints:
                    lines.append(f"  - {ep.get('method', '?')}: {ep.get('path', '?')}")

    # --- Constraints ---
    constraint_ids: set[str] = set()
    for rel in model.relationships:
        if rel.type == RelationType.CONSTRAINED_BY:
            if rel.from_id in realizing_comp_ids or rel.to_id in realizing_comp_ids:
                constraint_ids.add(rel.from_id)
                constraint_ids.add(rel.to_id)

    constraints = [c for c in model.entities.constraints if c.id in constraint_ids]
    if constraints:
        lines.append("\n## Constraints")
        for con in constraints:
            lines.append(f"- {con.id}: {con.name} [{con.type.value}]")
            lines.append(f"  metric={con.metric}, threshold={con.threshold}")

    # --- Dependency relationships ---
    dep_lines: list[str] = []
    all_related_ids = set(realizing_comp_ids) | interface_ids | behavior_ids | constraint_ids
    for rel in model.relationships:
        if rel.from_id in all_related_ids or rel.to_id in all_related_ids:
            dep_lines.append(f"  {rel.from_id} --{rel.type.value}--> {rel.to_id}")

    if dep_lines:
        lines.append("\n## Relationship Graph")
        lines.extend(dep_lines)

    # --- Manifest data for realizing files ---
    if manifest and realizing_comps:
        modules = manifest.get("modules", [])
        comp_files = set()
        for comp in realizing_comps:
            comp_files.update(comp.files)

        relevant_modules = [m for m in modules if m.get("file", "") in comp_files]
        if relevant_modules:
            lines.append("\n## Manifest Detail (AST-scanned)")
            for mod in relevant_modules:
                lines.append(f"\n### {mod.get('file', '?')}")
                if mod.get("docstring"):
                    lines.append(f"  Docstring: {mod['docstring'][:200]}")
                if mod.get("functions"):
                    lines.append(f"  Functions: {', '.join(mod['functions'][:15])}")
                if mod.get("classes"):
                    for cls in mod["classes"][:5]:
                        cls_name = cls.get("name", "?")
                        methods = cls.get("methods", [])
                        lines.append(f"  Class {cls_name}: {', '.join(methods[:10])}")

    return "\n".join(lines)

"""architect_ingest tool — accept a SourceGraph JSON for any language.

Allows agents or external tools to submit dependency/export data for
non-Python repos. Stores the graph and runs grouping + interface extraction.
"""
from __future__ import annotations

import json
from pathlib import Path


async def ingest_source_graph(
    repo_path: str,
    source_graph_json: str,
) -> dict:
    """Ingest a SourceGraph JSON and generate architecture components.

    Args:
        repo_path: Absolute path to the repository.
        source_graph_json: JSON string with SourceGraph data.

    Returns:
        Dict with components, interfaces, and group info.
    """
    try:
        from architecture_model.manifest.protocol import SourceGraph
        from architecture_model.manifest.grouping import group_source_graph, auto_fblocks
        from architecture_model.core.types import (
            ArchitectureModel, Component, Entities, ModelMeta,
        )
        from architecture_model.orchestration.auto_enrich import extract_component_interfaces
        from architecture_model.core.parser import save_model

        project_root = Path(repo_path)

        # Parse the source graph
        data = json.loads(source_graph_json)
        graph = SourceGraph.from_json(data)
        graph.root = repo_path

        # Group into components
        groups = group_source_graph(graph)
        if not groups:
            return {"error": "No non-trivial source units found", "units": len(graph.units)}

        # Create components from groups
        components: list[Component] = []
        for idx, group in enumerate(groups, 1):
            components.append(Component(
                id=f"COMP-{idx}",
                name=group.name,
                status="ACTIVE",
                files=group.modules,
            ))

        # Build model with relationships from edges
        from architecture_model.core.types import Relationship, RelationType
        
        # Map files to component IDs
        file_to_comp: dict[str, str] = {}
        for comp in components:
            for f in (comp.files or []):
                file_to_comp[f] = comp.id
        
        # Convert edges to relationships between components
        relationships: list[Relationship] = []
        seen_rels: set[tuple[str, str]] = set()
        for edge in graph.edges:
            source_comp = file_to_comp.get(edge.source)
            target_comp = file_to_comp.get(edge.target)
            if source_comp and target_comp and source_comp != target_comp:
                pair = (source_comp, target_comp)
                if pair not in seen_rels:
                    seen_rels.add(pair)
                    relationships.append(Relationship(
                        type=RelationType.DEPENDS_ON,
                        from_id=source_comp,
                        to_id=target_comp,
                        description=f"{edge.source} -> {edge.target}",
                    ))

        model = ArchitectureModel(
            meta=ModelMeta(project=project_root.name, schema_version="1.3"),
            entities=Entities(components=components),
            relationships=relationships,
        )

        # Extract interface contracts
        n_ifaces = extract_component_interfaces(model, graph)

        # Enrich components from SourceGraph (signatures, symbols, contracts, patterns)
        from architecture_model.orchestration.auto_enrich import enrich_from_source_graph
        enrich_from_source_graph(model, graph)

        # Generate F-block config
        fblock_config = auto_fblocks(groups, threshold=3)

        # Save the model
        model_path = project_root / ".architecture-model-extracted.yaml"
        save_model(model, model_path)

        # Also save the source graph for later use
        graph_path = project_root / ".architecture-models" / "source-graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(json.dumps(graph.to_json(), indent=2))

        return {
            "stored": True,
            "model_path": str(model_path),
            "graph_path": str(graph_path),
            "components": len(components),
            "interfaces": n_ifaces,
            "fblocks": len(fblock_config),
            "units": len(graph.units),
            "edges": len(graph.edges),
            "language": graph.language,
            "groups": [
                {"name": g.name, "files": g.modules, "file_count": len(g.modules)}
                for g in groups
            ],
        }

    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": str(e)}

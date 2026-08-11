"""architect_docs MCP tool — generate SE documentation from architecture model."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
async def generate_docs(repo_path: str, formats: str = "all", manifest: Any = None) -> dict[str, Any]:
    """Generate standard SE documentation from an architecture model.

    Produces component specs, ICDs, dependency matrix, health report,
    and index from .architecture-model.yaml.

    Args:
        repo_path: Absolute path to the repository.
        formats: Comma-separated list of doc types to generate.
            Options: all, component_spec, icd, dependency_matrix, health, drift, index.
            Default: "all".

    Returns:
        Dict with generated file paths and any errors.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    model_file = path / ".architecture-model.yaml"
    if not model_file.exists():
        return {"error": "No .architecture-model.yaml found. Run architect_extract first."}

    try:
        from architecture_model.core.parser import _parse_raw
        import yaml

        raw = yaml.safe_load(model_file.read_text())
        model = _parse_raw(raw)

        # Determine which docs to generate
        requested = {f.strip() for f in formats.split(",")} if formats != "all" else {
            "component_spec", "icd", "dependency_matrix", "health", "drift", "behaviors",
            "system_design", "integration_flows", "diagrams", "index"
        }

        output_dir = path / "docs" / "architecture"
        output_dir.mkdir(parents=True, exist_ok=True)

        generated = []
        errors = []

        # Hydrate file_stats from manifest so component specs show Functions/Classes
        if manifest is not None:
            try:
                _mdata = manifest.to_dict() if hasattr(manifest, 'to_dict') else manifest
                _mod_lookup: dict[str, dict] = {}
                for m in _mdata.get("modules", []):
                    _mod_lookup[m.get("file", "")] = m
                for comp in getattr(model.entities, 'components', []) or []:
                    if not comp.files:
                        continue
                    if comp.extensions is None:
                        comp.extensions = {}
                    fs: dict[str, dict] = comp.extensions.get("file_stats", {})
                    for f in comp.files:
                        if f not in fs or fs[f].get("functions") in (None, "—"):
                            mod = _mod_lookup.get(f, {})
                            fs[f] = {
                                "functions": len(mod.get("functions", [])),
                                "classes": len(mod.get("classes", [])),
                            }
                    comp.extensions["file_stats"] = fs
            except Exception:
                pass  # best-effort hydration

        if "component_spec" in requested or "all" in requested:
            try:
                from architecture_model.docs.component_spec import generate_component_spec
                components = getattr(model.entities, 'components', [])
                if components:
                    parts = [generate_component_spec(comp, model) for comp in components]
                    content = "\n\n---\n\n".join(parts)
                else:
                    content = "# Component Specifications\n\nNo components found."
                out = output_dir / "component_specs.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"component_spec: {e}")

        if "icd" in requested or "all" in requested:
            try:
                from architecture_model.docs.icd import generate_icd
                content = generate_icd(model)
                out = output_dir / "icd.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"icd: {e}")

        if "dependency_matrix" in requested or "all" in requested:
            try:
                from architecture_model.docs.dependency_matrix import generate_dependency_matrix
                content = generate_dependency_matrix(model)
                out = output_dir / "dependency_matrix.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"dependency_matrix: {e}")

        if "health" in requested or "all" in requested:
            try:
                from architecture_model.docs.health import generate_health_report
                content = generate_health_report(model, root=path)
                out = output_dir / "health.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"health: {e}")

        if "behaviors" in requested or "all" in requested:
            try:
                from architecture_model.manifest.generator import generate_manifest
                from architecture_model.manifest.call_graph import build_call_graph, trace_flow, map_flow_to_components
                from architecture_model.orchestration.behavior_flows import (
                    classify_behaviors, summarize_crud_group, build_behavior_manifest,
                    build_behavior_sub_model, build_file_to_comp,
                )
                from architecture_model.docs.behavior_spec import generate_behavior_spec, generate_behavior_index

                manifest = generate_manifest(path)
                behaviors = getattr(model.entities, 'behaviors', [])
                if behaviors:
                    call_graph = build_call_graph(manifest)
                    file_to_comp = build_file_to_comp(model, manifest)
                    classification = classify_behaviors(
                        behaviors, model.relationships, call_graph, file_to_comp
                    )

                    beh_dir = output_dir / "behaviors"
                    beh_dir.mkdir(parents=True, exist_ok=True)

                    for behavior, flow_trace in classification.cross_component:
                        try:
                            scoped = build_behavior_manifest(behavior, flow_trace, manifest)
                            spec_md = generate_behavior_spec(behavior, flow_trace, scoped, file_to_comp)
                            (beh_dir / f"{behavior.id}.md").write_text(spec_md)
                        except Exception:
                            continue

                    crud_summaries = {
                        comp_id: summarize_crud_group(comp_id, behs)
                        for comp_id, behs in classification.crud_groups.items()
                    }
                    index_md = generate_behavior_index(classification, crud_summaries)
                    (beh_dir / "index.md").write_text(index_md)
                    generated.append(str((beh_dir / "index.md").relative_to(path)))
                else:
                    errors.append("behaviors: no behaviors found in model")
            except Exception as e:
                errors.append(f"behaviors: {e}")

        if "system_design" in requested or "all" in requested:
            try:
                from architecture_model.docs.system_design import generate_system_design
                content = generate_system_design(model)
                out = output_dir / "system_design.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"system_design: {e}")

        if "integration_flows" in requested or "all" in requested:
            try:
                from architecture_model.docs.integration_flows import generate_integration_flows
                content = generate_integration_flows(model)
                out = output_dir / "integration_flows.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"integration_flows: {e}")

        if "diagrams" in requested or "all" in requested:
            try:
                from architecture_model.docs.diagrams import generate_all_diagrams
                diag_dir = output_dir / "diagrams"
                diagram_paths = generate_all_diagrams(model, diag_dir)
                generated.extend(str(p.relative_to(path)) for p in diagram_paths)
            except Exception as e:
                errors.append(f"diagrams: {e}")

        if "drift" in requested or "all" in requested:
            try:
                from architecture_model.docs.drift import generate_drift_report
                # Drift requires old + new model comparison
                prev_model = None
                snapshot_dir = path / ".architecture" / "snapshots"
                if snapshot_dir.exists():
                    snapshots = sorted(snapshot_dir.glob("*.yaml"))
                    if snapshots:
                        from architecture_model.core.parser import load_model as _load
                        prev_model = _load(snapshots[-1])
                if prev_model is not None:
                    content = generate_drift_report(prev_model, model)
                    out = output_dir / "drift.md"
                    out.write_text(content)
                    generated.append(str(out.relative_to(path)))
                else:
                    errors.append("drift: skipped (no previous model for comparison)")
            except Exception as e:
                errors.append(f"drift: {e}")

        # Index generated LAST — needs paths of other generated docs
        if "index" in requested or "all" in requested:
            try:
                from architecture_model.docs.index import generate_index
                doc_paths_map: dict[str, list[Path]] = {}
                for gen_path in generated:
                    p = path / gen_path
                    doc_paths_map[p.stem] = [p]
                content = generate_index(model, doc_paths_map)
                out = output_dir / "index.md"
                out.write_text(content)
                generated.append(str(out.relative_to(path)))
            except Exception as e:
                errors.append(f"index: {e}")

        return {
            "generated": generated,
            "output_dir": str(output_dir.relative_to(path)),
            "errors": errors if errors else None,
            "doc_count": len(generated),
        }

    except Exception as e:
        return {"error": f"Doc generation failed: {e}"}

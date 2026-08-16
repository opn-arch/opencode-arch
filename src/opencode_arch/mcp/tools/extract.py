"""architect_extract MCP tool — validate and store an architecture extraction."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from opencode_arch.mcp.quality import with_quality


# Lazy import to allow patching in tests
def _get_telemetry_store():
    from opencode_arch.telemetry.store import TelemetryStore

    return TelemetryStore


@with_quality
async def store_extraction(
    repo_path: str,
    model_yaml: str,
    context_tokens: int = 0,
) -> dict[str, Any]:
    """Validate and store an architecture model extraction.

    IMPORTANT: Do NOT manually write .architecture-model.yaml via file tools.
    ALWAYS use this tool to store models — it validates, backs up, and records telemetry.

    Preferred workflow:
      1. architect_scan(repo_path) — get reality manifest
      2. architect_group(repo_path) — get component boundaries
      3. Build YAML model from scan+group output
      4. architect_extract(repo_path, model_yaml) — validate and store

    Or use architect_pipeline(repo_path) for fully automated extraction.

    Called AFTER the agent has produced a YAML architecture model.
    Validates the model, writes it to .architecture-model.yaml,
    and records telemetry.

    Args:
        repo_path: Path to the repository root (where to save the model).
        model_yaml: The YAML architecture model produced by the agent.
        context_tokens: How many tokens of context the agent used (for telemetry).

    Returns:
        Dict with: stored (bool), score (int), issues (list), telemetry_recorded (bool),
        pipeline (dict), warnings (list).
    """
    path = Path(repo_path)
    pipeline = {}
    warnings: list[str] = []

    try:
        # Parse the YAML
        raw = yaml.safe_load(model_yaml)
        if not isinstance(raw, dict):
            return {
                "stored": False,
                "error": "YAML did not parse to a dict",
                "score": 0,
                "pipeline": pipeline,
                "warnings": warnings,
            }

        # Validate using architecture_model
        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        model = _parse_raw(raw)

        # Entity fallback: if relationships exist but no components, return suggestions
        has_components = bool(getattr(model.entities, "components", None))
        has_relationships = bool(model.relationships)
        if has_relationships and not has_components:
            try:
                from architecture_model.manifest.generator import generate_manifest
                from architecture_model.manifest.grouping import create_components_from_manifest

                manifest = generate_manifest(path)
                components = create_components_from_manifest(manifest)
                if components:
                    return {
                        "stored": False,
                        "reason": "relationships_without_entities",
                        "message": (
                            "Model has relationships but no components. Use the suggested "
                            "components below, map your relationships to the correct IDs, "
                            "and call architect_extract again with a complete model."
                        ),
                        "suggested_components": [
                            {"id": c.id, "name": c.name, "files": c.files} for c in components
                        ],
                        "original_relationships": [
                            {
                                "from": r.from_id,
                                "to": r.to_id,
                                "type": str(r.type.value)
                                if hasattr(r.type, "value")
                                else str(r.type),
                                "description": getattr(r, "description", ""),
                            }
                            for r in model.relationships
                        ],
                        "pipeline": pipeline,
                        "warnings": warnings,
                    }
            except Exception as e:
                pipeline["entity_fallback"] = {"status": "error", "error": str(e)}

        validation = validate_model(model)

        score = validation.score
        issues = [str(issue) for issue in validation.issues]

        # D3: Snapshot existing model before overwrite
        model_file = path / ".architecture-model.yaml"
        try:
            if model_file.exists():
                snapshot_dir = path / ".architecture" / "snapshots"
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().isoformat().replace(":", "-")
                snapshot_path = snapshot_dir / f"{timestamp}.yaml"
                shutil.copy2(model_file, snapshot_path)
                # Cap at 10 snapshots
                snapshots = sorted(snapshot_dir.glob("*.yaml"))
                for old in snapshots[:-10]:
                    old.unlink()
                pipeline["snapshot"] = {"status": "ok", "detail": str(snapshot_path)}
            else:
                pipeline["snapshot"] = {"status": "ok", "detail": "no prior model"}
        except Exception as e:
            pipeline["snapshot"] = {"status": "error", "error": str(e)}

        # Write normalized model to repo (re-serialize from parsed model)
        output_path = path / ".architecture-model.yaml"
        try:
            from architecture_model.core.parser import save_model

            save_model(model, output_path)
        except Exception:
            # Fallback: write raw YAML if serialization fails
            output_path.write_text(model_yaml)

        # Record telemetry
        telemetry_recorded = False
        try:
            TelemetryStore = _get_telemetry_store()
            store = TelemetryStore()
            store.record(
                tool="architect_extract",
                repo=str(path.name),
                context_tokens=context_tokens,
                output_quality=score,
                iterations=1,
            )
            telemetry_recorded = True
            pipeline["telemetry"] = {"status": "ok"}
        except Exception as e:
            pipeline["telemetry"] = {"status": "error", "error": str(e)}

        try:
            from opencode_arch.telemetry.collector import drain_and_store

            drain_and_store(tool="architect_extract", repo=path.name)
            pipeline["telemetry_drain"] = {"status": "ok"}
        except Exception as e:
            pipeline["telemetry_drain"] = {"status": "error", "error": str(e)}

        # After the model is stored successfully, persist full project snapshot
        try:
            from architecture_model.manifest.generator import generate_manifest
            from architecture_model.persistence.store import save_project

            manifest = generate_manifest(Path(repo_path))

            # Try to compute representativeness
            rep = None
            try:
                from architecture_model.core.representativeness import compute_representativeness

                rep = compute_representativeness(model, manifest)
                pipeline["representativeness"] = {"status": "ok"}
            except Exception as e:
                pipeline["representativeness"] = {"status": "error", "error": str(e)}

            save_project(
                Path(repo_path),
                model,
                manifest,
                representativeness=rep,
                telemetry={"context_tokens": context_tokens} if context_tokens else None,
            )
            pipeline["project_snapshot"] = {"status": "ok"}
        except Exception as e:
            pipeline["project_snapshot"] = {"status": "error", "error": str(e)}

        result = {
            "stored": True,
            "score": score,
            "issues": issues,
            "path": str(output_path),
            "telemetry_recorded": telemetry_recorded,
        }

        # E3: Surface representativeness scores in response
        if rep is not None:
            result["representativeness"] = {
                "file_coverage": round(rep.file_coverage, 1),
                "relationship_accuracy": round(rep.relationship_accuracy, 1),
                "boundary_coherence": round(rep.boundary_coherence, 1),
                "overall": round(rep.overall, 1),
            }

        # Warn if entities empty but relationships exist
        has_entities = False
        if hasattr(model, "entities"):
            ent = model.entities
            if hasattr(ent, "components"):
                has_entities = bool(ent.components)
            elif isinstance(ent, dict):
                has_entities = any(bool(v) for v in ent.values())
        has_rels = bool(getattr(model, "relationships", None))
        if has_rels and not has_entities:
            result["warning"] = (
                "Model has relationships but no entities/components defined. "
                "Docs will be empty. Re-extract with components under entities.components."
            )

        # Generate manifest early so docs and later stages can use it
        _manifest = None
        try:
            from architecture_model.manifest.generator import generate_manifest as _gen_early

            _manifest = _gen_early(path)
        except Exception:
            pass

        # Auto-generate SE docs
        try:
            from opencode_arch.mcp.tools.docs import generate_docs

            docs_result = await generate_docs(repo_path=repo_path, manifest=_manifest)
            if isinstance(docs_result, dict) and docs_result.get("generated"):
                result["docs_generated"] = docs_result["generated"]
            pipeline["docs"] = {"status": "ok"}
        except Exception as e:
            pipeline["docs"] = {"status": "error", "error": str(e)}

        # Write top-level manifest.json
        if _manifest is not None:
            try:
                import json as _json_manifest

                models_dir = path / ".architecture-models"
                models_dir.mkdir(parents=True, exist_ok=True)
                manifest_path = models_dir / "manifest.json"
                manifest_data = _manifest.to_dict() if hasattr(_manifest, "to_dict") else _manifest
                manifest_path.write_text(_json_manifest.dumps(manifest_data, indent=2))
                result["manifest_path"] = str(manifest_path.relative_to(path))
            except Exception:
                pass  # best-effort

        # Auto-generate diagrams
        try:
            from architecture_model.docs.diagrams import generate_all_diagrams

            diag_dir = path / "docs" / "architecture" / "diagrams"
            diagram_paths = generate_all_diagrams(model, diag_dir)
            result["diagrams_generated"] = len(diagram_paths)
            pipeline["diagrams"] = {"status": "ok"}
        except Exception as e:
            pipeline["diagrams"] = {"status": "error", "error": str(e)}

        # Auto-decompose into sub-models + recursive manifests
        try:
            import json as _json
            from architecture_model.orchestration.decompose import decompose_model, write_sub_models
            from architecture_model.manifest.recursive import generate_recursive_manifests

            sub_models = decompose_model(path)
            if sub_models:
                out_dir = path / ".architecture-models"
                write_sub_models(sub_models, out_dir)
                result["sub_models"] = list(sub_models.keys())

            # Use manifest's functional_blocks as override if config doesn't have them
            source_block_override = None
            try:
                from architecture_model.config.loader import get_config

                cfg = get_config(path)
                if not cfg.source_block_dict:
                    from architecture_model.manifest.generator import (
                        generate_manifest as _gen_manifest,
                    )

                    m = _gen_manifest(path)
                    if m.functional_blocks:
                        source_block_override = m.functional_blocks
            except Exception:
                pass

            recursive = generate_recursive_manifests(
                path, source_block_override=source_block_override
            )
            if recursive:
                manifests_dir = path / ".architecture" / "manifests"
                manifests_dir.mkdir(parents=True, exist_ok=True)
                for block_id, rm in recursive.items():
                    out = manifests_dir / f"{block_id}.json"
                    out.write_text(_json.dumps(rm.manifest.to_dict(), indent=2))
                result["recursive_manifests"] = list(recursive.keys())
            pipeline["decompose"] = {"status": "ok"}
        except Exception as e:
            pipeline["decompose"] = {"status": "error", "error": str(e)}

        # Auto-create granular behaviors from manifest
        try:
            from architecture_model.orchestration.auto_enrich import create_behaviors_from_manifest
            from architecture_model.core.parser import save_model as _save

            # Top-level behaviors (reuse manifest generated earlier)
            if _manifest is None:
                try:
                    from architecture_model.manifest.generator import generate_manifest as _gen

                    _manifest = _gen(path)
                except Exception:
                    pass

            if _manifest and hasattr(model.entities, "components") and model.entities.components:
                existing_behaviors = getattr(model.entities, "behaviors", None) or []
                if not existing_behaviors:
                    top_behaviors, top_rels = create_behaviors_from_manifest(model, _manifest)
                    if top_behaviors:
                        model.entities.behaviors = top_behaviors
                        model.relationships.extend(top_rels)
                        _save(model, output_path)
                        result["behaviors_created"] = len(top_behaviors)

            # Recursive: behaviors for each sub-model
            if "sub_models" in result and _manifest:
                try:
                    sub_beh_count = 0
                    out_dir = path / ".architecture-models"
                    for block_id in result.get("sub_models", []):
                        sub_model_path = out_dir / block_id / ".architecture-model.yaml"
                        if not sub_model_path.exists():
                            continue
                        # Load sub-model
                        from architecture_model.core.parser import load_model as _load

                        sub_model = _load(sub_model_path)
                        # Get recursive manifest for this block
                        rm_path = path / ".architecture" / "manifests" / f"{block_id}.json"
                        if rm_path.exists():
                            import json as _j
                            from architecture_model.manifest.types import (
                                Manifest as _M,
                                MetricsResult as _MR,
                            )
                            from architecture_model.manifest.types import (
                                ModuleInfo as _MI,
                                FunctionInfo as _FI,
                                ModuleStatus as _MS,
                            )

                            rm_data = _j.loads(rm_path.read_text())
                            # Reconstruct manifest from JSON
                            rm_modules = []
                            for md in rm_data.get("modules", []):
                                fns = [
                                    _FI(
                                        name=f.get("name", ""),
                                        signature=f.get("signature", ""),
                                        calls=f.get("calls", []),
                                        raises=f.get("raises", []),
                                    )
                                    for f in (md.get("functions") or [])
                                ]
                                rm_modules.append(
                                    _MI(
                                        file=md["file"],
                                        name=md.get("name", ""),
                                        docstring=md.get("docstring"),
                                        functions=fns,
                                        imports=md.get("imports", []),
                                        line_count=md.get("line_count", 0),
                                        status=_MS.ACTIVE,
                                        classes=[],
                                    )
                                )
                            rm_ifaces = rm_data.get("interfaces", [])
                            iface_objs = [
                                type(
                                    "I",
                                    (),
                                    {"source": i.get("source", ""), "target": i.get("target", "")},
                                )()
                                for i in rm_ifaces
                            ]
                            rm_manifest = _M(
                                modules=rm_modules,
                                interfaces=iface_objs,
                                functional_blocks={},
                                generated_at=rm_data.get("generated_at", ""),
                                project_root=str(path),
                                metrics=_MR(values={"total_python_files": len(rm_modules)}),
                            )
                            sub_behs, sub_rels = create_behaviors_from_manifest(
                                sub_model, rm_manifest
                            )
                            if sub_behs:
                                if (
                                    not hasattr(sub_model.entities, "behaviors")
                                    or sub_model.entities.behaviors is None
                                ):
                                    sub_model.entities.behaviors = []
                                sub_model.entities.behaviors.extend(sub_behs)
                                sub_model.relationships.extend(sub_rels)
                                _save(sub_model, sub_model_path)
                                sub_beh_count += len(sub_behs)
                    if sub_beh_count:
                        result["sub_model_behaviors_created"] = sub_beh_count
                except Exception as e:
                    pipeline["sub_model_behaviors"] = {"status": "error", "error": str(e)}
            pipeline["behaviors"] = {"status": "ok"}
        except Exception as e:
            pipeline["behaviors"] = {"status": "error", "error": str(e)}

        # Auto-extract interfaces from cross-component imports
        try:
            from architecture_model.orchestration.auto_enrich import (
                extract_component_interfaces,
                manifest_to_source_graph,
            )
            from architecture_model.core.parser import save_model as _save_iface

            if _manifest is None:
                try:
                    from architecture_model.manifest.generator import (
                        generate_manifest as _gen_iface,
                    )

                    _manifest = _gen_iface(path)
                except Exception:
                    pass

            if _manifest and hasattr(model.entities, "components") and model.entities.components:
                source_graph = manifest_to_source_graph(_manifest, model)
                interface_count = extract_component_interfaces(model, source_graph)
                if interface_count > 0:
                    try:
                        _save_iface(model, output_path)
                    except Exception:
                        # Fallback: write via YAML dump if save_model fails
                        try:
                            from architecture_model.core.parser import dump_model
                            import yaml as _yaml_iface

                            output_path.write_text(
                                _yaml_iface.dump(
                                    dump_model(model), default_flow_style=False, sort_keys=False
                                )
                            )
                        except Exception:
                            pass  # Interface data is in memory; persist is best-effort
                pipeline["interfaces"] = {"status": "ok", "count": interface_count}
            else:
                pipeline["interfaces"] = {"status": "skipped", "count": 0}
        except Exception as e:
            pipeline["interfaces"] = {"status": "error", "error": str(e)}

        # Auto-classify behavior flows and generate per-behavior artifacts
        try:
            from architecture_model.manifest.call_graph import (
                build_call_graph,
                trace_flow,
                map_flow_to_components,
            )
            from architecture_model.orchestration.behavior_flows import (
                classify_behaviors,
                summarize_crud_group,
                build_behavior_manifest,
                build_behavior_sub_model,
                build_file_to_comp,
                BehaviorClassification,
            )
            from architecture_model.docs.behavior_spec import (
                generate_behavior_spec,
                generate_behavior_index,
            )
            from architecture_model.core.parser import save_model as _save_beh

            if _manifest and hasattr(model.entities, "behaviors") and model.entities.behaviors:
                # Build call graph
                call_graph = build_call_graph(_manifest)
                file_to_comp = build_file_to_comp(model, _manifest)

                # Classify
                classification = classify_behaviors(
                    model.entities.behaviors,
                    model.relationships,
                    call_graph,
                    file_to_comp,
                )

                # Write cross-component behavior artifacts
                beh_model_dir = path / ".architecture-models" / "behaviors"
                beh_doc_dir = path / "docs" / "architecture" / "behaviors"
                beh_model_dir.mkdir(parents=True, exist_ok=True)
                beh_doc_dir.mkdir(parents=True, exist_ok=True)

                for behavior, flow_trace in classification.cross_component:
                    try:
                        # Scoped manifest
                        scoped = build_behavior_manifest(behavior, flow_trace, _manifest)
                        # Sub-model
                        sub_model = build_behavior_sub_model(
                            behavior, flow_trace, model, file_to_comp
                        )
                        # Write sub-model
                        beh_out = beh_model_dir / behavior.id
                        beh_out.mkdir(parents=True, exist_ok=True)
                        _save_beh(sub_model, beh_out / "model.yaml")
                        # Write spec doc
                        spec_md = generate_behavior_spec(behavior, flow_trace, scoped, file_to_comp)
                        (beh_doc_dir / f"{behavior.id}.md").write_text(spec_md)
                    except Exception:
                        continue  # Skip individual behavior failures

                # Write behavior index
                crud_summaries = {
                    comp_id: summarize_crud_group(comp_id, behs)
                    for comp_id, behs in classification.crud_groups.items()
                }
                index_md = generate_behavior_index(classification, crud_summaries)
                (beh_doc_dir / "index.md").write_text(index_md)

                result["behavior_flows"] = {
                    "cross_component": len(classification.cross_component),
                    "crud_groups": len(classification.crud_groups),
                    "trivial": len(classification.trivial),
                }
                pipeline["behavior_flows"] = {"status": "ok"}

                # Compact model: offload leaf behaviors to sub-models
                try:
                    from architecture_model.orchestration.compaction import compact_for_storage
                    from architecture_model.core.parser import save_model as _save_compact

                    original_count = len(model.entities.behaviors)
                    model, offloaded = compact_for_storage(model)

                    # Write per-component sub-models with full behaviors
                    for comp_id, comp_behaviors in offloaded.items():
                        comp_dir = path / ".architecture-models" / comp_id
                        comp_dir.mkdir(parents=True, exist_ok=True)
                        comp = next((c for c in model.entities.components if c.id == comp_id), None)
                        if comp:
                            from architecture_model.core.types import (
                                ArchitectureModel as _AM,
                                Entities as _E,
                                ModelMeta as _MM,
                            )

                            sub = _AM(
                                meta=_MM(project=f"{path.name}/{comp.name}", schema_version="1.3"),
                                entities=_E(components=[comp], behaviors=comp_behaviors),
                                relationships=[
                                    r
                                    for r in model.relationships
                                    if r.from_id == comp_id
                                    or r.to_id in {b.id for b in comp_behaviors}
                                ],
                            )
                            try:
                                _save_compact(sub, comp_dir / ".architecture-model.yaml")
                            except Exception:
                                pass

                    _save_beh(model, output_path)
                    result["behaviors_reduced"] = (
                        f"{original_count} -> {len(model.entities.behaviors)}"
                    )
                    pipeline["compaction"] = {"status": "ok"}
                except Exception as e:
                    pipeline["compaction"] = {"status": "error", "error": str(e)}
            else:
                pipeline["behavior_flows"] = {"status": "ok", "detail": "no behaviors to classify"}
        except Exception as e:
            pipeline["behavior_flows"] = {"status": "error", "error": str(e)}

        result["next_steps"] = (
            "Use architect_slice for focused context on specific components. "
            "Use architect_log to record architectural decisions."
        )
        result["pipeline"] = pipeline
        result["warnings"] = warnings
        return result

    except yaml.YAMLError as e:
        return {
            "stored": False,
            "error": f"Invalid YAML: {e}",
            "score": 0,
            "pipeline": pipeline,
            "warnings": warnings,
        }
    except Exception as e:
        return {
            "stored": False,
            "error": f"Validation failed: {e}",
            "score": 0,
            "pipeline": pipeline,
            "warnings": warnings,
        }

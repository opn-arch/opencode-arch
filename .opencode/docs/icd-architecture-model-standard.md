# ICD: opencode-arch ↔ architecture-model-standard

> Interface Contract Document — all imports from `architecture_model.*` used by opencode-arch MCP tools.

## Core Parser

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `load_model` | `architecture_model.core.parser` | Load .architecture-model.yaml → ArchitectureModel | check, extract, gate, regen_score, slice |
| `save_model` | `architecture_model.core.parser` | Write ArchitectureModel → YAML file | author, extract, ingest |
| `dump_model` | `architecture_model.core.parser` | Serialize model to YAML string | extract |
| `_parse_raw` | `architecture_model.core.parser` | Parse YAML string → ArchitectureModel (no file I/O) | docs, extract, gate, validate |
| `parse_model` | `architecture_model.core.parser` | Parse model from dict | llm_audit |
| `ArchitectureModel` | `architecture_model.core.parser` | Main model type (re-export) | gate |

## Core Types

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `Relationship` | `architecture_model.core.types` | Relationship dataclass | ingest |
| `RelationType` | `architecture_model.core.types` | Enum of relationship types | ingest |
| (various types) | `architecture_model.core.types` | Entity types for model construction | extract |

## Core Validator

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `validate_model` | `architecture_model.core.validator` | Run all validation checks, return score | extract, validate |

## Core Representativeness

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `compute_representativeness` | `architecture_model.core.representativeness` | FC/RA/BC scores vs code reality | check, extract |

## Core Slicer

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `slice_by_layer` | `architecture_model.core.slicer` | Extract model subset by layer/component | slice |

## Core Regen Readiness

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| (regen functions) | `architecture_model.core.regen_readiness` | Compute regen readiness scores | regen_score |

## Core Source Block Quality

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `compute_source_block_quality` | `architecture_model.core.source_block_quality` | Quality metrics per S-block | llm_audit |

## Core Corrections

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `store_correction` | `architecture_model.core.corrections` | Persist correction for next pipeline run | correct |

## Config

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `get_config` | `architecture_model.config.loader` | Load ProjectConfig from repo root | check, decompose, extract |

## Manifest

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `generate_manifest` | `architecture_model.manifest.generator` | AST scan → manifest JSON | check, decompose, docs, extract, gate, scan, slice |
| `group_modules` | `architecture_model.manifest.grouping` | Cluster modules by import affinity | check, group, scan, slice |
| `auto_source_blocks` | `architecture_model.manifest.grouping` | Generate S-block config from groups | check, ingest |
| `create_components_from_manifest` | `architecture_model.manifest.grouping` | Manifest → Component entities | extract |
| `group_source_graph` | `architecture_model.manifest.grouping` | Group SourceGraph nodes | ingest |
| `generate_recursive_manifests` | `architecture_model.manifest.recursive` | Per-block manifest generation | check, decompose, extract |
| `build_call_graph` | `architecture_model.manifest.call_graph` | Function-level call graph | docs, extract |
| `trace_flow` | `architecture_model.manifest.call_graph` | Trace execution path | docs |
| `map_flow_to_components` | `architecture_model.manifest.call_graph` | Map call flow → components | docs |
| `SourceGraph` | `architecture_model.manifest.protocol` | Language-agnostic source graph type | ingest |

## Manifest Types

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| (manifest types) | `architecture_model.manifest.types` | ModuleInfo, etc. for manifest data | extract |

## Orchestration

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `decompose_model` | `architecture_model.orchestration.decompose` | Split model into sub-models per system | decompose, extract |
| `write_sub_models` | `architecture_model.orchestration.decompose` | Write sub-model YAML files | decompose, extract |
| `compact_for_storage` | `architecture_model.orchestration.compaction` | Remove redundant data before save | extract |
| `create_behaviors_from_manifest` | `architecture_model.orchestration.auto_enrich` | Auto-generate behaviors from code | extract |
| `enrich_from_source_graph` | `architecture_model.orchestration.auto_enrich` | Enrich model from SourceGraph | ingest |
| `extract_component_interfaces` | `architecture_model.orchestration.auto_enrich` | Derive interfaces from components | ingest |
| (behavior_flows functions) | `architecture_model.orchestration.behavior_flows` | Generate behavior flow diagrams | docs, extract |

## Docs Generation

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `generate_component_spec` | `architecture_model.docs.component_spec` | Component specification doc | docs |
| `generate_icd` | `architecture_model.docs.icd` | Interface control document | docs |
| `generate_dependency_matrix` | `architecture_model.docs.dependency_matrix` | Dependency matrix doc | docs |
| `generate_health_report` | `architecture_model.docs.health` | Model health report | docs |
| `generate_drift_report` | `architecture_model.docs.drift` | Code drift detection | docs |
| `generate_index` | `architecture_model.docs.index` | Documentation index | docs |
| `generate_all_diagrams` | `architecture_model.docs.diagrams` | Mermaid/PlantUML diagrams | docs, extract |
| `generate_behavior_spec` | `architecture_model.docs.behavior_spec` | Behavior specification | docs, extract |
| `generate_behavior_index` | `architecture_model.docs.behavior_spec` | Behavior index | docs |
| `generate_se_docs` | `architecture_model.docs.se.generator` | SE document suite | docs |
| `generate_integration_flows` | `architecture_model.docs.integration_flows` | Integration flow docs | docs |
| `generate_system_design` | `architecture_model.docs.system_design` | System design doc | docs |

## Authoring

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `parse_requirements_doc` | `architecture_model.authoring.parser` | Parse requirements → model | author |
| `check_development_gate` | `architecture_model.authoring.gate` | Gate readiness check | gate |

## Pipeline Stages

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `ObserveStage` | `architecture_model.pipeline.observe` | AST inventory | pipeline |
| `InferStage` | `architecture_model.pipeline.infer` | Capability/actor inference | pipeline |
| `AllocateStage` | `architecture_model.pipeline.allocate` | File→component allocation | pipeline |
| `RelateStage` | `architecture_model.pipeline.relate` | Relationship derivation | pipeline |
| `SpecifyStage` | `architecture_model.pipeline.specify` | Interface specification | pipeline |
| `ContractStage` | `architecture_model.pipeline.contract` | Test contract mapping | pipeline |
| `ValidateStage` | `architecture_model.pipeline.validate` | Model validation | pipeline |
| `DecomposeStage` | `architecture_model.pipeline.decompose` | System boundary detection | pipeline |
| `SynthesizeStage` | `architecture_model.pipeline.synthesize` | System-of-systems assembly | pipeline |
| `EmitStage` | `architecture_model.pipeline.emit` | Write artifacts to disk | pipeline |
| `Evidence` | `architecture_model.pipeline.protocol` | Provenance for claims | pipeline |

## Other

| Symbol | Module | Purpose | Used by |
|--------|--------|---------|---------|
| `GlobalLearningStore` etc. | `architecture_model.pipeline.global_learning` | Cross-session learning | learn |
| `build_flat_export` | `architecture_model.export.flatfiles` | Export for mobile AI | export |
| `save_project` | `architecture_model.persistence.store` | Persistence layer | extract |

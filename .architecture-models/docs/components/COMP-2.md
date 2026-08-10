# Component: Artifacts (COMP-2)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/artifacts/context.py` | — | — |
| `src/opencode_arch/artifacts/diagrams.py` | — | — |
| `src/opencode_arch/artifacts/selector.py` | — | — |
| `src/opencode_arch/artifacts/templates.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `assemble_artifact_context` | `template: ArtifactTemplate, model: ArchitectureModel, manifest: dict | None, max_tokens: int` | `str` | Assemble formatted context for artifact generation.

Returns a structured prompt string containing:
1. System prompt from template
2. For each section: heading + extracted data + instructions

Token budget is approximate (1 token ~ 4 chars). If total exceeds budget,
truncate section data (not instructions). |
| `format_capability_detail_context` | `cap_id: str, model: ArchitectureModel, manifest: dict | None` | `str` | Assemble rich context for generating a per-capability API detail doc.

Extracts the full neighborhood of a single capability:
- The capability entity itself
- Realizing component(s) and their files/signatures/constants
- Related behaviors (steps, triggers, pre/postconditions)
- Exposed interfaces (endpoints, protocol)
- Applicable constraints
- Upstream/downstream relationships

Returns a structured text block suitable for LLM prompt injection. |
| `generate_component_diagram` | `model: ArchitectureModel` | `str` | Generate a C4-style component diagram showing system structure.

Groups components by layer, renders actors, and shows
depends-on/exposes/consumes relationships. |
| `generate_dependency_diagram` | `model: ArchitectureModel` | `str` | Generate a dependency graph showing component relationships.

Simpler than C4 — plain PlantUML with rectangles and arrows.
Only includes entities that participate in at least one relationship. |
| `generate_sequence_diagram` | `behavior: Behavior, model: ArchitectureModel` | `str` | Generate a sequence diagram from a behavior's steps.

Returns empty string if behavior has no steps. |
| `generate_nav_diagram` | `model: ArchitectureModel` | `str` | Generate a full-model navigational traceability diagram.

Shows ALL entities (typed shapes) and ALL relationships (labeled edges)
on a single page. Components are nested inside their layer packages.
Every node displays its ID for precise referencing by systems engineers. |
| `generate_focused_diagram` | `model: ArchitectureModel, entity_id: str, depth: int` | `str` | Generate a focused subgraph centered on a specific entity.

Performs BFS from entity_id through relationships (both directions)
up to `depth` hops. Renders only the reachable subgraph with the
focus entity highlighted.

Returns empty string if entity_id is not found in the model. |
| `generate_all_diagrams` | `model: ArchitectureModel` | `dict[str, str]` | Generate all applicable diagrams for the model.

Returns dict mapping diagram name to PlantUML string.
Only includes diagrams where there's enough data. |
| `select_artifacts` | `model: ArchitectureModel, manifest: dict | None, include_capability_details: bool` | `list[ArtifactSpec]` | Return artifacts appropriate for this model's richness.

For each artifact in the registry, check if the model has the required entities.
Return only those artifacts whose requirements are met.
Results sorted by priority (1 first), then alphabetically by id.

If include_capability_details is True, also generates per-capability
api-detail-{cap_id} artifacts for every realized capability. |
| `get_artifact_spec` | `artifact_id: str` | `ArtifactSpec | None` | Look up a single artifact spec by ID. |
| `should_decompose` | `model: ArchitectureModel, manifest: dict | None` | `bool` | Determine if system is complex enough to warrant per-subsystem docs.

Heuristic: returns True if ANY of:
- More than 5 functional blocks (distinct source_block values on components)
- More than 50 source files in manifest
- More than 20 components |
| `select_subsystem_artifacts` | `subsystem: SubsystemInfo, model: ArchitectureModel, manifest: dict | None` | `list[ArtifactSpec]` | Select artifacts appropriate for a subsystem (subset of system-level).

Only returns artifacts from SUBSYSTEM_ARTIFACTS that:
1. Are in the SUBSYSTEM_ARTIFACTS list
2. Have their requirements met (scoped to subsystem's components)

Returns empty list if subsystem has no components. |
| `select_capability_detail_artifacts` | `model: ArchitectureModel` | `list[ArtifactSpec]` | Generate one ArtifactSpec per capability for detailed API docs.

Only includes capabilities that have at least one realizing component
(via 'realizes' relationship). Each gets artifact_id = "api-detail-{cap.id}". |
| `get_template` | `artifact_id: str` | `ArtifactTemplate | None` | Look up template by artifact ID. Returns None if not found. |

## Patterns

None

## Confidence

57%

# Pipeline Type Contracts

> Data types flowing through each stage of the extraction pipeline.

## Pipeline Flow

```
observe → infer → allocate → relate → specify → contract → validate → decompose → synthesize → emit
```

Every stage returns `StageResult[T]` where `T` is the stage-specific output type.

## Common Protocol Types

```python
@dataclass
class Evidence:
    source: str          # "ast", "llm_analysis", "config", "test", etc.
    confidence: float    # 0.0 - 1.0
    raw: str             # raw evidence text
    location: str        # file:line

@dataclass
class Claim(Generic[T]):
    value: T
    evidence: list[Evidence]
    uncertain: bool
    # confidence = weighted average of evidence (see SOURCE_WEIGHTS)

@dataclass
class Uncertainty:
    category: str
    description: str
    context: dict
    suggested_fallback: str   # "llm_analysis"
    priority: str             # "enriching"

@dataclass
class QualityMetrics:
    score: float
    sub_scores: dict[str, float]
    thresholds: dict[str, float]
    # passes = all sub_scores >= thresholds

@dataclass
class StageResult(Generic[T]):
    output: T
    quality: QualityMetrics
    diagnostics: list[Diagnostic]
    uncertainties: list[Uncertainty]
    input_hash: str
    duration_ms: int

@dataclass
class PipelineContext:
    repo_path: Path
    output_dir: Path
    domain: str              # "software"
    scope: str               # system ID for scoped runs
    scope_files: list[Path]
    config: dict
    cache: dict[str, StageResult]
    prior_corrections: list[Evidence]
    learning_store: LearningStore | None
    global_learning: GlobalLearningStore | None
    llm_callback: Any        # async (stage, prompt, context) -> str
```

## Source Weights

```python
SOURCE_WEIGHTS = {
    "ast": 1.0,
    "user_confirmation": 1.0,
    "user_correction": 1.0,
    "test": 0.95,
    "config": 0.9,
    "netlist": 0.95,
    "documentation": 0.8,
    "git_history": 0.7,
    "llm_analysis": 0.6,
    "search_result": 0.5,
}
```

## Stage 1: Observe → `Inventory`

```python
@dataclass
class Inventory:
    modules: list[ModuleRecord]      # per-file AST data
    edges: list[ImportEdge]          # import relationships
    routes: list[RouteRecord]        # HTTP/API routes
    constraints: list[ConstraintRecord]  # tech constraints
    test_files: list[TestFileRecord]
    docs: list[DocRecord]

@dataclass
class ModuleRecord:
    path: Path
    language: str
    functions: list[FunctionRecord]
    classes: list[ClassRecord]
    constants: list[ConstantRecord]
    imports: list[str]
    line_count: int
    docstring: str | None

@dataclass
class ImportEdge:
    source: Path
    target: Path
    symbols: list[str]
```

**Requires**: nothing (entry point)

## Stage 2: Infer → `InferenceResult`

```python
@dataclass
class InferenceResult:
    capabilities: list[InferredCapability]
    actors: list[InferredActor]
    behaviors: list[InferredBehavior]

@dataclass
class InferredCapability:
    id: str
    name: str
    description: str
    evidence_source: str    # "routes", "domain_module", "test_pattern"
    sub_capabilities: list[str]

@dataclass
class InferredActor:
    id: str
    name: str
    actor_type: str         # "human" | "system" | "timer"

@dataclass
class InferredBehavior:
    id: str
    name: str
    actor_id: str
    capability_id: str
    steps: list[str]
    triggers: list[str]
    behavior_type: str      # "use_case" | "workflow" | "route_handler"
```

**Requires**: `observe`

## Stage 3: Allocate → `AllocationResult`

```python
@dataclass
class AllocationResult:
    components: list[ComponentAllocation]
    unallocated: list[Path]
    file_coverage: float        # 0.0-1.0
    boundary_coherence: float   # cross-boundary import ratio

@dataclass
class ComponentAllocation:
    id: str
    name: str
    capability_id: str
    files: list[Path]
    layer: str                  # "web", "service", "data", "infra"
```

**Requires**: `observe`, `infer`

## Stage 4: Relate → `RelateResult`

```python
@dataclass
class RelateResult:
    relationships: list[DerivedRelationship]
    layers: list[dict]          # first-class layer entities

@dataclass
class DerivedRelationship:
    from_id: str
    to_id: str
    rel_type: str               # "realizes", "depends-on", "contains", "exposes"
    evidence_source: str        # "import", "call", "inheritance", "config"
    confidence: float
```

**Requires**: `observe`, `infer`, `allocate`

## Stage 5: Specify → `SpecifyResult`

```python
@dataclass
class SpecifyResult:
    interfaces: list[InterfaceSpec]

@dataclass
class InterfaceSpec:
    id: str
    name: str
    component_id: str
    interface_type: str         # "rest", "grpc", "event", "cli", "library"
    methods: list[str]
    description: str
```

**Requires**: `observe`, `allocate`

## Stage 6: Contract → `ContractResult`

```python
@dataclass
class ContractResult:
    contracts: list[TestContract]
    coverage_ratio: float       # components with tests / total

@dataclass
class TestContract:
    test_file: str
    target_component: str
    assertions: int
    description: str
```

**Requires**: `observe`, `allocate`

## Stage 7: Validate → `ValidateResult`

```python
@dataclass
class ValidateResult:
    score: int                  # 0-100
    issues: list[ValidationIssue]
    is_valid: bool

@dataclass
class ValidationIssue:
    severity: str               # "error", "warning", "info"
    message: str
    entity_id: str
    rule: str
```

**Requires**: `allocate`, `relate`

## Stage 8: Decompose → `DecomposeResult`

```python
@dataclass
class DecomposeResult:
    systems: list[SystemBoundary]
    inline_components: list[SystemBoundary]
    inter_system_edges: list[tuple[str, str, str]]  # (from_sys, to_sys, rel_type)

@dataclass
class SystemBoundary:
    system_id: str
    name: str
    component_ids: list[str]
    files: list[str]
    complexity: float
    is_full_system: bool        # False = inline (too small)
```

**Requires**: `allocate`, `relate`

## Stage 9: Synthesize → `SynthesizeResult`

```python
@dataclass
class SynthesizeResult:
    sos_model: SoSModel | None
    sos_model_yaml: str
    system_models: list[SystemModel]
    top_manifest_json: str
    pipeline_report_md: str
    lessons_md: str
    all_llm_calls: list[LLMCallRecord]

@dataclass
class SystemModel:
    system_id: str
    name: str
    model_yaml: str
    manifest_json: str
    stage_results: dict[str, StageResult]

@dataclass
class SoSModel:
    model_yaml: str
    actors: list[dict]
    emergent_capabilities: list[dict]
    cross_system_behaviors: list[dict]
    inter_system_interfaces: list[dict]
    constraints: list[dict]
```

**Requires**: `decompose`

## Stage 10: Emit → `EmitResult`

```python
@dataclass
class EmitResult:
    written_paths: list[str]
    total_bytes: int
    system_count: int
    doc_count: int
    output_dir: str
```

**Requires**: `synthesize`

## Stage Protocol

```python
class Stage(Protocol[T]):
    name: str
    version: str
    requires: list[str]     # names of prerequisite stages

    def run(self, context: PipelineContext) -> StageResult[T]: ...
    def can_run(self, context: PipelineContext) -> bool: ...
    def output_path(self, context: PipelineContext) -> Path: ...
```

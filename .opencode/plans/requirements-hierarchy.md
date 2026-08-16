# opencode-arch Requirements Hierarchy

**Source:** 245 sessions analyzed, 1216 unique requirements extracted

## Extraction & Pipeline (COMP-1) (483 requirements)

### MUST
- Extraction pipeline must detect multiple trigger types: HTTP routes, WebSocket, gRPC, CLI commands, event handlers, sche
- Entity decomposition must produce relationships, not just flat component lists
- Service behavior filter threshold must be configurable and documented as a design parameter
- Implement _derive_component_dependencies() that maps import edges to component-level depends-on relationships
- Add validation rule flagging models with components but zero relationships
- architect_slice should be called before editing core orchestration modules
- COMP-1 should be split to separate orchestration from utilities
- Model must define relationships between components
- *... +60 more*

### SHOULD
- Document design rationale for grouping formula parameters including empirical basis
- Add benchmarks comparing affinity-based grouping vs subdirectory-only grouping
- architect_scan should expose introspection mode showing supported languages and parsing capabilities
- architect_slice should be able to expose scan/manifest pipeline internals as architectural context
- Document functional_blocks schema and origin (user-defined vs auto-generated) in model artifacts
- architect_slice should support an ontology mode showing entity type relationships (function→behavior→component→capabilit
- architect_pipeline should support a describe/explain mode that documents what each stage does without executing
- Decompose extraction pipeline into sub-capabilities: AST Scanning, Behavior Classification, Component Formation, Use-Cas
- *... +229 more*

### COULD
- Support structured metadata extraction for discovered algorithms/formulas
- Add external_dependencies section to model schema for third-party library dependencies
- Model should include its own generation pipeline as a documented component
- Support multi-part research questions as linked child logs
- Support multi-system linking when conversations span multiple codebases
- Add entity lineage tracing: show how a function flows through pipeline to become behavior/capability/use-case
- Add functional_analysis artifact documenting the entity decomposition hierarchy
- Flag and handle truncated assistant responses during ingestion
- *... +170 more*

## Context & Validation (COMP-6) (180 requirements)

### MUST
- Document ICD between SourceGraph and Manifest types with field-level mapping
- scan_all_languages() and generate_manifest() signatures must be documented as interface specs
- Agent must call architect_slice before implementing new modules to understand existing types
- Ingestion must detect bug/issue discoveries and create typed issue child logs
- Model must have non-zero relationships; auto-generate from import analysis as fallback
- Support multi-system linking for cross-repo operations
- architect_slice should be callable as a prerequisite step before documentation generation
- Dependency matrix artifact needed for inter-module relationships
- *... +7 more*

### SHOULD
- architect_slice tool should support a help/introspect mode returning valid focus types, artifact modes, and parameters
- Orchestration subsystem must be represented as a component with compaction as a capability
- Auto-invoke architect_log when creating new files
- Auto-run architect_check after edits to core modules
- Auto-invoke architect_slice before editing core architecture files
- architect_slice must support a type_definitions mode that returns dataclass fields for named types
- Define cross-repo dependency between opencode-arch and architecture-model-standard
- Auto-fetch architecture context before editing core algorithm files
- *... +84 more*

### COULD
- Document compression ratio thresholds and their impact on pass rates
- architect_slice should support algorithm rationale queries
- Support research/code-archaeology session type that extracts structured architecture findings
- Models with 0 relationships should trigger a health warning
- Extract numbered tasks from conversation as individual child logs
- Log implementation decisions automatically after task completion
- Auto-invoke architect_check before implementing to verify alignment
- Recognize code research patterns and extract structured findings
- *... +65 more*

## Model Management (COMP-7) (10 requirements)

### MUST
- architect_diff should accept git commit references to compare architecture model states across history
- Add a Persistence capability covering serialization/deserialization of models, manifests, and metrics

### SHOULD
- Add architect_log call after investigative sessions to record findings automatically

### COULD
- Capture written scripts as linked artifacts
- Extract quantitative metrics into structured fields
- Handle truncated tool outputs by flagging and reconstructing
- Flag segments with high tool-call counts as potentially inefficient
- Parse CAP- prefixed lines as structured capability definitions
- Detect read-only exploration segments and tag appropriately
- Auto-extract environment/dependency issues as child logs

## Documentation (COMP-8) (35 requirements)

### MUST
- Populate relationships between components
- Models must include relationships between components
- Add relationships to logical architecture artifact
- architect_scan must auto-trigger after file creation operations to keep manifest current
- architect_log must be called when new modules are created
- Models with >5 components must have at least 1 relationship per component
- Relationships must be populated - zero relationships makes model unusable
- Tools must be auto-suggested when relevant context exists (e.g., writing docs about a project should trigger architect_s

### SHOULD
- Validation scoring formula and issue categories should be documented in a user-facing spec
- Add relationships between components, minimum coverage threshold
- COMP-8 should be decomposed into orchestration vs specific generators
- Define artifact type for per-component sub-model YAML specs
- Auto-suggest architect_slice when agent greps for type definitions
- Auto-invoke architect_log after file creation tasks complete
- architect_slice must support a type-schema mode returning field definitions for core types
- Auto-invoke architect_slice for type schemas before code generation tasks
- *... +11 more*

### COULD
- Add Diagram Generation as sub-capability of Documentation Tools
- Split COMP-8 into generator and diagrams sub-components
- Split COMP-8 into Behavior Doc Generation and General Documentation components
- Capture test-fail-fix iterations as linked sub-events
- Detect fix-rerun debug cycles and extract root cause as learning entry
- architect_log should auto-trigger when documentation files are created
- Documentation creation activities should be tagged with file paths and indexed separately
- Add dependency_matrix artifact type for coupling analysis

## Quality Gates (COMP-9) (54 requirements)

### MUST
- Validator must warn on leaf constraints without verifies relationships
- Use extensions dict not tags list for provenance storage
- Publish interface specifications for all public API functions (generate_manifest, group_modules, etc.)
- Models must include relationships, not just components
- Representativeness scores must be validated for sanity (0-100% range, no >100%)
- Models must have non-zero relationships to be considered valid
- Add representativeness metric combining confidence scores and file coverage ratios
- Model must capture relationships between confidence and coverage modules
- *... +3 more*

### SHOULD
- architect_validate should support an 'explain' mode that outputs scoring formula breakdown and check categories without 
- Models must have minimum relationship coverage proportional to component count
- architect_scan should support multi-repo scanning in a single invocation
- Research findings should be automatically logged via architect_log
- Auto-invoke architect_log on task start/completion when task ID pattern (e.g., C8) is detected
- Models must have minimum one relationship per component
- Auto-prompt architect_log after file creation/edit sequences
- architect_slice should be called before multi-file integration tasks
- *... +21 more*

### COULD
- architect_slice should extract dataclass schemas in structured format
- Auto-invoke architect_slice for coverage.py context before implementation edits
- Add coverage dimension registry capability to track dimensions 1-8+
- Add interface_spec artifact type for MCP tool contracts
- Clarify responsibility boundary between COMP-9 (Quality Gate Tools) and COMP-15 quality.py
- Add dry-run mode to architect_docs showing which artifacts have sufficient data
- Extract implicit tooling requirements from exploratory sessions
- Batch check results should auto-log to architect_log
- *... +6 more*

## Requirements Tools (COMP-10) (5 requirements)

### MUST
- Define sub-component decomposition for COMP-10 covering parser, LLM extractor, derivation, matcher capabilities
- Add relationships between COMP-10 and COMP-1, COMP-15 for tool registration and shared interfaces

### SHOULD
- Capture implicit requirements like 'all Tier 1 functions must emit metrics'
- architect_require tool must support batch requirement creation from task lists

### COULD
- Require minimum relationship coverage threshold

## Live Analysis (COMP-11) (7 requirements)

### MUST
- Model must maintain non-zero relationships between components

### SHOULD
- Populate relationships/edges between components based on interface derivation logic
- Agent should prompt architect_log after multi-file implementations
- architect_slice should support module-detail mode for dataclass inspection
- Compression ratio must stay below 50x threshold

### COULD
- Models must track field population status per component
- Enrichment pipeline stages should be explicitly modeled as sub-capabilities

## Runner (COMP-12) (27 requirements)

### MUST
- Relationships must be populated to define data/control flow between components
- Agent must call architect_slice before writing new modules to retrieve architecture context
- Agent must call architect_require to capture task requirements before implementation
- Agent must call architect_log after completing implementation tasks
- Model must decompose Runner component to expose LLM subsystem responsibilities
- Support custom system prompt injection via opencode.json or CLI flags
- Auto-register MCP servers on session startup
- OpencodeRunner should support initial context injection
- *... +4 more*

### SHOULD
- Add mock/test runner that bypasses external LLM calls
- Define relationships between CLI, runner, and orchestration components
- Auto-trigger architect_slice before file edits to provide architecture context
- Auto-trigger architect_check after commits to detect structural drift
- Components with multiple modules must define relationships showing internal call graphs
- Agent must call architect_slice before editing cross-module wiring
- Auto-suggest architect_scan when agent performs multiple raw file reads on a repository
- CI workflows must scan repo structure before generating workflow files

### COULD
- Add RegenLoop as distinct component or capability under CLI/runner
- Auto-trigger architect_log on implementation progress
- Extract file paths and change types from edit tool calls as structured metadata
- Log exploration activity automatically via architect_log when reading project files
- Detect and tag API surface changes distinctly from generic code edits
- Auto-log data discovery results as structured observations
- Add data-audit scan mode to discover non-code artifacts

## Telemetry (COMP-13) (30 requirements)

### MUST
- MCP tools must call drain_and_store after execution to persist telemetry
- TelemetryStore must accept both Path and string arguments
- Monitoring module must be a distinct component with relationship to package public API
- Add Monitoring capability under COMP-13 or as separate component

### SHOULD
- Add infrastructure_audit mode to architect_slice for cross-cutting concern discovery
- Support cross-cutting concerns in decomposition model
- Agent should automatically log research findings as observation entries
- Component specs must include interface and responsibility details, not just file counts
- Define cross-cutting concern representation for decorators like @monitored that span multiple components
- Add relationships between Telemetry component and all components using @monitored
- Support scoped directory-level scanning
- Auto-diff scan results against existing model to flag undocumented files
- *... +8 more*

### COULD
- Add monitoring coverage check to architect_check
- Agent should offer architectural context via architect_slice when detecting code exploration tasks
- Support external_dependencies field per component for resources like SQLite databases
- Support sub-capability decomposition within components
- Extract SQL DDL statements as structured schema metadata
- architect_log should auto-prompt after edit failures to capture root cause
- Extract edit/tool failures as child issues with file paths
- Add cross-cutting concern representation for decorators/instrumentation
- *... +2 more*

## MCP Server (COMP-15) (117 requirements)

### MUST
- architect_scan must integrate scan_all_languages() from architecture-model-standard to support multi-language repository
- architect_docs must support system_design and integration_flows doc types
- Relationships must be populated - 0 relationships at 15 entities provides no architectural value
- Models with 0 relationships should be flagged as incomplete
- Add enrichment pipeline for non-Python SourceGraph ingestion (dependency resolution, type inference, relationship extrac
- architect_slice must be called before editing existing files to load structural context
- Fix architecture-model-standard dependency to >=0.3.0
- Add or fix opencode.json manifest
- *... +7 more*

### SHOULD
- Auto-invoke architect_log after code modifications
- Pre-edit slice and post-edit check workflow
- Extract API mismatches as issue logs automatically
- Add relationship definitions between MCP tools and core pipeline modules
- architect_validate should auto-run after model type changes
- architect_slice should be called before implementing new tools to retrieve existing patterns
- COMP-15 must be decomposed into server framework and individual tool sub-components
- Decompose multi-area explorations into individual child logs
- *... +49 more*

### COULD
- architect_slice should be able to query cross-repo dependencies and external package architectures
- Extract numbered research questions as individual child log entries with per-question findings
- Add a quick repo exploration workflow combining scan and slice for tool architecture
- Extract algorithm/heuristic designs as tagged patterns during ingestion
- Auto-trigger architect_scan after new file creation
- Capture structured research summaries with per-file findings
- Extract structured test results (pass/fail counts, failure reasons) from conversation segments
- Auto-invoke architect_log during exploration phases
- *... +37 more*

## Artifacts (COMP-2) (55 requirements)

### MUST
- Agent must use MCP tools (architect_scan, architect_group, architect_extract, architect_check) instead of raw bash/Pytho
- Tool discoverability must be improved so agents naturally reach for MCP tools over bash
- Add export/serialization capability to component decomposition
- Models must include relationships/dependencies between components
- Create ConOps artifact documenting intended pipeline flow
- Support Interface Control Document (ICD) as a first-class artifact type

### SHOULD
- architect_slice should support a 'stats' mode returning component/relationship/behavior counts
- Support hierarchical component decomposition with parent-child relationships
- Model must represent dataclass hierarchy and field-level schema details
- Relationships must capture import/dependency chains between types.py and parser.py
- Enforce minimum relationship count per component
- Add relationships between MCP tools and core data model components
- Split COMP-2 into separate components for Manifest Generation (grouping/affinity) and Artifact Output
- architect_slice should support querying by module path to retrieve all relevant types and dependencies
- *... +22 more*

### COULD
- Document ModelMeta fields and extension points in interface_spec
- Support structured code analysis findings as a log subtype
- Add orchestration component to decomposition
- Add key_types or exports field per component listing major data structures that cross boundaries
- Split COMP-2 into Manifest Types and Orchestration/Enrichment subcomponents
- Flag and handle truncated conversation segments during ingestion
- Support multi-system linking for batch exploration logs
- Handle truncated assistant messages by reconstructing from tool calls
- *... +11 more*

## CLI Commands (COMP-3) (40 requirements)

### MUST
- launch.py must delegate to architect_scan and architect_slice MCP tools rather than reimplementing scan/slice logic
- No-subcommand invocation must trigger pre-flight orchestration sequence: scan → load model → slice → compute representat
- Interface specs must document function signatures for public APIs

### SHOULD
- Model must have minimum relationship density threshold
- Auto-suggest architect_scan when agent performs 3+ raw file reads on an unscanned repo
- architect_slice should support mode=component to extract module-level context
- Auto-invoke architect_log after multi-file edits
- Require minimum relationship count or flag model as incomplete
- Auto-invoke architect_slice before editing any component file to load context
- Auto-invoke architect_check after implementation tasks complete
- COMP-3 must be decomposed to separate calibration from other CLI commands
- *... +11 more*

### COULD
- Extract inline requirements from numbered goal lists
- Add interface_spec artifact type for function signatures and type schemas
- architect_slice should be auto-suggested when agent performs 4+ sequential file reads in same subsystem
- Add Compression Analysis capability to core component
- Split CLI and orchestration into separate components with defined interfaces
- Add per-component compression metrics and auto-slice thresholds
- Ingestion must detect and flag truncated messages
- Support 'research' log type for design exploration conversations
- *... +10 more*

## Requirements Library (COMP-4) (42 requirements)

### MUST
- Schema must explicitly support derives-from relationship type for constraint decomposition
- RelationType enum must include DERIVES_FROM and VERIFIES
- schema.json relationTypes must stay in sync with RelationType enum
- Models must have at least one relationship per component or fail validation
- Component schema must support optional pattern and contract fields

### SHOULD
- Core type definitions (Capability, Behavior, Component) must be decomposed as distinct capabilities with field-level doc
- Model must include interface_spec artifacts documenting dataclass field schemas
- Support hierarchical/nested entity types with parent-child relationships (sub-capabilities, sub-components, sub-behavior
- Preserve relationships even at high compression ratios
- Auto-prompt architect_require when task IDs (e.g., C1, C2) are referenced in conversation
- Schema component should be explicitly modeled with its own component entry and relationships to consumers
- Extract requirements from YAML/code specification blocks in user prompts
- Auto-invoke architect_log after code edits to record decisions
- *... +18 more*

### COULD
- Support multi-part queries as parent with child logs per sub-question
- architect_scan should support extracting enum values and dataclass fields from specific files
- Track test-fix cycles as structured iterations with pass/fail status
- Extract task ID patterns (C1-C8) and tag logs accordingly
- Extract task IDs (C1, C2) and link to parent workstream identifiers (WS-C)
- Separate multi-task conversations into distinct child logs per task ID
- Auto-invoke architect_slice before editing module files
- Split COMP-4 to separate core domain models from analysis logic
- *... +3 more*

## Resolution & Quality (COMP-5) (119 requirements)

### MUST
- Extract and preserve negative findings as distinct log entries
- architect tools must be invoked when fixing type mismatches that affect model correctness
- Define Behavior entity type and UC-N naming convention in schema
- Add 'contains' and 'triggers' as formal relationship types in schema
- Define Capability and Behavior as first-class model entities with realizes relationship type
- Model must have depends-on relationships populated to enable graph-theory metrics
- Confidence scoring must account for enrichment completeness from SourceGraph data
- Model must contain relationships between components
- *... +11 more*

### SHOULD
- Models must have a minimum relationship count relative to component count; zero relationships should trigger a completen
- COMP-5 must be decomposed into sub-components separating dependency resolution from system boundary detection
- Schema must support Decision and Constraint as first-class entity types beyond components
- COMP-5 must be decomposed to separate File Grouping, Manifest Resolution, and Component Assignment sub-components
- Auto-trigger architect_validate after schema/type file modifications
- architect_slice should support a 'types' mode that returns dataclass/enum field definitions for specified modules
- Model must retain relationships even at high compression ratios
- Interface specifications for core dataclasses (Behavior, Relationship, Status) must be documented as artifacts
- *... +57 more*

### COULD
- SystemScore dataclass and detect_systems() must be reflected in component spec for COMP-5
- Models must have non-zero relationships when multiple components exist
- Define decomposition rules specifying when and how entities should be broken into sub-entities
- Add ICD artifact documenting manifest-to-core-model data flow
- architect_log should be called automatically when new functions are added to track design decisions
- Edit error/retry sequences should be captured as distinct tracked events with root cause
- architect_validate must run after new module creation
- Split Resolution component into Grouping and Functional Block Assignment
- *... +27 more*

## Cross-System (12 requirements)

### SHOULD
- Model schema should support external_dependencies field to represent third-party packages
- Model should support cross-project dependency declarations
- Models with zero relationships should auto-infer from import analysis
- Model must include BaseEntity as a component with its field schema documented
- Parse test results from bash output into structured test_outcome field
- Support multi-repo tracking with per-repo outcome grouping
- Define minimum relationship coverage threshold

### COULD
- Support multi-system linking when conversation references multiple repositories
- Add public_api/exports field per component to track exported symbols
- Support cross-cutting concerns like monitoring/observability in schema
- Recognize test-fix-retest cycles as debugging iterations
- Detect API exploration intent and tag as api_discovery

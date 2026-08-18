---
document: Risk Assessment
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T20:07:47Z
generator_version: 0.3.0
model_hash: ceee27c08922
edition: 5
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 56/56 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Risk Assessment: System

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-DEP-src-mcp-COMP-1 | Dependency | HIGH | Quality has 13 dependents — single point of failure | Ensure thorough testing of Quality; consider interface abstraction |
| RISK-DEP-src-mcp-COMP-29 | Dependency | HIGH | Infrastructure has 12 dependents — single point of failure | Ensure thorough testing of Infrastructure; consider interface abstraction |
| RISK-DEP-src-mcp-COMP-7 | Dependency | MEDIUM | Diff has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-mcp-COMP-11 | Dependency | MEDIUM | Extract has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-mcp-COMP-22 | Dependency | MEDIUM | Require has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-1 | Dependency | MEDIUM | Bench has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-3 | Dependency | MEDIUM | Confidence has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-4 | Dependency | MEDIUM | Docs has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-5 | Dependency | MEDIUM | Docs Validator has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-6 | Dependency | MEDIUM | Extract has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-7 | Dependency | MEDIUM | Gap Analyzer has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-8 | Dependency | MEDIUM | Generate has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-9 | Dependency | MEDIUM | Launch has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-10 | Dependency | MEDIUM | Main has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-11 | Dependency | MEDIUM | Metrics has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-12 | Dependency | MEDIUM | Regen Loop has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-cli-COMP-13 | Dependency | MEDIUM | Infrastructure has 4 dependents | Monitor for breaking changes |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Quality | 27 |
| Slice | 26 |
| Bench | 11 |
| Extract | 11 |
| Generate | 11 |
| Regen Loop | 11 |
| Trace Requirements | 4 |

## Constraint Risks

*No constraints defined.*

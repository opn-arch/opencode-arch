---
document: Risk Assessment
system: Src (cli)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:40Z
generator_version: 0.3.0
model_hash: 4a18118f967e
edition: 13
---

> **Model Completeness: F (2%)**
> Some sections may be empty due to missing model entities.
> - 13/13 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Risk Assessment: Src (cli)

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-CAP-CAP-4 | Capability | HIGH | Capability 'Docs' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-10 | Capability | HIGH | Capability 'Main' has no realizing component | Allocate to component or remove if not needed |
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
| Bench | 11 |
| Extract | 11 |
| Generate | 11 |
| Regen Loop | 11 |

## Constraint Risks

*No constraints defined.*

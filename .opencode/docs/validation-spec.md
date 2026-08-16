# Validation Spec

> Source: `architecture_model.core.validator`

## Scoring Formula

```python
score = max(0, 100 - (error_count * 10) - (warning_count * 2))
```

- **Errors**: -10 points each
- **Warnings**: -2 points each
- **Info**: no penalty (advisory only)
- **Valid model**: `error_count == 0` (warnings acceptable)

## Severity Levels

| Severity | Impact | Meaning |
|----------|--------|---------|
| ERROR | -10 pts | Structural violation, model is invalid |
| WARNING | -2 pts | Degraded quality, should fix |
| INFO | 0 pts | Improvement opportunity |

## Validation Checks (execution order)

### 1. JSON Schema Validation (`JSON_SCHEMA_VIOLATION`)
- **Severity**: ERROR
- **Trigger**: `raw_dict` provided and fails Draft7 schema
- **Caps**: 10 schema errors max

### 2. ID Uniqueness (`DUPLICATE_ID`)
- **Severity**: ERROR
- **Check**: No duplicate IDs across all 16 entity types (actor, capability, behavior, interface, constraint, layer, component, system, data, event, resource, environment, quality_attribute, decision, lifecycle, external_system)

### 3. Referential Integrity (`DANGLING_REF`)
- **Severity**: WARNING
- **Check**: All `from_id`/`to_id` in relationships must exist as entities
- **Exceptions**: IDs ending in `-layer`, starting with `external-`, or matching short layer names (`web`, `services`, `data`, `pipeline`, `scheduling`)

### 4. Orphan Detection (`ORPHAN_BEHAVIOR`, `ORPHAN_COMPONENT`)
- **Severity**: INFO
- **Check**: ACTIVE behaviors/components with zero relationships
- **Scope**: Only behaviors and components (actors, layers, constraints may be standalone)

### 5. Status Consistency (`STATUS_MISMATCH`)
- **Severity**: WARNING
- **Check**: ACTIVE entity should not `depends-on` or `consumes` a PLANNED entity

### 6. Capability Realization (`UNREALIZED_CAPABILITY`)
- **Severity**: WARNING
- **Check**: Every ACTIVE capability must have at least one `realizes` relationship pointing to it

### 7. Meta Completeness (`MISSING_META`)
- **Severity**: ERROR for `project`/`schema_version`, WARNING for `source_artifacts`
- **Check**: Required meta fields are non-empty

### 8. v1.1 Semantics
- `DATA_MODEL_NO_FIELDS` (INFO): Data-model components without fields
- `STATE_UNREACHABLE` (WARNING): State-machine states with no incoming transitions

### 9. Regen Readiness
- `REGEN_UNREADY` (ERROR): Constant coverage < 30%
- `REGEN_PARTIAL` (WARNING): Constant coverage < 70%
- `REGEN_LOW_SIG_COVERAGE` (WARNING): Signature coverage < 50%
- **Only applies** to components with `test_contracts`

### 10. Domain Profile (`PROFILE_RULE`)
- **Severity**: WARNING
- **Check**: Conditional rules from loaded domain profile (e.g. `embedded`, `mechanical`)

### 11. Improvement Opportunities
- `IMPROVEMENT_NO_SIGNATURES` (INFO): No function signatures
- `IMPROVEMENT_NO_TEST_CONTRACTS` (INFO): Has signatures but no test contracts
- `IMPROVEMENT_NO_OBSERVABILITY` (INFO): Has both but no observability

### 12. Requirements Verification (`UNVERIFIED_CONSTRAINT`)
- **Severity**: WARNING
- **Check**: Leaf constraints (not parents via `derives-from`) must have a `verifies` edge

### 13. Dependency Cycles (`DEPENDENCY_CYCLE`)
- **Severity**: WARNING
- **Check**: DFS cycle detection in `depends-on` graph
- **Caps**: Reports max 5 cycles

### 14. Operational Fields
- `UNKNOWN_OPERATIONS_KEY` (WARNING): Unknown keys in `operations` dict
- `EXT_DEP_MISSING_NAME` (WARNING): External dependencies without `name`
- **Valid ops keys**: `startup_command`, `health_check`, `deployment_config`

## Lifecycle Gating

In `concept` lifecycle phase, issues with `UNVERIFIED` in the code are stripped from results.

## Strict Mode

When `strict=True`, all WARNINGs are promoted to ERRORs before returning.

## Side Effects

After all checks, `compute_model_confidence(model)` is called to update per-entity confidence scores.

## Issue Structure

```python
@dataclass
class ValidationIssue:
    severity: Severity      # ERROR | WARNING | INFO
    code: str              # e.g. "DUPLICATE_ID"
    message: str           # human-readable description
    entity_id: str | None  # affected entity
    context: str | None    # additional context
```

## API

```python
def validate_model(
    model: ArchitectureModel,
    strict: bool = False,
    raw_dict: dict | None = None,
) -> ValidationResult:
    ...

# ValidationResult properties:
result.score        # 0-100
result.is_valid     # True if error_count == 0
result.error_count
result.warning_count
result.info_count
result.summary()    # "Score: 85/100 | Errors: 0, Warnings: 7, Info: 3"
```

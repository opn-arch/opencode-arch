# Component: Resolution (COMP-5)

**Status:** Status.ACTIVE
**Description:** Source in src/opencode_arch/agent, src/opencode_arch/context, src/opencode_arch/mcp (6 files)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/regen/self_heal.py` | — | — |
| `src/opencode_arch/regen/spot_check.py` | — | — |
| `src/opencode_arch/agent/resolution.py` | — | — |
| `src/opencode_arch/mcp/quality.py` | — | — |
| `src/opencode_arch/context/formatter.py` | — | — |
| `src/opencode_arch/context/pipeline_bridge.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-9 (Quality Gate Tools) | uses | Quality Gate Tools imports from Resolution |

## Behaviors Realized

None

## Interface Dependencies

- **provides** `exposes_to_Tools` → COMP-1 (Extraction Tools) [estimate_regenerability, check_fidelity, with_quality, SessionAccumulator]

## Patterns

None

## Confidence

50%

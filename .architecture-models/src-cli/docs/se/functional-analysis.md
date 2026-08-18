---
document: Functional Analysis
system: Src (cli)
system_id: SYS-unknown
generated_at: 2026-08-18T20:07:49Z
generator_version: 0.3.0
model_hash: 4a18118f967e
edition: 3
---

> **Model Completeness: F (2%)**
> Some sections may be empty due to missing model entities.
> - 13/13 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Functional Analysis: Src (cli)

## Capability Inventory

| ID | Capability | Priority | Status | Description |
|----|-----------|----------|--------|-------------|
| CAP-1 | Bench | medium | ACTIVE | — |
| CAP-2 | Calibrate | medium | ACTIVE | — |
| CAP-3 | Confidence | medium | ACTIVE | — |
| CAP-4 | Docs | medium | ACTIVE | — |
| CAP-5 | Docs Validator | medium | ACTIVE | — |
| CAP-6 | Extract | medium | ACTIVE | — |
| CAP-7 | Gap Analyzer | medium | ACTIVE | — |
| CAP-8 | Generate | medium | ACTIVE | — |
| CAP-9 | Launch | medium | ACTIVE | — |
| CAP-10 | Main | medium | ACTIVE | — |
| CAP-11 | Metrics | medium | ACTIVE | — |
| CAP-12 | Regen Loop | medium | ACTIVE | — |
| CAP-13 | CLI Main | medium | ACTIVE | — |

## Functional Decomposition

```mermaid
graph TD
    CAP-1["Bench"]
    CAP-2["Calibrate"]
    CAP-3["Confidence"]
    CAP-4["Docs"]
    CAP-5["Docs Validator"]
    CAP-6["Extract"]
    CAP-7["Gap Analyzer"]
    CAP-8["Generate"]
    CAP-9["Launch"]
    CAP-10["Main"]
    CAP-11["Metrics"]
    CAP-12["Regen Loop"]
    CAP-13["CLI Main"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Bench | Bench (src-cli-COMP-1) | service |
| Calibrate | Calibrate (src-cli-COMP-2) | service |
| Confidence | Confidence (src-cli-COMP-3) | service |
| Docs | *unrealized* | — |
| Docs Validator | Docs (src-cli-COMP-4) | service |
| Docs Validator | Docs Validator (src-cli-COMP-5) | service |
| Extract | Extract (src-cli-COMP-6) | service |
| Gap Analyzer | Gap Analyzer (src-cli-COMP-7) | service |
| Generate | Generate (src-cli-COMP-8) | service |
| Launch | Launch (src-cli-COMP-9) | service |
| Main | *unrealized* | — |
| Metrics | Metrics (src-cli-COMP-11) | service |
| Regen Loop | Regen Loop (src-cli-COMP-12) | service |
| CLI Main | Main (src-cli-COMP-10) | service |

## Behavioral Coverage

Total behaviors: 1

**Untraced behaviors:** 1
- CLI: Main (BEH-1)

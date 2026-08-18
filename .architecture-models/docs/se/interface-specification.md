---
document: Interface Specification
system: opencode-arch
system_id: SYS-unknown
generated_at: 2026-08-17T18:14:32Z
generator_version: 0.3.0
model_hash: b8b11e54f9db
edition: 1
---

# Interface Specification: opencode-arch

## Interface Inventory

*No interfaces defined in the model.*

## Interface Details

*No interfaces to detail.*

## Component-Level Interfaces

### Extraction Tools (COMP-1)

| Name | Kind | Target | Signature |
|------|------|--------|-----------|
| exposes_to_Cli | provides | COMP-3 | `` |
| uses_Resolution | requires | COMP-5 | `` |
| uses_Cli | requires | COMP-3 | `` |
| uses_Requirements | requires | COMP-4 | `` |

### CLI Commands (COMP-3)

| Name | Kind | Target | Signature |
|------|------|--------|-----------|
| uses_Tools | requires | COMP-1 | `` |
| exposes_to_Tools | provides | COMP-1 | `` |

### Requirements (COMP-4)

| Name | Kind | Target | Signature |
|------|------|--------|-----------|
| exposes_to_Tools | provides | COMP-1 | `` |

### Resolution (COMP-5)

| Name | Kind | Target | Signature |
|------|------|--------|-----------|
| exposes_to_Tools | provides | COMP-1 | `` |


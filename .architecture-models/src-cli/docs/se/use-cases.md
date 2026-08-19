---
document: Use Cases
system: Src (cli)
system_id: SYS-unknown
generated_at: 2026-08-19T16:59:44Z
generator_version: 0.3.0
model_hash: b65cb1b8e8a2
edition: 6
---

> **Model Completeness: F (1%)**
> Some sections may be empty due to missing model entities.
> - 14/14 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Use Cases: Src (cli)

## Actor-Goal Matrix

| Actor | Goals |
|-------|-------|
| CLI User | — |

## Use Case Specifications

### UC: CLI: Main

**ID:** BEH-1
**Main Flow:**
  1. ArgumentParser
  2. add_subparsers
  3. add_parser
  4. add_argument
  5. parse_args

## Use Case Diagram

```mermaid
graph LR
    ACT-1(("CLI User"))
    BEH-1["CLI: Main"]
```

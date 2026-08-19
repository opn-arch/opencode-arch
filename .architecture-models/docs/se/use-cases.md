---
document: Use Cases
system: opencode-arch
system_id: SYS-unknown
generated_at: 2026-08-19T16:59:40Z
generator_version: 0.3.0
model_hash: f2b902537f3a
edition: 8
---

# Use Cases: opencode-arch
## Actor-Goal Matrix
| Actor | Goals |
|-------|-------|
| CLI User | Use opencode-arch effectively |
## Use Case Specifications
### UC: CLI: Run Benchmark

**ID:** BEH-1
**Main Flow:**
  1. ArgumentParser
  2. add_argument
  3. parse_args
  4. print
  5. run_benchmark

### UC: CLI: Benchmark Economy

**ID:** BEH-2
**Main Flow:**
  1. ArgumentParser
  2. add_argument
  3. parse_args
  4. run
  5. print_report

### UC: CLI: Main

**ID:** BEH-3
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
    BEH-1["CLI: Run Benchmark"]
    BEH-2["CLI: Benchmark Economy"]
    BEH-3["CLI: Main"]
```

---

---
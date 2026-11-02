---
name: generation
description: "Use when asked to generate code from an architecture model or run test-guided code generation against an openAG model"
---

# Test-Guided Code Generation

## Status: not available in openAG

<!-- legacy-ok:start -->
There is **no code-generation tool** in the current openAG toolset. The legacy
AMS `architect_generate` (and the `architect_scan` / `architect_slice` /
`architect_extract` flow it depended on) do **not** exist here. Do not attempt
to call them — they will fail.
<!-- legacy-ok:end -->

If a user asks to "generate code from the architecture model" or "make the code
pass the tests from the model", explain that openAG does not generate code. It
is an **analysis / modeling** toolset, not a codegen engine.

## What to do instead

Use the inspection tools to surface what the model says *should* exist, then
implement it yourself with normal editing + testing:

- `arch_pipeline(repo_path=...)` → write the model first (see the `extraction`
  skill for the full write-once-then-read workflow).
- `arch_frontier(repo_path=...)` → find candidate node ids (fall back to
  `arch_health` `worst_offenders` or `arch_decompose` if the frontier is empty).
- `arch_owed(repo_path=..., node_id=...)` → the attributes/promises a component
  still owes (intent, contract, produces, consumes, behavior, …).
- `arch_gaps(repo_path=..., node_id=...)` → typed G-DELIVERY gaps for a node.
- `arch_slice(repo_path=..., node_id=...)` → the entity-scoped sub-doc for
  context while you implement.

Then write and run tests with your normal tooling. openAG does not run the test
suite or emit code.

## Related

See the `extraction` skill for the canonical openAG model-building workflow and
the full `arch_*` tool reference.

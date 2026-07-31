# Full Behavioral Capture with System-of-Systems Decomposition

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the manifest scanner to completely capture function behavior (call order, control flow, data flow, guards) and integrate with the recursive decomposition system so large repos produce manageable per-block behavioral models with cross-block event chains at root level.

**Architecture:**
1. Extend `FunctionInfo` with 5 behavioral fields
2. New `behavior.py` module with AST body walkers
3. Scanner integration — `scan_file()` populates behavioral fields (works at every level: flat and recursive)
4. `generate_recursive_manifests()` automatically benefits (it calls `scan_file()`)
5. New `chains.py` builds event chains per-block (intra) and cross-block (inter)
6. Hierarchical representativeness: root checks cross-block, per-block checks intra-block
7. `architect_check` enhanced to run hierarchical verification

**Key Design Principle:** The scanner produces behavioral data per-file. The decomposition system scopes it per-block. The agent works one block at a time within token budget.

**Tech Stack:** Python 3.11+, `ast` module, architecture-model-standard

---

## Phase A: Scanner Extension (Tasks 1-5)

These tasks extend the AST scanner. Since `generate_recursive_manifests()` calls `scan_file()` internally, behavioral data flows to per-block manifests automatically.

### Task 1: Extend FunctionInfo with behavioral fields

**Files:**
- Modify: `src/architecture_model/manifest/types.py`
- Test: `tests/test_behavioral_fields.py`

**Step 1: Write the failing test**

```python
"""Tests for new behavioral fields on FunctionInfo."""
import pytest
from architecture_model.manifest.types import FunctionInfo


def test_function_info_has_behavioral_fields():
    fi = FunctionInfo(
        name="process", signature="(x: int) -> str",
        call_order=["validate", "transform", "save"],
        control_flow=["try_except", "for_loop"],
        data_in=["int"],
        data_out="str",
        guards=["assert x > 0"],
    )
    assert fi.call_order == ["validate", "transform", "save"]
    assert fi.control_flow == ["try_except", "for_loop"]
    assert fi.data_in == ["int"]
    assert fi.data_out == "str"
    assert fi.guards == ["assert x > 0"]


def test_function_info_defaults_empty():
    fi = FunctionInfo(name="simple", signature="() -> None")
    assert fi.call_order == []
    assert fi.control_flow == []
    assert fi.data_in == []
    assert fi.data_out == ""
    assert fi.guards == []
```

**Step 2:** Run test → FAIL (fields don't exist)

**Step 3: Add fields to FunctionInfo**

```python
@dataclass
class FunctionInfo:
    """A public function extracted from AST."""
    name: str
    signature: str
    calls: list[str] = field(default_factory=list)
    docstring: str | None = None
    raises: list[str] = field(default_factory=list)
    # Behavioral fields (populated by behavior.py extractors)
    call_order: list[str] = field(default_factory=list)     # ordered call sequence
    control_flow: list[str] = field(default_factory=list)   # structural patterns
    data_in: list[str] = field(default_factory=list)        # parameter type annotations
    data_out: str = ""                                       # return type annotation
    guards: list[str] = field(default_factory=list)         # preconditions/assertions
```

**Step 4:** Run test → PASS, then full suite → 660+ passed

**Step 5:** Commit: `feat: add behavioral fields to FunctionInfo`

---

### Task 2: Implement call_order extractor

**Files:**
- Create: `src/architecture_model/manifest/behavior.py`
- Test: `tests/test_behavior_extraction.py`

**Step 1: Write failing tests**

```python
"""Tests for behavioral extraction from function bodies."""
import ast
import pytest
from architecture_model.manifest.behavior import extract_call_order, extract_control_flow, extract_guards


class TestCallOrder:
    def test_simple_sequence(self):
        code = 'def f(x):\n    validate(x)\n    result = transform(x)\n    save(result)\n    return result\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["validate", "transform", "save"]

    def test_method_calls(self):
        code = 'def run(self):\n    self.setup()\n    data = self.fetch()\n    self.process(data)\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["self.setup", "self.fetch", "self.process"]

    def test_nested_calls_innermost_first(self):
        code = 'def f(x):\n    return save(transform(validate(x)))\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["validate", "transform", "save"]

    def test_conditional_calls_all_branches(self):
        code = 'def f(x):\n    check(x)\n    if x > 0:\n        positive(x)\n    else:\n        negative(x)\n    finish()\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["check", "positive", "negative", "finish"]

    def test_no_calls_empty(self):
        code = 'def f():\n    return 1 + 2\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == []
```

**Step 2:** FAIL (module doesn't exist)

**Step 3:** Create `behavior.py` with `extract_call_order()`:
- Walk function body in execution order (top-to-bottom, depth-first into expressions)
- For nested calls: yield innermost first (evaluation order)
- Filter out builtins (print, len, str, int, etc.)
- Handle `self.method()` as `"self.method"`

**Step 4:** PASS

**Step 5:** Commit: `feat: call_order extractor — ordered call sequence from function bodies`

---

### Task 3: Implement control_flow extractor

**Files:**
- Modify: `src/architecture_model/manifest/behavior.py`
- Test: `tests/test_behavior_extraction.py`

**Patterns to detect:**
- `try_except` — error handling
- `while_loop` — indefinite iteration
- `for_loop` — definite iteration
- `async_for` — async iteration
- `if_chain` — 3+ branches (if/elif/elif...)
- `with_context` — context manager
- `async_with` — async context manager
- `generator` — yield/yield from
- `match_case` — pattern matching (3.10+)
- `recursion` — function calls itself

**Implementation:** Single pass `ast.walk(func_node)`, classify each node type, deduplicate.

**Commit:** `feat: control_flow extractor — detect structural patterns`

---

### Task 4: Implement guards extractor

**Files:**
- Modify: `src/architecture_model/manifest/behavior.py`
- Test: `tests/test_behavior_extraction.py`

**Guards detected (first 6 statements of function body only):**
- `assert <condition>` → `"assert <condition_text>"`
- `if <cond>: raise <Exc>` → `"raise <Exc> if <cond>"`
- `if <cond>: return <val>` (early return) → `"return <val> if <cond>"`

**Commit:** `feat: guards extractor — preconditions from function bodies`

---

### Task 5: Integrate into scanner

**Files:**
- Modify: `src/architecture_model/manifest/scanner.py`
- Test: `tests/test_scanner_behavioral.py`

**What to do:**
1. Import `extract_call_order`, `extract_control_flow`, `extract_guards` from `behavior.py`
2. In `_extract_public_functions()` — after building each `FunctionInfo`, call the extractors on the AST node
3. Add `_extract_data_in(func_node)` and `_extract_data_out(func_node)` helpers
4. Same for class `method_details` — enrich each method's `FunctionInfo`

**Critical insight:** Since `scan_file()` is called by both `generate_manifest()` (flat) and `generate_recursive_manifests()` (per-block), this ONE integration point gives us behavioral data at ALL levels automatically.

**Tests:** Verify `scan_file()` produces `call_order`, `control_flow`, `guards`, `data_in`, `data_out` on real code.

**Commit:** `feat: integrate behavioral extraction into scan_file`

---

## Phase B: Hierarchical Event Chains (Tasks 6-7)

These tasks build cross-component chains scoped by block level.

### Task 6: Event chains with block scoping

**Files:**
- Create: `src/architecture_model/manifest/chains.py`
- Test: `tests/test_event_chains.py`

**Key data structure:**

```python
@dataclass
class EventChain:
    trigger: str                        # "Component.function"
    steps: list[str]                    # ["Comp.func", "Comp2.func2", ...]
    components_involved: list[str]      # unique component names in chain
    scope: str = "intra"                # "intra" (within block) or "cross" (spans blocks)
    block_id: str = ""                  # which block this chain belongs to (if intra)
```

**Two-level chain building:**

```python
def build_block_chains(
    block_manifest: Manifest,           # per-block manifest from recursive scan
    groups: list[ModuleGroup],          # grouping within this block
    block_id: str,
) -> list[EventChain]:
    """Build intra-block event chains (all within one F-block)."""
    # Trace call_order within block's modules only
    # All chains get scope="intra", block_id=block_id


def build_cross_block_chains(
    recursive_manifests: dict[str, RecursiveManifest],
    block_groups: dict[str, list[ModuleGroup]],  # per-block groupings
) -> list[EventChain]:
    """Build cross-block event chains (spanning 2+ F-blocks).
    
    Uses block_dependencies from recursive manifests to identify
    cross-boundary call paths. These go in the ROOT model only.
    """
    # Trace call_order where the target resolves to a different block
    # All chains get scope="cross"
```

**Why this matters for token budget:**
- Agent working on F1 only sees F1's intra-block chains (~10-20 chains)
- Agent working on root model sees cross-block chains (~5-10 chains)
- Never sees the full 100+ chain flat list

**Tests:**
1. Simple intra-block chain (all within one component group)
2. Cross-block chain (call from F1 module resolves to F2 module)
3. No cross-block chains when everything is internal

**Commit:** `feat: hierarchical event chains — intra-block and cross-block scoping`

---

### Task 7: Integrate chains into recursive manifests

**Files:**
- Modify: `src/architecture_model/manifest/recursive.py`
- Modify: `src/architecture_model/manifest/types.py` (add chains to RecursiveManifest)
- Test: `tests/test_recursive_chains.py`

**Changes to RecursiveManifest:**

```python
@dataclass
class RecursiveManifest:
    block_id: str
    block_name: str
    parent_model: str
    component_id: str
    manifest: Manifest
    children: dict[str, 'RecursiveManifest'] = field(default_factory=dict)
    block_dependencies: list[str] = field(default_factory=list)
    # NEW: behavioral data
    intra_chains: list[EventChain] = field(default_factory=list)  # chains within this block
```

**Changes to `generate_recursive_manifests()`:**
After generating each block's manifest:
1. Run `group_modules()` on the block's modules
2. Run `build_block_chains()` to get intra-block chains
3. Store in `RecursiveManifest.intra_chains`

After all blocks processed:
- Run `build_cross_block_chains()` for root-level chains
- Return cross-block chains separately (or store in a top-level field)

**Commit:** `feat: recursive manifests include intra-block event chains`

---

## Phase C: Hierarchical Representativeness (Tasks 8-9)

### Task 8: Hierarchical representativeness check

**Files:**
- Modify: `src/architecture_model/core/representativeness.py`
- Test: `tests/test_representativeness.py`

**New function:**

```python
@dataclass
class HierarchicalRepresentativenessResult:
    root: RepresentativenessResult                    # root model scores
    blocks: dict[str, RepresentativenessResult]       # per-block scores
    overall: float                                     # weighted average


def compute_hierarchical_representativeness(
    root_model: ArchitectureModel,
    sub_models: dict[str, ArchitectureModel],         # block_id -> sub-model
    recursive_manifests: dict[str, RecursiveManifest],
    cross_block_chains: list[EventChain],
) -> HierarchicalRepresentativenessResult:
    """Verify representativeness at every level of decomposition.
    
    Root level checks:
    - All blocks represented as components/systems
    - Cross-block relationships match cross-block import deps
    - Cross-block event chains captured in root behaviors
    
    Block level checks (per block):
    - File coverage within the block
    - Relationship accuracy within the block
    - Boundary coherence within the block
    - Behavioral coverage (complex functions have behaviors)
    - Intra-block event chains captured
    """
```

**Scoring:**
- Root: (block_coverage + cross_relationship_accuracy + cross_chain_coverage) / 3
- Per-block: (file_coverage + relationship_accuracy + boundary_coherence + behavioral_coverage) / 4
- Overall: (root_score + avg(block_scores)) / 2

**Target: 100% at every level.**

**Commit:** `feat: hierarchical representativeness — verify at root and per-block levels`

---

### Task 9: Update architect_check for hierarchical mode

**Files:**
- Modify: `src/opencode_arch/mcp/tools/check.py`
- Test: `tests/test_check_tool.py`

**Enhanced `architect_check`:**

When the repo has `.architecture-models/` directory (decomposed), run hierarchical check:
```python
async def check_representativeness(repo_path: str, model_yaml: str) -> dict:
    # If decomposed (has recursive manifests):
    #   Run hierarchical check → return per-block scores + root scores
    # If flat (no blocks):
    #   Run flat check (existing behavior)
```

**Output format (hierarchical mode):**
```json
{
  "mode": "hierarchical",
  "root": {"file_coverage": 100, "relationship_accuracy": 100, "behavioral_coverage": 80},
  "blocks": {
    "F1": {"file_coverage": 100, "relationship_accuracy": 100, "boundary_coherence": 95, "behavioral_coverage": 90},
    "F2": {"file_coverage": 100, ...}
  },
  "cross_block_chains": 5,
  "overall": 95.0,
  "uncovered_files": [],
  "uncaptured_behaviors": ["retry_with_backoff"]
}
```

**Commit:** `feat: architect_check supports hierarchical mode for decomposed repos`

---

## Phase D: Integration & Verification (Tasks 10-11)

### Task 10: Pipeline integration — from_scratch with behavior

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py`
- Test: `tests/test_pipeline_behavioral.py`

**Enhance `run_pipeline(from_scratch=True)`:**

Current: bootstraps model from manifest → enriches structurally.

New: bootstraps model → enriches structurally → enriches behaviorally → builds chains → verifies representativeness.

```python
if from_scratch:
    # 1. Generate flat manifest (now includes behavioral data)
    flat_manifest = generate_manifest(project_root)
    
    # 2. Group into components
    components = create_components_from_manifest(flat_manifest)
    
    # 3. Build model with relationships from interfaces
    model = bootstrap_model(components, flat_manifest.interfaces)
    
    # 4. Enrich structurally
    enrich_from_manifest(model, flat_manifest)
    
    # 5. Build event chains
    groups = group_modules(flat_manifest.modules, flat_manifest.interfaces)
    chains = build_block_chains(flat_manifest, groups, block_id="root")
    
    # 6. Add behaviors from chains
    enrich_behaviors_from_chains(model, chains)
    
    # 7. Verify representativeness
    rep = compute_representativeness(model, flat_manifest.modules, flat_manifest.interfaces)
    logger.info(f"Representativeness: {rep.overall:.1f}%")
    
    # 8. Save
    save_model(model, model_path)
```

**Commit:** `feat: pipeline from_scratch includes behavioral enrichment and chain building`

---

### Task 11: End-to-end integration test

**Files:**
- Create: `tests/test_behavioral_e2e.py`

**Tests:**

```python
class TestBehavioralEndToEnd:
    def test_scan_produces_behavioral_data_on_self(self):
        """architecture-model-standard scan includes call_order/control_flow."""
        manifest = generate_manifest(SELF_ROOT)
        funcs_with_calls = sum(1 for m in manifest.modules for f in m.functions if f.call_order)
        funcs_with_flow = sum(1 for m in manifest.modules for f in m.functions if f.control_flow)
        assert funcs_with_calls > 20
        assert funcs_with_flow > 10

    def test_recursive_manifests_have_chains(self):
        """Per-block recursive manifests include intra-block chains."""
        manifests = generate_recursive_manifests(SELF_ROOT)
        total_chains = sum(len(rm.intra_chains) for rm in manifests.values())
        assert total_chains > 5

    def test_from_scratch_pipeline_with_behavior(self):
        """from_scratch pipeline produces model with behaviors."""
        result = run_pipeline(SELF_ROOT, from_scratch=True)
        # Model should have behavioral data
        model = load_model(SELF_ROOT / ".architecture-model-extracted.yaml")
        assert len(model.entities.behaviors) > 0

    def test_hierarchical_representativeness_above_80(self):
        """Full hierarchical check scores above 80%."""
        # Run pipeline, then check
        ...
        assert result.overall >= 80.0
```

**Commit:** `test: end-to-end behavioral capture integration`

---

## Token Budget Analysis

After implementation, agent workflow for a large repo:

| Step | Agent action | Tokens consumed |
|------|-------------|----------------|
| 1 | `architect_scan(repo)` | ~500 (metrics + suggested_components) |
| 2 | `architect_group(repo)` | ~300 (group names + file counts) |
| 3 | `architect_slice(repo, focus="F1")` | ~4000 (F1 components + intra-chains) |
| 4 | Extract F1 sub-model YAML | Agent produces ~1000 tokens |
| 5 | `architect_check(repo, model)` | ~200 (scores + issues) |
| 6 | Repeat 3-5 for F2, F3... | ~5000 per block |
| 7 | `architect_slice(repo, focus="all")` | ~2000 (root: cross-block only) |
| 8 | Extract root model | ~500 |
| 9 | Final `architect_check` | ~200 (hierarchical) |

**Total for a 5-block repo: ~30K tokens** (vs. unbounded without decomposition)

---

## Execution Order

```
Phase A (scanner):  Task 1 → 2 → 3 → 4 → 5 (sequential, each builds on previous)
Phase B (chains):   Task 6 → 7 (depends on Phase A)
Phase C (repr):     Task 8 → 9 (depends on Phase B)
Phase D (pipeline): Task 10 → 11 (depends on all above)
```

All in `architecture-model-standard` except Task 9 (opencode-arch).

## Verification Commands

```bash
# After Phase A (Task 5):
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.manifest.generator import generate_manifest
m = generate_manifest(Path('/Users/baigm2/Documents/Projects/architecture-model-standard'))
with_calls = sum(1 for mod in m.modules for f in mod.functions if f.call_order)
with_flow = sum(1 for mod in m.modules for f in m.functions if f.control_flow)
with_guards = sum(1 for mod in m.modules for f in m.functions if f.guards)
print(f'call_order: {with_calls} functions')
print(f'control_flow: {with_flow} functions')
print(f'guards: {with_guards} functions')
"

# After Phase B (Task 7):
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.manifest.recursive import generate_recursive_manifests
rms = generate_recursive_manifests(Path('/Users/baigm2/Documents/Projects/architecture-model-standard'))
for block_id, rm in rms.items():
    print(f'{block_id} ({rm.block_name}): {len(rm.intra_chains)} intra-chains')
"

# After Phase C (Task 9):
/opt/anaconda3/bin/python -c "
import asyncio
from opencode_arch.mcp.tools.check import check_representativeness
# ... run hierarchical check
"

# Full suite:
/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -q
```

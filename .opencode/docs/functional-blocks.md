# Functional Blocks (F-blocks / S-blocks)

## What Are They?

Functional blocks are the top-level decomposition units of a codebase. They represent coherent subsystems — groups of files that serve a common architectural purpose.

In the codebase they appear as:
- **Config**: `FunctionalBlockConfig` in `architecture_model.config.schema`
- **Model**: `source_block` field on `Component` entities
- **IDs**: `S1`, `S2`, ... `S0` (shared/fallback)

## Terminology

| Term | Meaning |
|------|---------|
| **Functional block** | Config-level concept: a declared subsystem |
| **Source block (S-block)** | Same thing — the ID prefix `S` reflects "source" grouping |
| **F-block** | Legacy name (older docs use `F1`, `F2`; newer code uses `S1`, `S2`) |

## Where They Come From

### 1. Explicit Configuration (`.architecture-model.yaml`)

```yaml
functional_blocks:
  S1:
    name: "Pipeline"
    dirs: ["src/architecture_model/pipeline"]
    files: ["src/architecture_model/pipeline/observe.py", ...]
    description_source: "Extraction pipeline stages"
  S2:
    name: "Core"
    dirs: ["src/architecture_model/core"]
    ...
```

### 2. Auto-Discovery (`config/loader.py:_discover_functional_blocks`)

When no explicit config exists, blocks are auto-discovered:

1. **Find source root** — deepest package with subpackages (`src/<pkg>/`, `<pkg>/`, `lib/<pkg>/`)
2. **Each subdirectory** with `.py` files becomes an S-block
3. **Names** derived from directory name (title-cased, underscores→spaces)
4. **Description** from `__init__.py` docstring
5. **Sub-blocks** discovered recursively from sub-directories

**Fallback**: If no clear package structure, top-level directories become blocks.

```python
# Auto-discovery produces:
FunctionalBlockConfig(
    id="S1",
    name="Pipeline",
    dirs=["src/architecture_model/pipeline"],
    files=["src/architecture_model/pipeline/observe.py", ...],
    description_source="auto-discovered from src/architecture_model/pipeline/",
    sub_blocks=[...],
)
```

### 3. Runtime Generation (`manifest/grouping.py:auto_source_blocks`)

When the pipeline runs without config, `group_modules()` clusters files by import affinity, then `auto_source_blocks()` converts groups to S-block config:

```python
def auto_source_blocks(groups: list[ModuleGroup], threshold: int = 3) -> dict:
    # Groups with >= threshold files → individual S-block
    # Smaller groups → merged into "S0" (Shared)
    # Flat-repo fallback: if ALL groups < threshold, each gets own S-block
```

## Data Structure

```python
@dataclass
class FunctionalBlockConfig:
    id: str                          # "S1", "S2", etc.
    name: str                        # "Pipeline", "Core"
    dirs: list[str]                  # directories owned
    files: list[str]                 # specific files owned
    description_source: str          # docstring or auto-discovery note
    sub_blocks: list[SubBlockConfig] # nested decomposition
    exclude: list[str]               # glob patterns to exclude
    recursive: bool                  # include subdirs recursively

@dataclass
class SubBlockConfig:
    id: str
    name: str
    files: list[str]
    dirs: list[str]
    description: str
    sub_blocks: list[SubBlockConfig]  # recursive nesting
```

## How They Become `source_block` in the Model

### During Component Creation

When components are created from manifest groups (`create_components_from_manifest`):

```python
comp = Component(
    id=f"COMP-{idx}",
    name=group.name,
    status="ACTIVE",
    files=group.modules,
    source_block=block_id,  # ← S-block assignment
)
```

### During Pipeline Allocate Stage

The allocate stage uses `config.source_block_dir_map` to map files to blocks:

```python
# config.source_block_dir_map produces:
# {"src/pipeline": "S1", "src/core": "S2", "src/docs": "S3"}
```

Files are matched by directory prefix to determine which S-block they belong to.

## Config Properties

`ProjectConfig` provides convenience accessors:

```python
config.source_block_dir_map  # {"dir/path": "S1", ...} for file→block lookup
config.source_block_dict     # {"S1": {"name": ..., "dirs": ..., "files": ...}}
config.functional_blocks     # list[FunctionalBlockConfig]
```

## Lifecycle

```
Config/Auto-Discovery → FunctionalBlockConfig
                            ↓
                    Pipeline Allocate Stage
                            ↓
                    Component.source_block = "S1"
                            ↓
                    Model validation / decompose
                            ↓
                    Per-block sub-models (.architecture-models/)
                            ↓
                    Per-block manifests (.architecture/manifests/)
```

## Key Behaviors

- **Merge rule**: If config has `functional_blocks`, those are used; otherwise auto-discovery runs
- **Threshold**: Groups need ≥3 files to become standalone S-blocks (configurable)
- **Fallback**: Small groups merge into `S0` ("Shared")
- **Flat repos**: If all groups are tiny, each gets its own block anyway
- **Sub-blocks**: Provide finer granularity within an S-block without splitting it

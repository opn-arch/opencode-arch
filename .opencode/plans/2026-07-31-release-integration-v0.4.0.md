# Release Integration Plan — v0.4.0

## Goal
Ship v0.4.0 of both `architecture-model-standard` and `opencode-arch` with module grouping, expanded patterns, and the new `architect_group` MCP tool.

## Phase 1: Harden architecture-model-standard

### 1.1 Fix pyproject.toml version
- File: `pyproject.toml` line 7
- Change: `version = "0.3.0"` → `version = "0.4.0"`

### 1.2 Export grouping from manifest/__init__.py
- File: `src/architecture_model/manifest/__init__.py`
- Add import: `from architecture_model.manifest.grouping import group_modules, create_components_from_manifest, ModuleGroup`
- Add to `__all__`: `"group_modules"`, `"create_components_from_manifest"`, `"ModuleGroup"`

### 1.3 Export run_pipeline from orchestration/__init__.py
- File: `src/architecture_model/orchestration/__init__.py`
- Add import: `from architecture_model.orchestration.pipeline import run_pipeline`
- Add `"run_pipeline"` to `__all__`

### 1.4 Add grouping + run_pipeline to top-level __init__.py
- File: `src/architecture_model/__init__.py`
- Add import: `from architecture_model.manifest.grouping import group_modules, create_components_from_manifest, ModuleGroup`
- Add to `__all__`: `"group_modules"`, `"create_components_from_manifest"`, `"ModuleGroup"`
- Note: `run_pipeline` is already imported and exported here

### 1.5 Add from_scratch mode to run_pipeline
- File: `src/architecture_model/orchestration/pipeline.py`
- Add parameter: `from_scratch: bool = False`
- When `from_scratch=True` and no model exists: use `create_components_from_manifest()` to bootstrap a model, then run enrichment
- Write test in `tests/test_pipeline_from_scratch.py`

### 1.6 Add docstrings to grouping.py
- File: `src/architecture_model/manifest/grouping.py`
- Add module docstring, function docstrings with Args/Returns

### 1.7 Full test suite pass
- Command: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
- Expected: 648+ tests passing, 0 failures

## Phase 2: New architect_group MCP Tool (opencode-arch)

### 2.1 Create mcp/tools/group.py
- File: `src/opencode_arch/mcp/tools/group.py`
- Function: `async def group_repository(repo_path: str, target_groups: int = 0) -> dict`
- Logic:
  1. `generate_manifest(Path(repo_path))`
  2. `group_modules(manifest, target=target_groups)`
  3. Return `{groups: [{name, files, pattern, locked}], total_modules, total_groups}`
- Write test: `tests/test_group_tool.py`

### 2.2 Register architect_group in server.py
- File: `src/opencode_arch/mcp/server.py`
- Add import and register the tool with FastMCP

### 2.3 Enhance scan_repository with suggested_components
- File: `src/opencode_arch/mcp/tools/scan.py`
- After scanning, also run `group_modules()` and include `suggested_components` in output
- This gives the agent grouping suggestions alongside the raw scan

### 2.4 Enhance slice_context fallback with grouped context
- File: `src/opencode_arch/mcp/tools/slice.py`
- In the fallback path (no model exists): use `group_modules()` + `create_components_from_manifest()` for richer context
- Include component names and patterns in the compact YAML output

### 2.5 Update extraction skill
- File: `skills/extraction/SKILL.md`
- Add `architect_group` to the workflow (after scan, before extraction)
- Explain that grouping provides suggested component boundaries

## Phase 3: Harden opencode-arch

### 3.1 Fix versions to 0.4.0
- File: `src/opencode_arch/__init__.py` — change `__version__` to `"0.4.0"`
- File: `pyproject.toml` — change version to `"0.4.0"`

### 3.2 Fix dependency
- File: `pyproject.toml`
- Change: `architecture-model-standard>=0.1.0` → `architecture-model-standard>=0.4.0`

### 3.3 Create opencode.json
- File: `opencode.json` (project root)
- MCP extension manifest declaring 6 tools: scan, slice, validate, extract, generate, group
- Include tool descriptions, parameter schemas

### 3.4 Verify telemetry module
- Command: `/opt/anaconda3/bin/python -c "from opencode_arch.telemetry.store import TelemetryStore; from opencode_arch.telemetry.recorder import record_invocation; print('OK')"`

### 3.5 Verify extract subpackage
- Command: `/opt/anaconda3/bin/python -c "from opencode_arch.extract.from_code import extract_from_code; print('OK')"`

### 3.6 Update CONTEXT.md
- Add `architect_group` tool description
- Update test count
- Update version references
- Add grouping to key APIs section

### 3.7 Full test suite pass
- Command: `/opt/anaconda3/bin/python -m pytest tests/ -v`
- Note pre-existing failures in test_scan.py, test_extract_from_code.py, test_docs_cli.py, test_integration.py

## Phase 4: Verification

### 4.1 Integration test: scan → group → validate → extract
- File: `tests/test_full_pipeline_integration.py`
- Test the full MCP tool flow: scan a test repo, group it, produce model YAML, validate, extract

### 4.2 MCP server smoke test
- Command: `/opt/anaconda3/bin/python -c "from opencode_arch.mcp.server import mcp; print(f'Tools: {len(mcp._tool_manager._tools)}')"` (or equivalent)
- Verify all 6 tools registered

### 4.3 Tag both repos v0.4.0
- `architecture-model-standard`: `git tag v0.4.0`
- `opencode-arch`: `git tag v0.4.0`
- Only after all tests pass

## Execution Order
Phase 1 → `pip install -e .` (arch-std) → Phase 2 + 3 (parallel where possible) → Phase 4

## Verification Commands
```bash
# Phase 1
cd /Users/baigm2/Documents/Projects/architecture-model-standard
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py

# Phase 2+3
cd /Users/baigm2/Documents/Projects/opencode-arch
/opt/anaconda3/bin/python -m pytest tests/ -v

# Smoke test
/opt/anaconda3/bin/python -c "from architecture_model import group_modules, create_components_from_manifest, ModuleGroup; print('arch-std exports OK')"
/opt/anaconda3/bin/python -c "from opencode_arch.mcp.tools.group import group_repository; print('group tool OK')"
```

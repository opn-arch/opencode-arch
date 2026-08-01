# Multi-Tool Documentation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `.cursorrules` template and MCP setup guides so Cursor, Cline, and Continue users can use architecture-model-standard with zero friction.

**Architecture:** Docs-only deliverable. Create templates in `docs/integrations/` that users copy into their projects. The `.cursorrules` file teaches Cursor's agent about the architecture model. MCP guides show how to configure each tool to use the opencode-arch MCP server.

**Tech Stack:** Markdown, YAML config examples

**Repo:** `architecture-model-standard` @ `/Users/baigm2/Documents/Projects/architecture-model-standard/`

---

### Task 1: Create .cursorrules template

**Files:**
- Create: `docs/integrations/cursorrules-template.md`
- Create: `docs/integrations/.cursorrules`

**Step 1: Write .cursorrules**

```markdown
# Architecture Model Rules

This project uses architecture-model-standard for structural documentation.

## Key Files
- `.architecture-model.yaml` — Project configuration (layers, functional blocks)
- `.architecture-model-extracted.yaml` — Full architecture model (entities + relationships)
- `.architecture-models/` — Per-block manifests and generated docs
- `.architecture-models/docs/` — Generated documentation (component specs, ICD, health report)

## How to Use

### Before making changes:
1. Read `.architecture-models/docs/README.md` for project overview
2. Check the relevant component spec in `.architecture-models/docs/components/`
3. Review the dependency matrix to understand coupling

### When adding new features:
1. Identify which functional block (F-block) the feature belongs to
2. Check `.architecture-model.yaml` for block boundaries
3. Keep dependencies flowing downward through layers (see `layers:` in config)

### Architecture constraints:
- Components in higher layers should not depend on lower layers
- Each F-block should be independently comprehensible
- Cross-block dependencies indicate coupling — minimize them

## Model Schema (for reference)
```yaml
entities:
  components:
    - id: COMP-1
      name: ComponentName
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: CapabilityName
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
```

## Relationship types: realizes, uses, constrains, contains, triggers, depends_on, implements, exposes
```

**Step 2: Write the guide doc**

Create `docs/integrations/cursorrules-template.md` explaining how to use it:

```markdown
# Using Architecture Model with Cursor

## Setup

1. Copy the `.cursorrules` file to your project root:
   ```bash
   cp docs/integrations/.cursorrules /path/to/your/project/.cursorrules
   ```

2. (Optional) Run the architecture model pipeline first:
   ```bash
   architecture-model init /path/to/your/project
   ```

3. Cursor will now read the `.cursorrules` file and understand your project's architecture.

## What this gives you

- Cursor's agent will check component specs before making changes
- It will respect layer boundaries and dependency directions
- It will identify which F-block a change belongs to
- It understands the model schema for updating the architecture

## Customization

Edit `.cursorrules` to add project-specific rules:
- Add naming conventions
- Specify which directories map to which layers
- Add testing requirements per component
```

**Step 3: Commit**

```bash
git add docs/integrations/
git commit -m "docs: add .cursorrules template for Cursor integration"
```

---

### Task 2: MCP setup guide for Cursor

**Files:**
- Create: `docs/integrations/cursor-mcp.md`

**Step 1: Write guide**

```markdown
# Architecture Model MCP Server — Cursor Setup

## Prerequisites

```bash
pip install opencode-arch
```

## Configuration

Add to your Cursor MCP settings (`.cursor/mcp.json` in project root or global settings):

```json
{
  "mcpServers": {
    "arch-model": {
      "command": "python",
      "args": ["-m", "opencode_arch.mcp.server"],
      "env": {}
    }
  }
}
```

## Available Tools

Once configured, Cursor's agent can use these tools:

| Tool | Purpose |
|------|---------|
| `architect_scan` | Scan repo structure (AST analysis) |
| `architect_slice` | Get compressed context (token arbitrage) |
| `architect_validate` | Validate architecture model |
| `architect_extract` | Store architecture extraction |
| `architect_group` | Group modules into components |
| `architect_check` | Verify model representativeness |

## Workflow

1. **First time:** Agent calls `architect_scan` → `architect_group` → produces model → `architect_validate` → `architect_extract`
2. **Ongoing:** Agent calls `architect_slice` to get compressed context before reasoning about changes

## Token Savings

The `architect_slice` tool compresses your entire codebase into ~4000 tokens of dense context. For a 50K-line project, this represents ~50x compression while preserving architectural understanding.
```

**Step 2: Commit**

```bash
git add docs/integrations/cursor-mcp.md
git commit -m "docs: add Cursor MCP setup guide"
```

---

### Task 3: MCP setup guide for Cline

**Files:**
- Create: `docs/integrations/cline-mcp.md`

**Step 1: Write guide**

```markdown
# Architecture Model MCP Server — Cline Setup

## Prerequisites

```bash
pip install opencode-arch
```

## Configuration

Add to Cline's MCP settings (VS Code settings or `cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "arch-model": {
      "command": "python",
      "args": ["-m", "opencode_arch.mcp.server"],
      "disabled": false
    }
  }
}
```

Or via Cline's UI: Settings → MCP Servers → Add Server → Enter:
- Name: `arch-model`
- Command: `python -m opencode_arch.mcp.server`

## Usage with Cline

Cline will automatically discover the MCP tools. You can prompt it:

> "Use architect_scan to understand this project's structure, then architect_slice to get compressed context"

> "Validate my architecture model using architect_validate"

## Recommended Workflow

Add to your Cline custom instructions:

```
Before making architectural changes, always:
1. Call architect_slice to understand current architecture
2. After changes, call architect_check to verify model is still representative
```
```

**Step 2: Commit**

```bash
git add docs/integrations/cline-mcp.md
git commit -m "docs: add Cline MCP setup guide"
```

---

### Task 4: MCP setup guide for Continue

**Files:**
- Create: `docs/integrations/continue-mcp.md`

**Step 1: Write guide**

```markdown
# Architecture Model MCP Server — Continue Setup

## Prerequisites

```bash
pip install opencode-arch
```

## Configuration

Add to your Continue config (`~/.continue/config.json` or `.continue/config.json`):

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "python",
          "args": ["-m", "opencode_arch.mcp.server"]
        }
      }
    ]
  }
}
```

## Usage

Continue will expose the architecture tools as context providers. Use them via:

- `@arch-model` context provider — automatically slices relevant architecture context
- Direct tool calls in chat — ask Continue to call `architect_scan`, `architect_slice`, etc.

## Context Provider Setup

For automatic architecture context in every conversation, add to config:

```json
{
  "contextProviders": [
    {
      "name": "architecture",
      "params": {
        "command": "python",
        "args": ["-m", "opencode_arch.mcp.server", "--slice", "--budget", "2000"]
      }
    }
  ]
}
```

This injects compressed architecture context into every prompt automatically.
```

**Step 2: Commit**

```bash
git add docs/integrations/continue-mcp.md
git commit -m "docs: add Continue MCP setup guide"
```

---

### Task 5: Integration overview README

**Files:**
- Create: `docs/integrations/README.md`

**Step 1: Write overview**

```markdown
# AI Tool Integrations

Architecture-model-standard works with any AI coding tool that supports MCP (Model Context Protocol) or custom rules files.

## Quick Start

| Tool | Setup Time | Method |
|------|-----------|--------|
| **OpenCode** | 30s | `opencode mcp add` (built-in) |
| **Cursor** | 2 min | [MCP config](./cursor-mcp.md) + [.cursorrules](./cursorrules-template.md) |
| **Cline** | 2 min | [MCP config](./cline-mcp.md) |
| **Continue** | 2 min | [MCP config](./continue-mcp.md) |

## What You Get

1. **Token arbitrage** — 50x compression of codebase into architectural context
2. **Structure awareness** — Agent knows component boundaries, layers, dependencies
3. **Quality gates** — Validate and check representativeness of architecture models
4. **Generated docs** — Component specs, ICDs, health reports auto-generated

## Without MCP (any tool)

Even without MCP support, you can use:
1. `.cursorrules` / custom instructions — paste architecture rules into your tool
2. Generated docs — point your tool at `.architecture-models/docs/`
3. Manual context — copy `architect_slice` output into prompts

## Installation

```bash
pip install opencode-arch  # MCP server + CLI
# OR
pip install architecture-model-standard  # Library only (for init/docs)
```
```

**Step 2: Commit**

```bash
git add docs/integrations/README.md
git commit -m "docs: add integrations overview README"
```

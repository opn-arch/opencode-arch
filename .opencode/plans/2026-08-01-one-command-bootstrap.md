# One-Command Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `architecture-model init .` run the full pipeline (config + extraction + docs) in one command, and create a standalone `npx @arch-model/init` package that does the same without requiring Python.

**Architecture:** Extend existing `_cmd_init` to chain into `run_pipeline()` + `generate_docs()` after writing config. Create a new npm package `packages/arch-model-init/` that reimplements the init logic in JS (using the JS scanner for TS/JS projects, with fallback heuristics for other languages).

**Tech Stack:** Python (existing CLI), Node.js/TypeScript (npx package), argparse, ts-morph (for JS scanner integration)

**Repos:**
- `architecture-model-standard` @ `/Users/baigm2/Documents/Projects/architecture-model-standard/`
- Tests: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

---

### Task 1: Extend Python `init` to run full pipeline

**Files:**
- Modify: `src/architecture_model/cli/main.py:127-162`
- Test: `tests/test_cli_init_full.py`

**Step 1: Write the failing test**

```python
"""Tests for full-pipeline init command."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from architecture_model.cli.main import main


def _create_mini_project(tmp: Path):
    """Create a minimal Python project for init."""
    (tmp / "app.py").write_text("def hello(): pass\n")
    (tmp / "utils.py").write_text("import app\ndef helper(): pass\n")


def test_init_runs_full_pipeline(tmp_path):
    """init should write config AND run pipeline + docs."""
    _create_mini_project(tmp_path)
    
    with patch("sys.argv", ["architecture-model", "init", str(tmp_path)]):
        code = main()
    
    assert code == 0
    # Config written
    assert (tmp_path / ".architecture-model.yaml").exists()
    # Pipeline ran (produces manifests dir)
    assert (tmp_path / ".architecture-models").is_dir()


def test_init_skip_pipeline_flag(tmp_path):
    """--config-only should skip pipeline."""
    _create_mini_project(tmp_path)
    
    with patch("sys.argv", ["architecture-model", "init", str(tmp_path), "--config-only"]):
        code = main()
    
    assert code == 0
    assert (tmp_path / ".architecture-model.yaml").exists()
    assert not (tmp_path / ".architecture-models").is_dir()


def test_init_shows_compression_ratio(tmp_path, capsys):
    """init should display compression ratio after pipeline."""
    _create_mini_project(tmp_path)
    
    with patch("sys.argv", ["architecture-model", "init", str(tmp_path)]):
        main()
    
    captured = capsys.readouterr()
    assert "compression" in captured.out.lower() or "token" in captured.out.lower()
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_cli_init_full.py -v`
Expected: FAIL (init doesn't run pipeline yet)

**Step 3: Implement enhanced init**

Modify `_cmd_init` in `src/architecture_model/cli/main.py`:

```python
def _cmd_init(args) -> int:
    from ..config.loader import discover_config, write_config, CONFIG_FILENAME
    from ..orchestration.pipeline import run_pipeline
    from ..docs import generate_docs

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    config_path = root / CONFIG_FILENAME
    if config_path.exists() and not args.force:
        print(f"Config already exists: {config_path}")
        print("Use --force to overwrite.")
        return 1

    print(f"Scanning: {root}")
    config, _report = discover_config(root)

    # Summary
    print(f"\nProject: {config.name}")
    print(f"System:  {config.system}")
    print(f"Layers:  {len(config.layers)}")
    for layer in config.layers:
        print(f"  - {layer.id}: {layer.dirs}")
    print(f"Functional Blocks: {len(config.functional_blocks)}")
    for fb in config.functional_blocks:
        print(f"  - [{fb.id}] {fb.name} ({len(fb.files)} files)")
        if fb.description_source:
            print(f"    {fb.description_source}")
    print(f"Metrics: {len(config.metrics)}")
    for m in config.metrics:
        print(f"  - {m.label}: {m.path} ({m.pattern})")

    # Write config
    out_path = write_config(config, root)
    print(f"\nWritten: {out_path}")

    # Run full pipeline unless --config-only
    if not getattr(args, "config_only", False):
        print("\nRunning pipeline...")
        try:
            result = run_pipeline(root, from_scratch=True)
            print(f"  Manifests: {len(result.manifests)}")
            print(f"  F-blocks: {len(result.fblock_config) if result.fblock_config else 0}")
            if result.errors:
                print(f"  Warnings: {len(result.errors)}")
                for err in result.errors[:3]:
                    print(f"    - {err}")
        except Exception as e:
            print(f"  Pipeline warning: {e}")
            print("  Config written successfully. Run 'architecture-model manifest --recursive' manually.")
            return 0

        # Generate docs
        print("\nGenerating docs...")
        try:
            from ..core.parser import load_model
            extracted = root / ".architecture-models" / "extracted.yaml"
            if not extracted.exists():
                # Try finding any model file
                for candidate in [root / ".architecture-model-extracted.yaml"]:
                    if candidate.exists():
                        extracted = candidate
                        break
            if extracted.exists():
                model = load_model(str(extracted))
                docs_dir = generate_docs(model, root / ".architecture-models" / "docs")
                print(f"  Docs: {docs_dir}")
        except Exception as e:
            print(f"  Docs warning: {e}")

        # Show compression ratio
        _show_compression_stats(root)

    return 0


def _show_compression_stats(root: Path):
    """Display token savings summary."""
    source_size = sum(
        f.stat().st_size
        for ext in ("*.py", "*.ts", "*.js", "*.go", "*.rs", "*.java")
        for f in root.rglob(ext)
        if not any(p in f.parts for p in ("node_modules", ".git", "vendor", "__pycache__"))
    )
    if source_size == 0:
        return

    # Model size (compressed representation)
    model_files = list((root / ".architecture-models").rglob("*.yaml")) if (root / ".architecture-models").exists() else []
    model_size = sum(f.stat().st_size for f in model_files)
    
    if model_size > 0:
        ratio = source_size / model_size
        source_tokens = source_size // 4  # ~4 chars per token
        model_tokens = model_size // 4
        saved = source_tokens - model_tokens
        print(f"\n--- Token Savings ---")
        print(f"  Source: ~{source_tokens:,} tokens ({source_size:,} bytes)")
        print(f"  Model:  ~{model_tokens:,} tokens ({model_size:,} bytes)")
        print(f"  Compression: {ratio:.1f}x ({saved:,} tokens saved)")
```

Also add `--config-only` flag to the argparse setup. Find where `init` subparser is defined and add:
```python
init_parser.add_argument("--config-only", action="store_true", help="Only write config, skip pipeline")
```

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_cli_init_full.py -v`
Expected: PASS

**Step 5: Run full test suite for regressions**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py -x`
Expected: All pass

**Step 6: Commit**

```bash
git add src/architecture_model/cli/main.py tests/test_cli_init_full.py
git commit -m "feat: extend init command to run full pipeline + show token savings"
```

---

### Task 2: Create npx @arch-model/init package

**Files:**
- Create: `packages/arch-model-init/package.json`
- Create: `packages/arch-model-init/tsconfig.json`
- Create: `packages/arch-model-init/src/index.ts`
- Create: `packages/arch-model-init/src/scanner.ts`
- Create: `packages/arch-model-init/src/config-writer.ts`
- Create: `packages/arch-model-init/src/detect.ts`
- Create: `packages/arch-model-init/bin/arch-model-init.js`
- Test: `packages/arch-model-init/tests/init.test.ts`

**Step 1: Create package.json**

```json
{
  "name": "@arch-model/init",
  "version": "0.1.0",
  "description": "One-command architecture model bootstrap for any project",
  "bin": {
    "arch-model-init": "./bin/arch-model-init.js"
  },
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {
    "ts-morph": "^22.0.0",
    "yaml": "^2.4.0",
    "glob": "^10.3.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vitest": "^1.6.0",
    "@types/node": "^20.0.0"
  },
  "files": ["dist/", "bin/"],
  "keywords": ["architecture", "model", "init", "scaffold"],
  "license": "MIT"
}
```

**Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
```

**Step 3: Create src/detect.ts (language detection)**

```typescript
import { existsSync } from "fs";
import { join } from "path";

export type Language = "python" | "typescript" | "javascript" | "go" | "rust" | "java" | "unknown";

export function detectLanguage(root: string): Language {
  const indicators: [string, Language][] = [
    ["tsconfig.json", "typescript"],
    ["package.json", "typescript"], // treat JS projects as TS for scanning
    ["pyproject.toml", "python"],
    ["setup.py", "python"],
    ["go.mod", "go"],
    ["Cargo.toml", "rust"],
    ["pom.xml", "java"],
    ["build.gradle", "java"],
  ];

  for (const [file, lang] of indicators) {
    if (existsSync(join(root, file))) return lang;
  }
  return "unknown";
}
```

**Step 4: Create src/scanner.ts (TS/JS scanning via ts-morph)**

```typescript
import { Project, SourceFile, SyntaxKind } from "ts-morph";
import { join, relative } from "path";

export interface ExportedSymbol {
  name: string;
  kind: "function" | "class" | "constant" | "type" | "interface";
  signature: string;
  doc: string;
}

export interface SourceUnit {
  file: string;
  has_content: boolean;
  exports: ExportedSymbol[];
  language: string;
}

export interface DependencyEdge {
  source: string;
  target: string;
  symbols: string[];
}

export interface SourceGraph {
  units: SourceUnit[];
  edges: DependencyEdge[];
  root: string;
  language: string;
}

export function scanTypeScript(root: string): SourceGraph {
  const project = new Project({
    tsConfigFilePath: join(root, "tsconfig.json"),
    skipAddingFilesFromTsConfig: false,
  });

  // If no tsconfig, add files manually
  if (project.getSourceFiles().length === 0) {
    project.addSourceFilesAtPaths(join(root, "src/**/*.{ts,tsx,js,jsx}"));
    project.addSourceFilesAtPaths(join(root, "lib/**/*.{ts,tsx,js,jsx}"));
  }

  const units: SourceUnit[] = [];
  const edges: DependencyEdge[] = [];
  const files = project.getSourceFiles().filter(
    (f) => !f.getFilePath().includes("node_modules")
  );

  for (const file of files) {
    const relPath = relative(root, file.getFilePath());
    const exports = getExports(file);
    const isReExportOnly = exports.length > 0 && file.getStatements().every(
      (s) => s.getKind() === SyntaxKind.ExportDeclaration
    );

    units.push({
      file: relPath,
      has_content: !isReExportOnly && exports.length > 0,
      exports,
      language: relPath.endsWith(".ts") || relPath.endsWith(".tsx") ? "typescript" : "javascript",
    });

    // Collect imports as edges
    for (const imp of file.getImportDeclarations()) {
      const moduleSpecifier = imp.getModuleSpecifierValue();
      if (moduleSpecifier.startsWith(".")) {
        const resolved = imp.getModuleSpecifierSourceFile();
        if (resolved) {
          const targetPath = relative(root, resolved.getFilePath());
          const symbols = imp.getNamedImports().map((n) => n.getName());
          const defaultImport = imp.getDefaultImport();
          if (defaultImport) symbols.push(defaultImport.getText());
          edges.push({ source: relPath, target: targetPath, symbols });
        }
      }
    }
  }

  return { units, edges, root, language: "typescript" };
}

function getExports(file: SourceFile): ExportedSymbol[] {
  const symbols: ExportedSymbol[] = [];

  for (const fn of file.getFunctions().filter((f) => f.isExported())) {
    symbols.push({
      name: fn.getName() || "default",
      kind: "function",
      signature: `(${fn.getParameters().map((p) => `${p.getName()}: ${p.getType().getText()}`).join(", ")}) => ${fn.getReturnType().getText()}`,
      doc: fn.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  for (const cls of file.getClasses().filter((c) => c.isExported())) {
    symbols.push({
      name: cls.getName() || "default",
      kind: "class",
      signature: cls.getImplements().map((i) => i.getText()).join(", "),
      doc: cls.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  for (const iface of file.getInterfaces().filter((i) => i.isExported())) {
    symbols.push({
      name: iface.getName(),
      kind: "interface",
      signature: "",
      doc: iface.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  for (const ta of file.getTypeAliases().filter((t) => t.isExported())) {
    symbols.push({
      name: ta.getName(),
      kind: "type",
      signature: ta.getType().getText(),
      doc: ta.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  return symbols;
}
```

**Step 5: Create src/config-writer.ts (produces .architecture-model.yaml)**

```typescript
import { writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { stringify } from "yaml";
import type { SourceGraph } from "./scanner";

interface FunctionalBlock {
  name: string;
  files: string[];
}

export function groupIntoBlocks(graph: SourceGraph, targetGroups = 0): FunctionalBlock[] {
  // Group by top-level directory
  const dirGroups = new Map<string, string[]>();
  for (const unit of graph.units) {
    if (!unit.has_content) continue;
    const parts = unit.file.split("/");
    const dir = parts.length > 1 ? parts[0] : "_root";
    if (!dirGroups.has(dir)) dirGroups.set(dir, []);
    dirGroups.get(dir)!.push(unit.file);
  }

  return Array.from(dirGroups.entries()).map(([dir, files]) => ({
    name: dir === "_root" ? "Core" : dir.charAt(0).toUpperCase() + dir.slice(1),
    files,
  }));
}

export function writeConfig(root: string, graph: SourceGraph, blocks: FunctionalBlock[]): string {
  const fblocks: Record<string, any> = {};
  blocks.forEach((b, i) => {
    fblocks[`F${i + 1}`] = {
      name: b.name,
      files: b.files,
    };
  });

  const config = {
    project: { name: root.split("/").pop() || "project" },
    system: `${graph.language} project`,
    schema_version: "1.3",
    functional_blocks: fblocks,
    layers: {
      L1: { name: "Application", dirs: ["src/", "lib/"] },
    },
  };

  const configPath = join(root, ".architecture-model.yaml");
  writeFileSync(configPath, stringify(config), "utf-8");
  return configPath;
}

export function writeSourceGraph(root: string, graph: SourceGraph): string {
  const outDir = join(root, ".architecture-models");
  mkdirSync(outDir, { recursive: true });
  const outPath = join(outDir, "source-graph.json");
  writeFileSync(outPath, JSON.stringify(graph, null, 2), "utf-8");
  return outPath;
}
```

**Step 6: Create src/index.ts (main entry point)**

```typescript
import { resolve } from "path";
import { detectLanguage } from "./detect";
import { scanTypeScript } from "./scanner";
import { groupIntoBlocks, writeConfig, writeSourceGraph } from "./config-writer";

export interface InitResult {
  configPath: string;
  sourceGraphPath: string;
  language: string;
  fileCount: number;
  blockCount: number;
}

export async function init(targetDir: string): Promise<InitResult> {
  const root = resolve(targetDir);
  const language = detectLanguage(root);

  console.log(`Detected language: ${language}`);

  if (language !== "typescript" && language !== "javascript") {
    throw new Error(
      `@arch-model/init currently supports TypeScript/JavaScript projects.\n` +
      `For ${language} projects, use: pip install architecture-model-standard && architecture-model init .`
    );
  }

  console.log("Scanning project...");
  const graph = scanTypeScript(root);
  console.log(`  Found ${graph.units.length} source files, ${graph.edges.length} dependencies`);

  const blocks = groupIntoBlocks(graph);
  console.log(`  Grouped into ${blocks.length} functional blocks`);

  const configPath = writeConfig(root, graph, blocks);
  console.log(`  Config: ${configPath}`);

  const sourceGraphPath = writeSourceGraph(root, graph);
  console.log(`  Source graph: ${sourceGraphPath}`);

  // Show compression stats
  const sourceTokens = graph.units.reduce((acc, u) => acc + u.exports.length * 50, 0); // rough estimate
  const modelTokens = Math.round(JSON.stringify(graph).length / 4);
  console.log(`\n--- Token Savings ---`);
  console.log(`  Compression: model captures structure in ~${modelTokens.toLocaleString()} tokens`);

  return {
    configPath,
    sourceGraphPath,
    language,
    fileCount: graph.units.length,
    blockCount: blocks.length,
  };
}

export { scanTypeScript } from "./scanner";
export { detectLanguage } from "./detect";
```

**Step 7: Create bin/arch-model-init.js**

```javascript
#!/usr/bin/env node
const { init } = require("../dist/index");

const targetDir = process.argv[2] || ".";

init(targetDir)
  .then((result) => {
    console.log(`\nDone! Architecture model initialized.`);
    console.log(`  Files scanned: ${result.fileCount}`);
    console.log(`  Blocks: ${result.blockCount}`);
    console.log(`\nNext steps:`);
    console.log(`  1. Review .architecture-model.yaml`);
    console.log(`  2. Use with your AI coding tool (Cursor, Continue, Cline)`);
  })
  .catch((err) => {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  });
```

**Step 8: Write tests**

```typescript
// packages/arch-model-init/tests/init.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { detectLanguage } from "../src/detect";
import { groupIntoBlocks } from "../src/config-writer";
import type { SourceGraph } from "../src/scanner";

describe("detectLanguage", () => {
  it("detects typescript from tsconfig.json", () => {
    const tmp = mkdtempSync(join(tmpdir(), "arch-"));
    writeFileSync(join(tmp, "tsconfig.json"), "{}");
    expect(detectLanguage(tmp)).toBe("typescript");
  });

  it("detects python from pyproject.toml", () => {
    const tmp = mkdtempSync(join(tmpdir(), "arch-"));
    writeFileSync(join(tmp, "pyproject.toml"), "");
    expect(detectLanguage(tmp)).toBe("python");
  });

  it("returns unknown for empty dir", () => {
    const tmp = mkdtempSync(join(tmpdir(), "arch-"));
    expect(detectLanguage(tmp)).toBe("unknown");
  });
});

describe("groupIntoBlocks", () => {
  it("groups by top-level directory", () => {
    const graph: SourceGraph = {
      units: [
        { file: "src/a.ts", has_content: true, exports: [], language: "typescript" },
        { file: "src/b.ts", has_content: true, exports: [], language: "typescript" },
        { file: "lib/c.ts", has_content: true, exports: [], language: "typescript" },
      ],
      edges: [],
      root: "/tmp",
      language: "typescript",
    };
    const blocks = groupIntoBlocks(graph);
    expect(blocks).toHaveLength(2);
    expect(blocks.map((b) => b.name).sort()).toEqual(["Lib", "Src"]);
  });
});
```

**Step 9: Install deps and run tests**

```bash
cd packages/arch-model-init
npm install
npm test
```

**Step 10: Commit**

```bash
git add packages/arch-model-init/
git commit -m "feat: add @arch-model/init npx package for JS/TS projects"
```

---

### Task 3: Integration test — full round trip

**Step 1:** Create a temp TS project, run `npx .` on it, verify outputs.

**Step 2:** Test Python init on a sample project, verify docs generated.

**Step 3: Commit final integration test**

```bash
git commit -m "test: add integration tests for bootstrap flow"
```

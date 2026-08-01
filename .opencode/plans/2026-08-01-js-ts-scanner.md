# JS/TS Scanner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `@arch-model/scanner-js` npm package that produces `source-graph.json` from TypeScript/JavaScript projects using ts-morph, plus a Python tree-sitter fallback.

**Architecture:** The scanner is a standalone npm package in `packages/scanner-js/`. It outputs SourceGraph JSON matching the protocol in `src/architecture_model/manifest/protocol.py`. The Python fallback uses tree-sitter-typescript bindings for environments without Node.js. The existing `enrich_from_source_graph()` in arch-model-standard already consumes this format.

**Tech Stack:** ts-morph, Node.js, tree-sitter (Python bindings), vitest

**Repos:**
- `architecture-model-standard` @ `/Users/baigm2/Documents/Projects/architecture-model-standard/`

**NOTE:** The `@arch-model/init` package (Task 2 of bootstrap plan) already includes a scanner module. This plan creates the STANDALONE scanner package with more comprehensive capabilities (re-export resolution, barrel file handling, JSDoc extraction, type inference). The init package can depend on this.

---

### Task 1: Create @arch-model/scanner-js package structure

**Files:**
- Create: `packages/scanner-js/package.json`
- Create: `packages/scanner-js/tsconfig.json`
- Create: `packages/scanner-js/src/index.ts`
- Create: `packages/scanner-js/src/scan.ts`
- Create: `packages/scanner-js/src/resolve-exports.ts`
- Create: `packages/scanner-js/src/types.ts`
- Create: `packages/scanner-js/bin/scan.js`
- Test: `packages/scanner-js/tests/scan.test.ts`

**Step 1: Create package.json**

```json
{
  "name": "@arch-model/scanner-js",
  "version": "0.1.0",
  "description": "TypeScript/JavaScript source scanner for architecture-model-standard",
  "bin": {
    "arch-model-scan": "./bin/scan.js"
  },
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {
    "ts-morph": "^22.0.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vitest": "^1.6.0",
    "@types/node": "^20.0.0"
  },
  "files": ["dist/", "bin/"],
  "keywords": ["architecture", "scanner", "typescript", "ast"],
  "license": "MIT"
}
```

**Step 2: Create src/types.ts (matching Python SourceGraph protocol)**

```typescript
/**
 * Types matching architecture_model.manifest.protocol.SourceGraph
 * This is the output format consumed by enrich_from_source_graph().
 */

export interface ExportedSymbol {
  name: string;
  kind: "function" | "class" | "constant" | "type" | "interface";
  signature: string;
  doc: string;
}

export interface SourceUnit {
  file: string;           // relative path from repo root
  has_content: boolean;   // false = re-export only, empty, or generated
  exports: ExportedSymbol[];
  language: "typescript" | "javascript";
}

export interface DependencyEdge {
  source: string;         // source file path (relative)
  target: string;         // target file path (relative)
  symbols: string[];      // imported symbol names
}

export interface SourceGraph {
  units: SourceUnit[];
  edges: DependencyEdge[];
  root: string;
  language: string;
}

export interface ScanOptions {
  root: string;
  tsConfigPath?: string;    // custom tsconfig location
  include?: string[];       // glob patterns to include
  exclude?: string[];       // glob patterns to exclude (default: node_modules, dist, .git)
  followReExports?: boolean; // resolve barrel files (default: true)
}
```

**Step 3: Create src/resolve-exports.ts (barrel file resolution)**

```typescript
import { SourceFile, SyntaxKind, ExportDeclaration } from "ts-morph";
import type { ExportedSymbol } from "./types";

/**
 * Determines if a file is a barrel (re-export only) file.
 * Barrel files: index.ts that only re-exports from other modules.
 */
export function isBarrelFile(file: SourceFile): boolean {
  const statements = file.getStatements();
  if (statements.length === 0) return true;
  
  return statements.every((s) => {
    const kind = s.getKind();
    return (
      kind === SyntaxKind.ExportDeclaration ||
      kind === SyntaxKind.ImportDeclaration ||
      kind === SyntaxKind.EmptyStatement
    );
  });
}

/**
 * Resolves re-exports to their original source.
 * e.g., `export { foo } from './bar'` → traces foo back to bar.ts
 */
export function resolveReExports(file: SourceFile): Map<string, string> {
  const reExportMap = new Map<string, string>(); // symbol → original file path
  
  for (const exp of file.getExportDeclarations()) {
    const moduleSpecifier = exp.getModuleSpecifierSourceFile();
    if (!moduleSpecifier) continue;
    
    const targetPath = moduleSpecifier.getFilePath();
    
    // Named re-exports: export { foo, bar } from './module'
    for (const named of exp.getNamedExports()) {
      reExportMap.set(named.getName(), targetPath);
    }
    
    // Star re-exports: export * from './module'
    if (exp.getNamedExports().length === 0 && !exp.getNamespaceExport()) {
      // export * — all exports from target
      for (const symbol of moduleSpecifier.getExportedDeclarations().keys()) {
        reExportMap.set(symbol, targetPath);
      }
    }
  }
  
  return reExportMap;
}
```

**Step 4: Create src/scan.ts (main scanner)**

```typescript
import { Project, SourceFile, SyntaxKind } from "ts-morph";
import { relative, join } from "path";
import type { SourceGraph, SourceUnit, DependencyEdge, ExportedSymbol, ScanOptions } from "./types";
import { isBarrelFile, resolveReExports } from "./resolve-exports";

const DEFAULT_EXCLUDE = ["**/node_modules/**", "**/dist/**", "**/.git/**", "**/coverage/**", "**/*.d.ts"];

export function scan(options: ScanOptions): SourceGraph {
  const { root, tsConfigPath, include, exclude = DEFAULT_EXCLUDE, followReExports = true } = options;

  const project = new Project({
    tsConfigFilePath: tsConfigPath || tryFindTsConfig(root),
    skipAddingFilesFromTsConfig: false,
    skipFileDependencyResolution: false,
  });

  // If no files loaded from tsconfig, add manually
  if (project.getSourceFiles().length === 0) {
    const patterns = include || ["src/**/*.{ts,tsx,js,jsx}", "lib/**/*.{ts,tsx,js,jsx}", "*.{ts,tsx,js,jsx}"];
    for (const pattern of patterns) {
      project.addSourceFilesAtPaths(join(root, pattern));
    }
  }

  const sourceFiles = project.getSourceFiles().filter((f) => {
    const path = f.getFilePath();
    return !exclude.some((pat) => {
      // Simple glob check (node_modules, dist, etc.)
      const segment = pat.replace(/\*\*/g, "").replace(/\*/g, "").replace(/\//g, "");
      return path.includes(segment);
    });
  });

  const units: SourceUnit[] = [];
  const edges: DependencyEdge[] = [];

  for (const file of sourceFiles) {
    const relPath = relative(root, file.getFilePath());
    const exports = extractExports(file);
    const barrel = isBarrelFile(file);

    units.push({
      file: relPath,
      has_content: !barrel && (exports.length > 0 || hasSignificantCode(file)),
      exports,
      language: relPath.match(/\.tsx?$/) ? "typescript" : "javascript",
    });

    // Extract dependency edges
    for (const imp of file.getImportDeclarations()) {
      const moduleSpecifier = imp.getModuleSpecifierValue();
      if (!moduleSpecifier.startsWith(".") && !moduleSpecifier.startsWith("/")) continue;

      const resolved = imp.getModuleSpecifierSourceFile();
      if (!resolved) continue;

      const targetPath = relative(root, resolved.getFilePath());
      const symbols: string[] = [];

      for (const named of imp.getNamedImports()) {
        symbols.push(named.getName());
      }
      const defaultImport = imp.getDefaultImport();
      if (defaultImport) symbols.push(defaultImport.getText());
      const namespaceImport = imp.getNamespaceImport();
      if (namespaceImport) symbols.push(`* as ${namespaceImport.getText()}`);

      edges.push({ source: relPath, target: targetPath, symbols });
    }
  }

  return { units, edges, root, language: "typescript" };
}

function extractExports(file: SourceFile): ExportedSymbol[] {
  const symbols: ExportedSymbol[] = [];

  // Functions
  for (const fn of file.getFunctions().filter((f) => f.isExported())) {
    const params = fn.getParameters().map((p) => {
      const typeText = p.getType().getText(p);
      return `${p.getName()}${p.isOptional() ? "?" : ""}: ${typeText}`;
    });
    symbols.push({
      name: fn.getName() || "default",
      kind: "function",
      signature: `(${params.join(", ")}) => ${fn.getReturnType().getText(fn)}`,
      doc: fn.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  // Classes
  for (const cls of file.getClasses().filter((c) => c.isExported())) {
    const implements_ = cls.getImplements().map((i) => i.getText());
    const extends_ = cls.getExtends()?.getText() || "";
    let sig = "";
    if (extends_) sig += `extends ${extends_}`;
    if (implements_.length) sig += ` implements ${implements_.join(", ")}`;
    symbols.push({
      name: cls.getName() || "default",
      kind: "class",
      signature: sig.trim(),
      doc: cls.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  // Interfaces
  for (const iface of file.getInterfaces().filter((i) => i.isExported())) {
    const extends_ = iface.getExtends().map((e) => e.getText());
    symbols.push({
      name: iface.getName(),
      kind: "interface",
      signature: extends_.length ? `extends ${extends_.join(", ")}` : "",
      doc: iface.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  // Type aliases
  for (const ta of file.getTypeAliases().filter((t) => t.isExported())) {
    symbols.push({
      name: ta.getName(),
      kind: "type",
      signature: ta.getTypeNode()?.getText() || "",
      doc: ta.getJsDocs()[0]?.getDescription()?.trim() || "",
    });
  }

  // Exported constants (const x = ...)
  for (const vs of file.getVariableStatements().filter((v) => v.isExported())) {
    for (const decl of vs.getDeclarations()) {
      symbols.push({
        name: decl.getName(),
        kind: "constant",
        signature: decl.getType().getText(decl),
        doc: vs.getJsDocs()[0]?.getDescription()?.trim() || "",
      });
    }
  }

  return symbols;
}

function hasSignificantCode(file: SourceFile): boolean {
  // A file has significant code if it has functions, classes, or >5 statements
  return (
    file.getFunctions().length > 0 ||
    file.getClasses().length > 0 ||
    file.getStatements().length > 5
  );
}

function tryFindTsConfig(root: string): string | undefined {
  const candidates = ["tsconfig.json", "tsconfig.build.json"];
  for (const c of candidates) {
    try {
      const path = join(root, c);
      require("fs").accessSync(path);
      return path;
    } catch {}
  }
  return undefined;
}
```

**Step 5: Create src/index.ts**

```typescript
export { scan } from "./scan";
export { isBarrelFile, resolveReExports } from "./resolve-exports";
export type { SourceGraph, SourceUnit, DependencyEdge, ExportedSymbol, ScanOptions } from "./types";
```

**Step 6: Create bin/scan.js (CLI)**

```javascript
#!/usr/bin/env node
const { scan } = require("../dist/scan");
const { writeFileSync } = require("fs");
const { resolve, join } = require("path");

const root = resolve(process.argv[2] || ".");
const output = process.argv[3] || join(root, ".architecture-models", "source-graph.json");

console.log(`Scanning: ${root}`);
const graph = scan({ root });

console.log(`  Files: ${graph.units.length}`);
console.log(`  Dependencies: ${graph.edges.length}`);
console.log(`  Exports: ${graph.units.reduce((acc, u) => acc + u.exports.length, 0)}`);

const { mkdirSync } = require("fs");
const { dirname } = require("path");
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(graph, null, 2));
console.log(`  Output: ${output}`);
```

**Step 7: Write tests**

```typescript
// packages/scanner-js/tests/scan.test.ts
import { describe, it, expect, beforeAll } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { scan } from "../src/scan";
import { isBarrelFile } from "../src/resolve-exports";
import { Project } from "ts-morph";

function createTestProject(): string {
  const tmp = mkdtempSync(join(tmpdir(), "scanner-"));
  mkdirSync(join(tmp, "src"), { recursive: true });
  
  writeFileSync(join(tmp, "tsconfig.json"), JSON.stringify({
    compilerOptions: { target: "ES2022", module: "Node16", moduleResolution: "Node16", rootDir: "./src", outDir: "./dist" },
    include: ["src/**/*"]
  }));

  writeFileSync(join(tmp, "src", "utils.ts"), `
export function add(a: number, b: number): number {
  return a + b;
}

export const VERSION = "1.0.0";

/** Helper class for math operations */
export class MathHelper {
  multiply(a: number, b: number): number { return a * b; }
}
`);

  writeFileSync(join(tmp, "src", "main.ts"), `
import { add, MathHelper } from "./utils";

export function run(): void {
  const result = add(1, 2);
  const helper = new MathHelper();
  console.log(result, helper.multiply(3, 4));
}
`);

  writeFileSync(join(tmp, "src", "index.ts"), `
export { add, VERSION } from "./utils";
export { run } from "./main";
`);

  return tmp;
}

describe("scan", () => {
  let tmp: string;

  beforeAll(() => {
    tmp = createTestProject();
  });

  it("finds all source files", () => {
    const graph = scan({ root: tmp });
    expect(graph.units.length).toBe(3);
  });

  it("extracts exports with signatures", () => {
    const graph = scan({ root: tmp });
    const utils = graph.units.find((u) => u.file.includes("utils"));
    expect(utils).toBeDefined();
    expect(utils!.exports.length).toBe(3); // add, VERSION, MathHelper
    
    const addFn = utils!.exports.find((e) => e.name === "add");
    expect(addFn).toBeDefined();
    expect(addFn!.kind).toBe("function");
    expect(addFn!.signature).toContain("number");
  });

  it("captures dependency edges", () => {
    const graph = scan({ root: tmp });
    const mainToUtils = graph.edges.find(
      (e) => e.source.includes("main") && e.target.includes("utils")
    );
    expect(mainToUtils).toBeDefined();
    expect(mainToUtils!.symbols).toContain("add");
    expect(mainToUtils!.symbols).toContain("MathHelper");
  });

  it("detects barrel files", () => {
    const graph = scan({ root: tmp });
    const index = graph.units.find((u) => u.file.includes("index"));
    expect(index).toBeDefined();
    expect(index!.has_content).toBe(false); // barrel file
  });

  it("sets language correctly", () => {
    const graph = scan({ root: tmp });
    expect(graph.language).toBe("typescript");
    for (const unit of graph.units) {
      expect(unit.language).toBe("typescript");
    }
  });
});

describe("isBarrelFile", () => {
  it("detects re-export-only files", () => {
    const project = new Project({ useInMemoryFileSystem: true });
    const barrel = project.createSourceFile("index.ts", `export { foo } from "./foo";\nexport { bar } from "./bar";`);
    expect(isBarrelFile(barrel)).toBe(true);
  });

  it("does not flag files with implementation", () => {
    const project = new Project({ useInMemoryFileSystem: true });
    const impl = project.createSourceFile("impl.ts", `export function foo() { return 1; }`);
    expect(isBarrelFile(impl)).toBe(false);
  });
});
```

**Step 8: Install and run tests**

```bash
cd packages/scanner-js
npm install
npm test
```

**Step 9: Commit**

```bash
git add packages/scanner-js/
git commit -m "feat: add @arch-model/scanner-js package with ts-morph scanning"
```

---

### Task 2: Python tree-sitter fallback

**Files:**
- Create: `src/architecture_model/manifest/ts_scanner.py`
- Test: `tests/test_ts_scanner.py`

**Step 1: Write failing test**

```python
"""Tests for tree-sitter TypeScript fallback scanner."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from architecture_model.manifest.ts_scanner import scan_typescript_fallback


@pytest.fixture
def ts_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.ts").write_text(
        "import { helper } from './utils';\n"
        "export function main(): void { helper(); }\n"
    )
    (src / "utils.ts").write_text(
        "export function helper(): string { return 'hi'; }\n"
        "export class Config { value: number = 0; }\n"
    )
    (tmp_path / "tsconfig.json").write_text("{}")
    return tmp_path


def test_fallback_produces_source_graph(ts_project):
    """Fallback scanner produces valid SourceGraph dict."""
    result = scan_typescript_fallback(ts_project)
    assert "units" in result
    assert "edges" in result
    assert len(result["units"]) >= 2


def test_fallback_extracts_exports(ts_project):
    """Fallback extracts exported function/class names."""
    result = scan_typescript_fallback(ts_project)
    utils = next(u for u in result["units"] if "utils" in u["file"])
    export_names = [e["name"] for e in utils["exports"]]
    assert "helper" in export_names
    assert "Config" in export_names


def test_fallback_extracts_imports_as_edges(ts_project):
    """Fallback extracts import edges."""
    result = scan_typescript_fallback(ts_project)
    assert len(result["edges"]) >= 1
    edge = result["edges"][0]
    assert "main" in edge["source"]
    assert "utils" in edge["target"]


def test_fallback_without_tree_sitter(ts_project):
    """Returns empty graph gracefully if tree-sitter not installed."""
    with patch.dict("sys.modules", {"tree_sitter": None, "tree_sitter_typescript": None}):
        result = scan_typescript_fallback(ts_project)
    # Should return empty but valid structure
    assert "units" in result
```

**Step 2: Implement tree-sitter fallback**

```python
"""Tree-sitter based TypeScript/JavaScript scanner (fallback).

Used when Node.js/@arch-model/scanner-js is not available.
Provides degraded output: no type resolution, raw signatures.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def scan_typescript_fallback(root: Path) -> dict[str, Any]:
    """Scan a TS/JS project using tree-sitter (or regex fallback).
    
    Returns a SourceGraph-compatible dict.
    """
    try:
        return _scan_with_tree_sitter(root)
    except (ImportError, Exception):
        return _scan_with_regex(root)


def _scan_with_tree_sitter(root: Path) -> dict[str, Any]:
    """Use tree-sitter-typescript for parsing."""
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language, Parser

    TS_LANGUAGE = Language(ts_typescript.language_typescript())
    parser = Parser(TS_LANGUAGE)
    
    units = []
    edges = []
    
    for ext in ("*.ts", "*.tsx", "*.js", "*.jsx"):
        for filepath in root.rglob(ext):
            if any(p in filepath.parts for p in ("node_modules", "dist", ".git")):
                continue
            rel = str(filepath.relative_to(root))
            content = filepath.read_bytes()
            tree = parser.parse(content)
            
            exports = _extract_exports_ts(tree.root_node, content)
            import_edges = _extract_imports_ts(tree.root_node, content, rel)
            
            units.append({
                "file": rel,
                "has_content": len(exports) > 0,
                "exports": exports,
                "language": "typescript" if ext.startswith("*.ts") else "javascript",
            })
            edges.extend(import_edges)
    
    return {"units": units, "edges": edges, "root": str(root), "language": "typescript"}


def _extract_exports_ts(node, content: bytes) -> list[dict]:
    """Extract exported symbols from tree-sitter AST."""
    exports = []
    text = content.decode("utf-8", errors="replace")
    
    for child in node.children:
        child_text = text[child.start_byte:child.end_byte]
        
        if child.type == "export_statement":
            # export function foo() / export class Bar
            decl = child.child_by_field_name("declaration") or (child.children[1] if len(child.children) > 1 else None)
            if decl:
                if decl.type == "function_declaration":
                    name_node = decl.child_by_field_name("name")
                    if name_node:
                        exports.append({"name": text[name_node.start_byte:name_node.end_byte], "kind": "function", "signature": "", "doc": ""})
                elif decl.type == "class_declaration":
                    name_node = decl.child_by_field_name("name")
                    if name_node:
                        exports.append({"name": text[name_node.start_byte:name_node.end_byte], "kind": "class", "signature": "", "doc": ""})
                elif decl.type in ("lexical_declaration", "variable_declaration"):
                    for declarator in decl.children:
                        if declarator.type == "variable_declarator":
                            name_node = declarator.child_by_field_name("name")
                            if name_node:
                                exports.append({"name": text[name_node.start_byte:name_node.end_byte], "kind": "constant", "signature": "", "doc": ""})
                elif decl.type == "interface_declaration":
                    name_node = decl.child_by_field_name("name")
                    if name_node:
                        exports.append({"name": text[name_node.start_byte:name_node.end_byte], "kind": "interface", "signature": "", "doc": ""})
                elif decl.type == "type_alias_declaration":
                    name_node = decl.child_by_field_name("name")
                    if name_node:
                        exports.append({"name": text[name_node.start_byte:name_node.end_byte], "kind": "type", "signature": "", "doc": ""})
    
    return exports


def _extract_imports_ts(node, content: bytes, source_file: str) -> list[dict]:
    """Extract import statements as dependency edges."""
    edges = []
    text = content.decode("utf-8", errors="replace")
    
    for child in node.children:
        if child.type == "import_statement":
            source_node = child.child_by_field_name("source")
            if source_node:
                module_path = text[source_node.start_byte:source_node.end_byte].strip("'\"")
                if module_path.startswith("."):
                    # Resolve relative path (simplified)
                    symbols = []
                    # Extract named imports
                    for named in child.children:
                        if named.type == "import_clause":
                            for spec in named.children:
                                if spec.type == "named_imports":
                                    for imp_spec in spec.children:
                                        if imp_spec.type == "import_specifier":
                                            name_node = imp_spec.child_by_field_name("name")
                                            if name_node:
                                                symbols.append(text[name_node.start_byte:name_node.end_byte])
                    
                    # Simple path resolution (won't handle all cases)
                    target = _resolve_import_path(source_file, module_path)
                    edges.append({"source": source_file, "target": target, "symbols": symbols})
    
    return edges


def _resolve_import_path(source: str, module_path: str) -> str:
    """Simple relative import resolution."""
    from pathlib import PurePosixPath
    source_dir = str(PurePosixPath(source).parent)
    resolved = str((PurePosixPath(source_dir) / module_path).resolve()).lstrip("/")
    # Add .ts extension if missing
    if not any(resolved.endswith(ext) for ext in (".ts", ".tsx", ".js", ".jsx")):
        resolved += ".ts"
    return resolved


def _scan_with_regex(root: Path) -> dict[str, Any]:
    """Ultra-simple regex fallback when tree-sitter unavailable."""
    units = []
    edges = []
    
    export_fn_re = re.compile(r"export\s+(?:async\s+)?function\s+(\w+)")
    export_class_re = re.compile(r"export\s+class\s+(\w+)")
    export_const_re = re.compile(r"export\s+(?:const|let|var)\s+(\w+)")
    export_interface_re = re.compile(r"export\s+interface\s+(\w+)")
    export_type_re = re.compile(r"export\s+type\s+(\w+)")
    import_re = re.compile(r"import\s+.*?from\s+['\"](\.[^'\"]+)['\"]")
    
    for ext in ("*.ts", "*.tsx", "*.js", "*.jsx"):
        for filepath in root.rglob(ext):
            if any(p in filepath.parts for p in ("node_modules", "dist", ".git")):
                continue
            rel = str(filepath.relative_to(root))
            try:
                text = filepath.read_text(errors="replace")
            except Exception:
                continue
            
            exports = []
            for m in export_fn_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "function", "signature": "", "doc": ""})
            for m in export_class_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "class", "signature": "", "doc": ""})
            for m in export_const_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "constant", "signature": "", "doc": ""})
            for m in export_interface_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "interface", "signature": "", "doc": ""})
            for m in export_type_re.finditer(text):
                exports.append({"name": m.group(1), "kind": "type", "signature": "", "doc": ""})
            
            units.append({
                "file": rel,
                "has_content": len(exports) > 0,
                "exports": exports,
                "language": "typescript" if ext.startswith("*.ts") else "javascript",
            })
            
            for m in import_re.finditer(text):
                target = _resolve_import_path(rel, m.group(1))
                edges.append({"source": rel, "target": target, "symbols": []})
    
    return {"units": units, "edges": edges, "root": str(root), "language": "typescript"}
```

**Step 3: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_ts_scanner.py -v`
Expected: PASS (regex fallback should work without tree-sitter)

**Step 4: Commit**

```bash
git add src/architecture_model/manifest/ts_scanner.py tests/test_ts_scanner.py
git commit -m "feat: add tree-sitter/regex fallback TS scanner for Python environments"
```

---

### Task 3: Wire scanner into CLI + MCP

**Files:**
- Modify: `src/architecture_model/cli/main.py` — add `scan-js` subcommand
- Modify (opencode-arch): `src/opencode_arch/mcp/tools/scan.py` — try Node scanner first

**Step 1: Add scan-js CLI command**

Add to main.py's subparsers:

```python
def _cmd_scan_js(args) -> int:
    """Scan TS/JS project and output source-graph.json."""
    import json
    import subprocess
    from ..manifest.ts_scanner import scan_typescript_fallback

    root = Path(args.path).resolve()
    output = Path(args.output) if args.output else root / ".architecture-models" / "source-graph.json"
    
    # Try Node.js scanner first (better quality)
    try:
        result = subprocess.run(
            ["npx", "@arch-model/scanner-js", str(root), str(output)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"Scanned with @arch-model/scanner-js")
            print(result.stdout)
            return 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback to Python scanner
    print("Using Python fallback scanner (no type resolution)")
    graph = scan_typescript_fallback(root)
    
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, indent=2))
    print(f"  Files: {len(graph['units'])}")
    print(f"  Edges: {len(graph['edges'])}")
    print(f"  Output: {output}")
    return 0
```

**Step 2: Commit**

```bash
git commit -m "feat: add scan-js CLI command with Node.js/fallback detection"
```

# Tree-sitter Kotlin/Java Scanner

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a tree-sitter-based Kotlin/Java scanner to `architecture-model-standard` that produces `SourceGraph` output, enabling the full pipeline (grouping, system detection, behavior inference, etc.) to work on JVM codebases. Then integrate the `knowledge_os_auto` Android app into the logs_db extraction.

**Architecture:** New scanner module that uses tree-sitter Python bindings to parse `.kt`/`.java` files, extract classes, functions, imports, and annotations, then outputs `SourceGraph`. The existing pipeline already consumes `SourceGraph` — no downstream changes needed.

**Tech Stack:** Python 3.12, tree-sitter >= 0.22, tree-sitter-kotlin, tree-sitter-java, pytest.

**Repo:** `architecture-model-standard` at `/Users/baigm2/Documents/Projects/architecture-model-standard/`

**Run tests:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py`

**Target:** `/Users/baigm2/Documents/Projects/logs_db/knowledge_os_auto/` (12 Kotlin source files)

**Key constraints:**
- Optional dependency: scanner gracefully degrades if tree-sitter not installed
- Exclude `build/`, `generated/` directories (like we exclude `__pycache__` for Python)
- Output = `SourceGraph` (language-agnostic protocol already exists)
- Must integrate with `full_extraction()` pipeline (scan all languages → merge SourceGraphs → run pipeline)

---

## Phase 1: Tree-sitter Setup + Kotlin Scanner

### Task 1: Add tree-sitter as optional dependency

**Files:**
- Modify: `pyproject.toml`

Add optional dependency group:
```toml
[project.optional-dependencies]
jvm = ["tree-sitter>=0.22", "tree-sitter-kotlin>=0.1", "tree-sitter-java>=0.1"]
```

Install: `pip install -e ".[jvm]"`

**Step 1: Verify packages exist on PyPI**

```bash
/opt/anaconda3/bin/pip install tree-sitter tree-sitter-kotlin tree-sitter-java
```

Note: tree-sitter Python bindings recently changed API (0.22+ uses `Language` from grammar packages directly). Check which API version is available.

---

### Task 2: Implement Kotlin scanner

**Files:**
- Create: `src/architecture_model/manifest/kt_scanner.py`
- Test: `tests/test_kt_scanner.py`

**Step 1: Write tests**

```python
"""Tests for tree-sitter Kotlin scanner."""
import pytest
from pathlib import Path

try:
    import tree_sitter
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

pytestmark = pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")

from architecture_model.manifest.kt_scanner import scan_kotlin
from architecture_model.manifest.protocol import SourceGraph


class TestKotlinScanner:
    def test_detects_classes(self, tmp_path):
        """Scans Kotlin files and finds class declarations."""
        kt_file = tmp_path / "User.kt"
        kt_file.write_text('''
package com.example.models

class User(val name: String, val email: String) {
    fun displayName(): String = "$name <$email>"
    private fun validate() {}
}

data class Address(val street: String, val city: String)
''')
        graph = scan_kotlin(tmp_path)
        assert len(graph.units) == 1
        exports = graph.units[0].exports
        # Should find User class + displayName method, Address class
        names = {e.name for e in exports}
        assert "User" in names
        assert "Address" in names
        assert "displayName" in names
        assert "validate" not in names  # private

    def test_detects_top_level_functions(self, tmp_path):
        """Scans Kotlin top-level functions."""
        kt_file = tmp_path / "Utils.kt"
        kt_file.write_text('''
package com.example.utils

fun formatDate(date: Long): String {
    return date.toString()
}

internal fun helper() {}
''')
        graph = scan_kotlin(tmp_path)
        exports = graph.units[0].exports
        names = {e.name for e in exports}
        assert "formatDate" in names
        assert "helper" not in names  # internal

    def test_detects_imports_as_edges(self, tmp_path):
        """Import statements become dependency edges."""
        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "User.kt").write_text("package com.example.models\nclass User")
        (tmp_path / "Service.kt").write_text('''
package com.example

import com.example.models.User

class UserService {
    fun getUser(): User = User()
}
''')
        graph = scan_kotlin(tmp_path)
        assert len(graph.edges) >= 1
        # Service.kt imports from models/User.kt
        edge = graph.edges[0]
        assert "Service.kt" in edge.source
        assert "User" in edge.symbols or "models" in edge.target

    def test_excludes_build_dirs(self, tmp_path):
        """Files in build/ directories are excluded."""
        (tmp_path / "build").mkdir()
        (tmp_path / "build" / "Generated.kt").write_text("class Generated")
        (tmp_path / "Main.kt").write_text("class Main")
        graph = scan_kotlin(tmp_path)
        files = {u.file for u in graph.units}
        assert "Main.kt" in files
        assert "build/Generated.kt" not in files

    def test_extracts_annotations(self, tmp_path):
        """Composable and other annotations are captured."""
        kt_file = tmp_path / "Screen.kt"
        kt_file.write_text('''
package com.example.ui

import androidx.compose.runtime.Composable

@Composable
fun HomeScreen() {
    // UI content
}

fun regularFunction() {}
''')
        graph = scan_kotlin(tmp_path)
        exports = graph.units[0].exports
        # Both should be found
        names = {e.name for e in exports}
        assert "HomeScreen" in names
        assert "regularFunction" in names

    def test_real_android_app(self):
        """Scan the actual knowledge_os_auto app."""
        app_path = Path("/Users/baigm2/Documents/Projects/logs_db/knowledge_os_auto/app/src/main")
        if not app_path.exists():
            pytest.skip("Android app not available")
        graph = scan_kotlin(app_path)
        assert len(graph.units) >= 8  # 10 main source files
        assert graph.language == "kotlin"
        # Should find key classes
        all_exports = [e.name for u in graph.units for e in u.exports]
        assert "MainActivity" in all_exports or "KnowledgeOSSession" in all_exports
```

**Step 2: Implement scanner**

```python
"""Tree-sitter based Kotlin scanner producing SourceGraph output."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from architecture_model.manifest.protocol import (
    DependencyEdge, ExportedSymbol, SourceGraph, SourceUnit
)

# Lazy import tree-sitter (optional dependency)
_KOTLIN_LANGUAGE = None

def _get_kotlin_language():
    """Load tree-sitter Kotlin language (cached)."""
    global _KOTLIN_LANGUAGE
    if _KOTLIN_LANGUAGE is None:
        try:
            import tree_sitter_kotlin as tskotlin
            from tree_sitter import Language
            _KOTLIN_LANGUAGE = Language(tskotlin.language())
        except ImportError:
            raise ImportError(
                "tree-sitter-kotlin not installed. Install with: "
                "pip install tree-sitter tree-sitter-kotlin"
            )
    return _KOTLIN_LANGUAGE


# Directories to exclude
EXCLUDE_DIRS = {"build", ".gradle", ".idea", "generated", "ksp", "kspCaches"}


def scan_kotlin(root: Path) -> SourceGraph:
    """Scan Kotlin files in root directory, produce SourceGraph.
    
    Extracts:
    - Class declarations (with public methods)
    - Top-level functions (non-private, non-internal)
    - Import statements → dependency edges
    - Package declarations → for import resolution
    """
    from tree_sitter import Parser
    
    language = _get_kotlin_language()
    parser = Parser(language)
    
    units: list[SourceUnit] = []
    edges: list[DependencyEdge] = []
    package_to_file: dict[str, str] = {}  # package.Class → file
    
    # Find all .kt files
    kt_files = []
    for f in root.rglob("*.kt"):
        if any(excl in f.parts for excl in EXCLUDE_DIRS):
            continue
        kt_files.append(f)
    
    # First pass: index packages
    for filepath in kt_files:
        rel = str(filepath.relative_to(root))
        try:
            source = filepath.read_bytes()
        except Exception:
            continue
        tree = parser.parse(source)
        pkg = _extract_package(tree.root_node, source)
        if pkg:
            package_to_file[pkg] = rel
    
    # Second pass: extract symbols and imports
    for filepath in kt_files:
        rel = str(filepath.relative_to(root))
        try:
            source = filepath.read_bytes()
        except Exception:
            continue
        
        tree = parser.parse(source)
        exports = _extract_exports(tree.root_node, source)
        imports = _extract_imports(tree.root_node, source)
        
        units.append(SourceUnit(
            file=rel,
            has_content=bool(exports),
            exports=exports,
            language="kotlin",
        ))
        
        # Resolve imports to files
        for imp in imports:
            # Try to match import to a known package/file
            target = _resolve_import(imp, package_to_file, rel)
            if target and target != rel:
                edges.append(DependencyEdge(
                    source=rel,
                    target=target,
                    symbols=[imp.split(".")[-1]],
                ))
    
    return SourceGraph(units=units, edges=edges, root=str(root), language="kotlin")


def _extract_package(node, source: bytes) -> str:
    """Extract package declaration from Kotlin file."""
    for child in node.children:
        if child.type == "package_header":
            # Get the identifier
            for c in child.children:
                if c.type == "identifier":
                    return source[c.start_byte:c.end_byte].decode()
    return ""


def _extract_exports(node, source: bytes) -> list[ExportedSymbol]:
    """Extract public classes and functions from AST."""
    exports = []
    
    for child in node.children:
        if child.type == "class_declaration":
            _extract_class(child, source, exports)
        elif child.type == "function_declaration":
            _extract_function(child, source, exports, top_level=True)
        elif child.type == "object_declaration":
            _extract_object(child, source, exports)
    
    return exports


def _is_private_or_internal(node, source: bytes) -> bool:
    """Check if a declaration has private or internal visibility."""
    for child in node.children:
        if child.type == "modifiers":
            text = source[child.start_byte:child.end_byte].decode()
            if "private" in text or "internal" in text:
                return True
    return False


def _extract_class(node, source: bytes, exports: list):
    """Extract class name and public methods."""
    if _is_private_or_internal(node, source):
        return
    
    name = None
    for child in node.children:
        if child.type == "type_identifier":
            name = source[child.start_byte:child.end_byte].decode()
            break
    
    if not name:
        return
    
    # Get constructor signature if present
    sig = ""
    for child in node.children:
        if child.type == "primary_constructor":
            sig = source[child.start_byte:child.end_byte].decode()
            break
    
    exports.append(ExportedSymbol(name=name, kind="class", signature=sig))
    
    # Extract public methods
    for child in node.children:
        if child.type == "class_body":
            for member in child.children:
                if member.type == "function_declaration":
                    _extract_function(member, source, exports, top_level=False)


def _extract_function(node, source: bytes, exports: list, top_level: bool):
    """Extract function name and signature."""
    if _is_private_or_internal(node, source):
        return
    
    name = None
    for child in node.children:
        if child.type == "simple_identifier":
            name = source[child.start_byte:child.end_byte].decode()
            break
    
    if not name:
        return
    
    # Get parameter list for signature
    sig = ""
    for child in node.children:
        if child.type == "function_value_parameters":
            sig = source[child.start_byte:child.end_byte].decode()
            break
    
    exports.append(ExportedSymbol(
        name=name,
        kind="function",
        signature=sig,
    ))


def _extract_object(node, source: bytes, exports: list):
    """Extract Kotlin object declarations."""
    if _is_private_or_internal(node, source):
        return
    name = None
    for child in node.children:
        if child.type == "type_identifier":
            name = source[child.start_byte:child.end_byte].decode()
            break
    if name:
        exports.append(ExportedSymbol(name=name, kind="class", signature="object"))


def _extract_imports(node, source: bytes) -> list[str]:
    """Extract import statements."""
    imports = []
    for child in node.children:
        if child.type == "import_list":
            for imp in child.children:
                if imp.type == "import_header":
                    for c in imp.children:
                        if c.type == "identifier":
                            imports.append(source[c.start_byte:c.end_byte].decode())
    return imports


def _resolve_import(imp: str, package_map: dict[str, str], current_file: str) -> str | None:
    """Resolve an import string to a file path using package map."""
    # Try exact package match
    if imp in package_map:
        return package_map[imp]
    # Try parent package (import com.example.models.User → package com.example.models)
    parts = imp.rsplit(".", 1)
    if len(parts) == 2 and parts[0] in package_map:
        return package_map[parts[0]]
    return None
```

---

### Task 3: Implement Java scanner (minimal)

**Files:**
- Modify: `src/architecture_model/manifest/kt_scanner.py` (add `scan_java()`)

Same pattern as Kotlin but with Java grammar. Java-specific differences:
- No top-level functions (everything in classes)
- `public`/`private`/`protected` keywords explicit
- Package in `package com.example;` (with semicolons)
- Different tree-sitter node types

```python
def scan_java(root: Path) -> SourceGraph:
    """Scan Java files in root directory, produce SourceGraph."""
    ...
```

Since the Android app is Kotlin-only (the only `.java` is a BuildConfig), this is lower priority. Can be a stub that delegates to regex if needed.

---

### Task 4: Create unified multi-language scanner

**Files:**
- Create: `src/architecture_model/manifest/multi_scanner.py`
- Test: `tests/test_multi_scanner.py`

```python
"""Multi-language scanner that merges SourceGraphs from all detected languages."""
from pathlib import Path
from architecture_model.manifest.protocol import SourceGraph, SourceUnit, DependencyEdge


def scan_all_languages(root: Path) -> SourceGraph:
    """Scan repository for all supported languages, return merged SourceGraph.
    
    Detects languages by file extension:
    - .py → Python (via existing generate_manifest → SourceGraph.from_manifest)
    - .kt → Kotlin (via scan_kotlin)
    - .java → Java (via scan_java)  
    - .ts/.tsx/.js/.jsx → TypeScript (via scan_typescript_fallback)
    
    Returns a single merged SourceGraph with all languages.
    Cross-language edges are NOT detected (would require interface contract analysis).
    """
    graphs: list[SourceGraph] = []
    
    # Python
    py_files = list(root.rglob("*.py"))
    if py_files:
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(root)
        graphs.append(SourceGraph.from_manifest(manifest))
    
    # Kotlin
    kt_files = [f for f in root.rglob("*.kt") 
                if "build" not in f.parts and "generated" not in f.parts]
    if kt_files:
        try:
            from architecture_model.manifest.kt_scanner import scan_kotlin
            # Find Kotlin source root (typically app/src/main or src/main/kotlin)
            kt_root = _find_kotlin_root(root)
            if kt_root:
                graphs.append(scan_kotlin(kt_root))
        except ImportError:
            pass  # tree-sitter not installed, skip
    
    # TypeScript (if present)
    ts_files = list(root.rglob("*.ts")) + list(root.rglob("*.tsx"))
    if ts_files:
        from architecture_model.manifest.ts_scanner import scan_typescript_fallback
        ts_data = scan_typescript_fallback(root)
        graphs.append(SourceGraph.from_json(ts_data))
    
    # Merge all graphs
    return _merge_graphs(graphs)


def _find_kotlin_root(repo_root: Path) -> Path | None:
    """Find the Kotlin source root in an Android project."""
    candidates = [
        repo_root / "app" / "src" / "main",
        repo_root / "src" / "main" / "kotlin",
        repo_root / "src" / "main" / "java",  # Kotlin files often in java/ dir
    ]
    # Also search for any directory named knowledge_os_auto or similar
    for child in repo_root.iterdir():
        if child.is_dir() and (child / "app" / "src" / "main").exists():
            candidates.insert(0, child / "app" / "src" / "main")
    
    for c in candidates:
        if c.exists():
            return c
    return None


def _merge_graphs(graphs: list[SourceGraph]) -> SourceGraph:
    """Merge multiple SourceGraphs into one."""
    all_units: list[SourceUnit] = []
    all_edges: list[DependencyEdge] = []
    languages: set[str] = set()
    
    for g in graphs:
        all_units.extend(g.units)
        all_edges.extend(g.edges)
        if g.language:
            languages.add(g.language)
    
    return SourceGraph(
        units=all_units,
        edges=all_edges,
        language="+".join(sorted(languages)) if len(languages) > 1 else (languages.pop() if languages else ""),
    )
```

---

## Phase 2: Integration with Full Extraction Pipeline

### Task 5: Update full_extraction() to use multi-language scanner

**Files:**
- Modify: `src/architecture_model/orchestration/full_extraction.py`

Instead of calling `generate_manifest(repo)` only, call `scan_all_languages(repo)` to get a unified SourceGraph, then convert to Manifest format for downstream consumers (or adapt pipeline to work directly on SourceGraph where possible).

**Key integration point:** The existing pipeline uses `Manifest` (Python-specific) in many places. The SourceGraph-based grouping (`group_source_graph()` at line 502 of grouping.py) already exists. Route through SourceGraph path when non-Python files are detected.

---

### Task 6: Run on logs_db with Android app included

```bash
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.manifest.multi_scanner import scan_all_languages

repo = Path('/Users/baigm2/Documents/Projects/logs_db')
graph = scan_all_languages(repo)

print(f'Total units: {len(graph.units)}')
print(f'Languages: {graph.language}')

# Show Kotlin units
kt_units = [u for u in graph.units if u.language == 'kotlin']
print(f'\nKotlin files: {len(kt_units)}')
for u in kt_units:
    exports = [e.name for e in u.exports]
    print(f'  {u.file}: {exports}')
"
```

Expected: Python files (~120) + Kotlin files (~10) in one unified SourceGraph. The system detector should then identify the Android app as its own system (very high independence — different language, different directory, clear API boundary via HTTP to the backend).

---

## Phase 3: Cross-Language Interface Detection

### Task 7: Detect API contract boundaries between languages

**Files:**
- Create: `src/architecture_model/orchestration/cross_language.py`
- Test: `tests/test_cross_language.py`

**Concept:** The Android app communicates with the Python backend via HTTP API. Detect this boundary by:
1. Kotlin side: find Retrofit/OkHttp interface definitions or URL strings
2. Python side: find matching router endpoints
3. Create `Interface` entities representing the API contract between systems

```python
def detect_cross_language_interfaces(
    graph: SourceGraph,
    model: ArchitectureModel,
) -> list[Interface]:
    """Detect API boundaries between language-specific systems.
    
    Heuristic: if a Kotlin file references URL paths that match Python router endpoints,
    that's a cross-language interface.
    """
    ...
```

This is the most complex task — may need to read actual Kotlin source to find API base URLs or Retrofit interface definitions. Could be Phase 2 of a future plan if too complex.

---

## Summary

| Phase | Tasks | What | New Code |
|-------|-------|------|----------|
| 1 | 1-4 | Tree-sitter Kotlin/Java scanner + multi-language merger | `kt_scanner.py`, `multi_scanner.py` |
| 2 | 5-6 | Integration with full_extraction pipeline | Modify `full_extraction.py` |
| 3 | 7 | Cross-language API interface detection | `cross_language.py` (optional/future) |

**New modules:**
- `src/architecture_model/manifest/kt_scanner.py` — tree-sitter Kotlin + Java scanner
- `src/architecture_model/manifest/multi_scanner.py` — unified multi-language scanner
- `src/architecture_model/orchestration/cross_language.py` — API boundary detection

**Dependencies added (optional):**
- `tree-sitter >= 0.22`
- `tree-sitter-kotlin >= 0.1`
- `tree-sitter-java >= 0.1`

**Expected logs_db output with Android:**
- Python: ~120 modules (existing)
- Kotlin: ~10 modules (new)
- Systems: Android App should be its own system (highest independence — different language, directory, no import coupling to Python)
- Cross-language interface: HTTP API contract between Android ↔ Python backend

**Android app structure (knowledge_os_auto):**
| File | Purpose |
|------|---------|
| `MainActivity.kt` | App entry point |
| `KnowledgeOSCarAppService.kt` | Android Auto service |
| `KnowledgeOSSession.kt` | Session management |
| `screens/ProjectListScreen.kt` | Project list UI |
| `screens/ProjectDetailScreen.kt` | Project detail UI |
| `screens/ProjectConversationScreen.kt` | Conversation UI |
| `screens/VoiceInputScreen.kt` | Voice input UI |
| `messaging/MessagingService.kt` | Push notifications |
| `messaging/ReplyReceiver.kt` | Notification reply |
| `messaging/NotificationHelper.kt` | Notification builder |

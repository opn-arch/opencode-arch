# Fix Module Grouping Algorithm

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix `group_modules()` to produce meaningful 5-12 groups instead of mostly singletons or one mega-group.

**Architecture:** Three-pronged fix: (1) add name-prefix pre-grouping so flat packages get initial clusters, (2) use normalized affinity scoring (Jaccard-like) to prevent mega-group attraction, (3) fix auto-target formula to always trigger merging.

**Tech Stack:** Python, pytest. Primary file: `architecture-model-standard/src/architecture_model/manifest/grouping.py`

**Run tests:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py` in `/Users/baigm2/Documents/Projects/architecture-model-standard/`

---

### Task 1: Write failing tests for name-prefix pre-grouping

**Files:**
- Modify: `tests/test_module_grouping.py`

**Step 1: Write the failing tests**

Add a new test class that verifies name-prefix grouping works for flat packages. Use the existing `_mod()` helper already in the test file:

```python
class TestNamePrefixPreGrouping:
    """Name-prefix affinity: files sharing a prefix get pre-grouped."""

    def test_shared_prefix_groups_together(self):
        """auth_login.py + auth_utils.py + auth_middleware.py → one group."""
        modules = [
            _mod("src/app/auth_login.py", funcs=["login"]),
            _mod("src/app/auth_utils.py", funcs=["hash_pw"]),
            _mod("src/app/auth_middleware.py", funcs=["check"]),
            _mod("src/app/db_connection.py", funcs=["connect"]),
            _mod("src/app/db_queries.py", funcs=["query"]),
            _mod("src/app/server.py", funcs=["start"]),
        ]
        groups = group_modules(modules, [])
        # Should get ~3 groups: auth (3 files), db (2 files), server (1 file)
        assert len(groups) <= 4
        auth_group = next(g for g in groups if any("auth" in f for f in g.modules))
        assert len(auth_group.modules) == 3

    def test_single_char_prefix_not_grouped(self):
        """Single-char prefixes (a_foo, a_bar) should NOT trigger grouping."""
        modules = [
            _mod("src/app/a_foo.py", funcs=["foo"]),
            _mod("src/app/a_bar.py", funcs=["bar"]),
            _mod("src/app/baz.py", funcs=["baz"]),
        ]
        groups = group_modules(modules, [])
        # All singletons (prefix "a" too short to be meaningful)
        assert len(groups) == 3

    def test_prefix_needs_two_plus_files(self):
        """A prefix with only one file doesn't form a group."""
        modules = [
            _mod("src/app/auth_login.py", funcs=["login"]),
            _mod("src/app/db_conn.py", funcs=["connect"]),
            _mod("src/app/db_pool.py", funcs=["pool"]),
        ]
        groups = group_modules(modules, [])
        db_group = next(g for g in groups if any("db_" in f for f in g.modules))
        assert len(db_group.modules) == 2
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py::TestNamePrefixPreGrouping -v`
Expected: FAIL (current algo produces singletons for flat packages)

**Step 3: Commit**

```bash
git add tests/test_module_grouping.py
git commit -m "test: add failing tests for name-prefix pre-grouping"
```

---

### Task 2: Write failing tests for normalized affinity scoring

**Files:**
- Modify: `tests/test_module_grouping.py`

**Step 1: Write the failing tests**

```python
class TestNormalizedAffinity:
    """Normalized scoring prevents mega-group attraction."""

    def test_no_mega_group_with_target(self):
        """With target_groups=4, should NOT produce one group with >60% of files."""
        modules = [_mod(f"src/app/mod_{i}.py", funcs=[f"fn_{i}"]) for i in range(20)]
        # Create import clusters: 0-4, 5-9, 10-14, 15-19
        interfaces = []
        for cluster_start in range(0, 20, 5):
            for i in range(cluster_start, cluster_start + 5):
                for j in range(i + 1, cluster_start + 5):
                    interfaces.append(InterfaceEdge(
                        source=f"src/app/mod_{i}.py",
                        target=f"src/app/mod_{j}.py",
                        import_path="",
                    ))
        groups = group_modules(modules, interfaces, target_groups=4)
        assert len(groups) == 4
        # No single group should have more than 8 files
        assert all(len(g.modules) <= 8 for g in groups)

    def test_clusters_preserved(self):
        """Import clusters should be kept together, not split."""
        modules = [_mod(f"src/app/mod_{i}.py", funcs=[f"fn_{i}"]) for i in range(12)]
        # 3 clusters of 4 with dense internal imports
        interfaces = []
        for cluster_start in range(0, 12, 4):
            for i in range(cluster_start, cluster_start + 4):
                for j in range(i + 1, cluster_start + 4):
                    interfaces.append(InterfaceEdge(
                        source=f"src/app/mod_{i}.py",
                        target=f"src/app/mod_{j}.py",
                        import_path="",
                    ))
        groups = group_modules(modules, interfaces, target_groups=3)
        assert len(groups) == 3
        sizes = sorted(len(g.modules) for g in groups)
        assert sizes == [4, 4, 4]
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py::TestNormalizedAffinity -v`
Expected: FAIL

**Step 3: Commit**

```bash
git add tests/test_module_grouping.py
git commit -m "test: add failing tests for normalized affinity scoring"
```

---

### Task 3: Write failing test for auto-target fix

**Files:**
- Modify: `tests/test_module_grouping.py`

**Step 1: Write the failing test**

```python
class TestAutoTargetFix:
    """Auto-target always triggers meaningful merging."""

    def test_eight_modules_get_merged(self):
        """8 flat modules with imports should merge, not stay as 8 singletons."""
        modules = [_mod(f"src/app/{name}.py", funcs=["fn"]) for name in [
            "auth", "users", "posts", "comments", "db", "cache", "config", "server"
        ]]
        # auth↔users, posts↔comments, db↔cache — 3 natural pairs + 2 singletons
        interfaces = [
            InterfaceEdge(source="src/app/auth.py", target="src/app/users.py", import_path=""),
            InterfaceEdge(source="src/app/users.py", target="src/app/auth.py", import_path=""),
            InterfaceEdge(source="src/app/posts.py", target="src/app/comments.py", import_path=""),
            InterfaceEdge(source="src/app/comments.py", target="src/app/posts.py", import_path=""),
            InterfaceEdge(source="src/app/db.py", target="src/app/cache.py", import_path=""),
        ]
        groups = group_modules(modules, interfaces)
        # Should merge to ~5 groups (3 pairs + 2 singletons), not stay at 8
        assert len(groups) <= 6
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py::TestAutoTargetFix -v`
Expected: FAIL (current auto-target for 8 modules = max(8, 3) = 8)

**Step 3: Commit**

```bash
git add tests/test_module_grouping.py
git commit -m "test: add failing test for auto-target formula"
```

---

### Task 4: Implement name-prefix pre-grouping

**Files:**
- Modify: `src/architecture_model/manifest/grouping.py`

**Step 1: Add `_group_by_prefix` helper (after `_is_subdirectory_group`)**

```python
def _group_by_prefix(files: list[str]) -> dict[str, list[str]]:
    """Group files by shared name prefix (minimum 2 chars before first underscore).
    
    Examples:
        auth_login.py, auth_utils.py → prefix "auth"
        db_connection.py, db_pool.py → prefix "db"
        server.py → no prefix (no underscore)
        a_foo.py → no prefix (single char too short)
    """
    prefix_map: dict[str, list[str]] = defaultdict(list)
    no_prefix: list[str] = []
    
    for f in files:
        stem = PurePosixPath(f).stem.lstrip("_")
        if "_" in stem:
            prefix = stem.split("_", 1)[0]
            if len(prefix) >= 2:
                prefix_map[prefix].append(f)
            else:
                no_prefix.append(f)
        else:
            no_prefix.append(f)
    
    # Only keep prefixes with 2+ files
    result: dict[str, list[str]] = {}
    for prefix, pfiles in prefix_map.items():
        if len(pfiles) >= 2:
            result[prefix] = pfiles
        else:
            no_prefix.extend(pfiles)
    
    if no_prefix:
        result[""] = no_prefix
    return result
```

**Step 2: Update the `else` branch in initial grouping (line 128-133)**

Replace:
```python
        else:
            # Default: each file gets its own group
            for f in files:
                stem = PurePosixPath(f).stem
                name = stem.lstrip("_").replace("_", " ").title().replace(" ", "")
                initial_groups.append((name, [f], False))
```

With:
```python
        else:
            # Name-prefix grouping: files sharing a multi-char prefix get pre-grouped
            prefix_groups = _group_by_prefix(files)
            for prefix, pfiles in prefix_groups.items():
                if prefix and len(pfiles) >= 2:
                    name = prefix.replace("_", " ").title().replace(" ", "")
                    initial_groups.append((name, pfiles, False))
                else:
                    for f in pfiles:
                        stem = PurePosixPath(f).stem
                        name = stem.lstrip("_").replace("_", " ").title().replace(" ", "")
                        initial_groups.append((name, [f], False))
```

**Step 3: Run prefix tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py::TestNamePrefixPreGrouping -v`
Expected: PASS

**Step 4: Run all grouping tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py -v`
Expected: Mostly pass (some old tests may need adjustment in Task 7)

**Step 5: Commit**

```bash
git add src/architecture_model/manifest/grouping.py
git commit -m "feat: add name-prefix pre-grouping for flat packages"
```

---

### Task 5: Implement normalized affinity scoring

**Files:**
- Modify: `src/architecture_model/manifest/grouping.py`

**Step 1: Replace `_merge_by_import_affinity` and `_cross_edge_count`**

Delete `_cross_edge_count` (lines 230-239). Replace `_merge_by_import_affinity` (lines 185-227):

```python
def _merge_by_import_affinity(
    groups: list[tuple[str, list[str]]],
    interfaces: list[InterfaceEdge],
    target: int,
) -> list[tuple[str, list[str]]]:
    """Iteratively merge groups with highest normalized import affinity."""
    # Build edge set between file pairs
    edges: set[tuple[str, str]] = set()
    for iface in interfaces:
        key = (min(iface.source, iface.target), max(iface.source, iface.target))
        edges.add(key)

    groups = list(groups)

    while len(groups) > target:
        best_score = -1.0
        best_pair = (0, 1)

        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                score = _normalized_affinity(groups[i][1], groups[j][1], edges)
                if score > best_score:
                    best_score = score
                    best_pair = (i, j)

        # If no import affinity, merge two smallest groups
        if best_score <= 0:
            sizes = [(len(g[1]), idx) for idx, g in enumerate(groups)]
            sizes.sort()
            best_pair = (sizes[0][1], sizes[1][1])

        i, j = best_pair
        merged_name = groups[i][0] if len(groups[i][1]) >= len(groups[j][1]) else groups[j][0]
        merged_files = groups[i][1] + groups[j][1]
        groups[i] = (merged_name, merged_files)
        groups.pop(j)

    return groups


def _normalized_affinity(
    files_a: list[str], files_b: list[str], edges: set[tuple[str, str]]
) -> float:
    """Normalized affinity: actual_edges / possible_edges between two groups.
    
    Prevents large groups from always winning since more files = more 
    possible edges = lower score unless connections are dense.
    """
    possible = len(files_a) * len(files_b)
    if possible == 0:
        return 0.0
    
    actual = 0
    for a in files_a:
        for b in files_b:
            key = (min(a, b), max(a, b))
            if key in edges:
                actual += 1
    
    return actual / possible
```

**Step 2: Run normalized affinity tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py::TestNormalizedAffinity -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/architecture_model/manifest/grouping.py
git commit -m "feat: use normalized affinity scoring to prevent mega-groups"
```

---

### Task 6: Fix auto-target formula

**Files:**
- Modify: `src/architecture_model/manifest/grouping.py`

**Step 1: Replace auto-target block (lines 136-148)**

Replace:
```python
    if target_groups is None:
        n_unlocked = sum(1 for _, _, locked in initial_groups if not locked)
        n_locked = sum(1 for _, _, locked in initial_groups if locked)
        # Aggressive merging: aim for 5-15 total groups regardless of module count
        if n_unlocked <= 10:
            target_unlocked = max(n_unlocked, 3)
        else:
            # sqrt scaling: 100 modules → ~10 groups, 400 → ~20
            import math
            target_unlocked = max(5, min(15, int(math.sqrt(n_unlocked) * 1.2)))
        target_groups = target_unlocked + n_locked
        # Hard cap: never exceed 20 total groups (agents can't reason about more)
        target_groups = min(target_groups, 20)
```

With:
```python
    if target_groups is None:
        n_unlocked = sum(1 for _, _, locked in initial_groups if not locked)
        n_locked = sum(1 for _, _, locked in initial_groups if locked)
        # Always merge: sqrt(n) * 0.8, clamped to [3, 12]
        # 4→3, 8→2→3, 16→3, 25→4, 64→6, 100→8, 144→9, 200→11
        if n_unlocked <= 3:
            target_unlocked = n_unlocked
        else:
            target_unlocked = max(3, min(12, int(math.sqrt(n_unlocked) * 0.8)))
        target_groups = target_unlocked + n_locked
        target_groups = min(target_groups, 15)
```

**Step 2: Run auto-target test**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py::TestAutoTargetFix -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/architecture_model/manifest/grouping.py
git commit -m "feat: fix auto-target to always merge for >3 modules"
```

---

### Task 7: Fix any broken existing tests

**Files:**
- Modify: `tests/test_module_grouping.py`

**Step 1: Run full grouping test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py -v`

**Step 2: Fix failing assertions**

Likely failures:
- `TestAutoTargetGroups` — old formula assertions need updating
- `TestImportAffinityMerging` — may expect different merge behavior
- `TestNamePrefixGrouping` — the old underscore-prefix test may conflict

Update test assertions to match new (correct) behavior. Keep test intent.

**Step 3: Run again until all pass**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_module_grouping.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/test_module_grouping.py
git commit -m "fix: update existing grouping tests for new algorithm"
```

---

### Task 8: Run full test suite + validate on real repos

**Step 1: Run full architecture-model-standard tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py`
Expected: 880+ pass, no new failures

**Step 2: Validate grouping on logs_db**

```bash
/opt/anaconda3/bin/python -c "
import sys; sys.path.insert(0, 'src')
from pathlib import Path
from architecture_model.manifest.generator import generate_manifest
from architecture_model.manifest.grouping import group_modules
m = generate_manifest(Path('/Users/baigm2/Documents/Projects/logs_db'))
groups = group_modules(m.modules, m.interfaces)
for g in groups: print(f'{g.name}: {len(g.modules)} files')
print(f'Total: {len(groups)} groups from {len([mod for mod in m.modules])} modules')
"
```

Expected: 5-10 meaningful groups (NOT 118 singletons)

**Step 3: Validate on architecture-model-standard itself**

Same script with `/Users/baigm2/Documents/Projects/architecture-model-standard`
Expected: 5-10 groups (NOT 62 singletons)

**Step 4: Validate on opencode-arch**

Same with `/Users/baigm2/Documents/Projects/opencode-arch`
Expected: 5-10 groups

**Step 5: If results are poor, iterate on thresholds/scoring**

---

## Summary of Changes

| What | Why |
|------|-----|
| Name-prefix pre-grouping (`_group_by_prefix`) | Flat packages get initial clusters (auth_*, db_*, etc.) |
| Normalized affinity (actual/possible edges) | Prevents mega-group attraction |
| Auto-target = sqrt(n)*0.8 clamped [3,12] | Always triggers merging for >3 modules |
| Hard cap reduced 20→15 | Agents can't reason about 15+ groups |

**Expected outcome:** All 3 repos produce 5-10 meaningful groups with positive modularity.

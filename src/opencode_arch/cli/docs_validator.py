"""Validate generated SE documentation against model and manifest."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


@dataclass
class ValidationIssue:
    """A single validation issue found in a doc artifact."""
    artifact_id: str       # which artifact had the issue
    line: int              # line number in the doc (1-indexed, 0 if unknown)
    issue_type: str        # "invalid_path", "unknown_function", "unknown_component", "stale_reference"
    message: str           # human-readable description
    severity: str          # "error" or "warning"


@dataclass
class DocsValidationResult:
    """Aggregate validation result for all docs."""
    total_artifacts: int
    passed: int
    failed: int
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """No errors (warnings are OK)."""
        return not any(i.severity == "error" for i in self.issues)


# File extensions we recognize as code/config paths
_PATH_EXTENSIONS = (
    ".py", ".ts", ".js", ".jsx", ".tsx",
    ".yaml", ".yml", ".json", ".toml",
    ".cfg", ".ini", ".md", ".rst",
    ".sh", ".bash", ".sql",
)

# Regex for backtick-wrapped file paths: must contain a slash or end with known extension
_FILE_REF_PATTERN = re.compile(
    r"`([^`\s]+(?:" + "|".join(re.escape(ext) for ext in _PATH_EXTENSIONS) + r"))`"
)

# Regex for backtick-wrapped function calls: word followed by ()
_FUNC_REF_PATTERN = re.compile(r"`(\w+)\(\)`")

# Regex for backtick-wrapped PascalCase class names: starts uppercase, has at least one lowercase
_CLASS_REF_PATTERN = re.compile(r"`([A-Z][a-zA-Z0-9]*)`")

# Regex for component-like IDs (e.g., COMP-1, SVC-1, IF-1, CAP-1)
_COMPONENT_ID_PATTERN = re.compile(r"\b([A-Z]{2,}-\d+)\b")


def validate_docs(
    docs_dir: Path,
    model: "ArchitectureModel",
    manifest: dict | None = None,
) -> DocsValidationResult:
    """Validate all markdown files in docs_dir against model and manifest.

    Checks:
    1. File paths mentioned in docs exist in manifest's file inventory
    2. Function/class names referenced exist in manifest's AST data
    3. Component IDs/names referenced match model's components
    4. Interface names referenced match model's interfaces

    An artifact PASSES if it has no "error" severity issues.
    """
    docs_dir = Path(docs_dir)
    md_files = sorted(docs_dir.glob("*.md"))

    if not md_files:
        return DocsValidationResult(total_artifacts=0, passed=0, failed=0)

    # Build lookup sets
    manifest_files = _get_manifest_files(manifest)
    manifest_symbols = _get_manifest_symbols(manifest)
    model_ids = _get_model_entity_ids(model)

    all_issues: list[ValidationIssue] = []
    passed = 0
    failed = 0

    for md_file in md_files:
        content = md_file.read_text()
        artifact_id = _get_artifact_id_from_file(md_file)
        artifact_issues: list[ValidationIssue] = []

        # Check 1: File path references (only if manifest available)
        if manifest is not None:
            file_refs = _extract_file_references(content)
            for line_no, path_ref in file_refs:
                if path_ref not in manifest_files:
                    artifact_issues.append(ValidationIssue(
                        artifact_id=artifact_id,
                        line=line_no,
                        issue_type="invalid_path",
                        message=f"File path '{path_ref}' not found in manifest",
                        severity="error",
                    ))

        # Check 2: Function/class references (only if manifest available)
        if manifest is not None:
            code_refs = _extract_code_references(content)
            for line_no, name_ref in code_refs:
                if name_ref not in manifest_symbols:
                    artifact_issues.append(ValidationIssue(
                        artifact_id=artifact_id,
                        line=line_no,
                        issue_type="unknown_function",
                        message=f"Symbol '{name_ref}' not found in manifest",
                        severity="warning",
                    ))

        # Check 3: Component/entity ID references (always check against model)
        comp_refs = _extract_component_references(content, model)
        for line_no, comp_ref in comp_refs:
            if comp_ref not in model_ids:
                artifact_issues.append(ValidationIssue(
                    artifact_id=artifact_id,
                    line=line_no,
                    issue_type="unknown_component",
                    message=f"Entity ID '{comp_ref}' not found in model",
                    severity="error",
                ))

        all_issues.extend(artifact_issues)

        # Artifact passes if no errors
        has_errors = any(i.severity == "error" for i in artifact_issues)
        if has_errors:
            failed += 1
        else:
            passed += 1

    return DocsValidationResult(
        total_artifacts=len(md_files),
        passed=passed,
        failed=failed,
        issues=all_issues,
    )


def _extract_file_references(content: str) -> list[tuple[int, str]]:
    """Extract file path references from markdown content.

    Looks for patterns like:
    - `src/foo/bar.py` (backtick-wrapped paths ending in known extensions)
    - References to .py, .ts, .js, .yaml, .json, .toml files

    Returns: list of (line_number, path_string)
    """
    results = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in _FILE_REF_PATTERN.finditer(line):
            results.append((line_no, match.group(1)))
    return results


def _extract_code_references(content: str) -> list[tuple[int, str]]:
    """Extract function/class name references from markdown.

    Looks for patterns like:
    - `function_name()` (backtick-wrapped with parens)
    - `ClassName` (backtick-wrapped PascalCase)

    Returns: list of (line_number, name_string)
    """
    results = []
    seen_on_line: dict[int, set[str]] = {}

    for line_no, line in enumerate(content.splitlines(), start=1):
        seen_on_line[line_no] = set()

        # Extract function calls: `name()`
        for match in _FUNC_REF_PATTERN.finditer(line):
            name = match.group(1)
            if name not in seen_on_line[line_no]:
                results.append((line_no, name))
                seen_on_line[line_no].add(name)

        # Extract PascalCase class names: `ClassName`
        for match in _CLASS_REF_PATTERN.finditer(line):
            name = match.group(1)
            # Skip if it looks like a file path (already caught by file refs)
            if "." in name or "/" in name:
                continue
            # Must have at least one lowercase letter to be PascalCase
            if not any(c.islower() for c in name):
                # All-caps short names (2-3 chars like CLI) are still valid class names
                if len(name) <= 4:
                    if name not in seen_on_line[line_no]:
                        results.append((line_no, name))
                        seen_on_line[line_no].add(name)
                continue
            if name not in seen_on_line[line_no]:
                results.append((line_no, name))
                seen_on_line[line_no].add(name)

    return results


def _extract_component_references(content: str, model: "ArchitectureModel") -> list[tuple[int, str]]:
    """Extract component ID/name references that should match the model.

    Looks for known component ID patterns (e.g., COMP-1, SVC-1, IF-1) in text.
    Returns: list of (line_number, component_ref)
    """
    results = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in _COMPONENT_ID_PATTERN.finditer(line):
            results.append((line_no, match.group(1)))
    return results


def _get_manifest_files(manifest: dict | None) -> set[str]:
    """Get the set of all file paths from manifest.

    Checks manifest["modules"] -> each module has "file" key
    Also checks manifest.get("files", [])
    Returns normalized relative paths.
    """
    if manifest is None:
        return set()

    files: set[str] = set()

    # From modules
    for module in manifest.get("modules", []):
        if "file" in module:
            files.add(module["file"])

    # From top-level files list
    for f in manifest.get("files", []):
        files.add(f)

    return files


def _get_manifest_symbols(manifest: dict | None) -> set[str]:
    """Get all function/class names from manifest AST data.

    Checks manifest["modules"] -> each module may have "functions", "classes" keys
    Returns set of symbol names.
    """
    if manifest is None:
        return set()

    symbols: set[str] = set()

    for module in manifest.get("modules", []):
        for func in module.get("functions", []):
            symbols.add(func)
        for cls in module.get("classes", []):
            symbols.add(cls)

    return symbols


def _get_model_entity_ids(model: "ArchitectureModel") -> set[str]:
    """Get all entity IDs from the architecture model."""
    return model.all_entity_ids


def _get_artifact_id_from_file(filepath: Path) -> str:
    """Extract artifact_id from file frontmatter or filename.

    Tries to read YAML frontmatter first:
    ---
    artifact_id: system-overview
    ---

    Falls back to: filename without extension (e.g., "system-overview.md" -> "system-overview")
    """
    try:
        content = filepath.read_text()
        if content.startswith("---\n"):
            # Try to parse frontmatter
            parts = content.split("---\n", 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1])
                if isinstance(frontmatter, dict) and "artifact_id" in frontmatter:
                    return frontmatter["artifact_id"]
    except Exception:
        pass

    # Fallback to filename without extension
    return filepath.stem

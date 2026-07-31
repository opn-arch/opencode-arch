"""Calibration command - spot-check confidence by attempting regeneration."""
from __future__ import annotations

import ast
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from architecture_model.core.types import ArchitectureModel, Component


@dataclass
class CalibrationReport:
    """Result of a calibration run."""

    components_tested: int
    correlation: float
    bands: dict  # confidence_band → regen_success_rate
    threshold: float  # recommended confidence for safe regeneration


def select_calibration_targets(
    model_or_components, *, n: int = 3, min_confidence: float = 0.7, count: int = 6
):
    """Select components for calibration.
    
    Supports two calling conventions:
    - Legacy: select_calibration_targets(model, n=3, min_confidence=0.7) with ArchitectureModel
    - New: select_calibration_targets(components, count=6) with list[dict]
    """
    if isinstance(model_or_components, list):
        # New dict-based interface (Task 6)
        components = model_or_components
        if not components:
            return []
        sorted_comps = sorted(components, key=lambda c: c.get("confidence", 0))
        num = len(sorted_comps)
        if num <= count:
            return sorted_comps
        indices = [round(i * (num - 1) / (count - 1)) for i in range(count)]
        return [sorted_comps[i] for i in indices]
    else:
        # Legacy ArchitectureModel interface
        model = model_or_components
        candidates = [c for c in model.entities.components if c.confidence >= min_confidence and c.files]
        if not candidates:
            candidates = [c for c in model.entities.components if c.files]
        random.shuffle(candidates)
        return candidates[:n]


def format_calibration_prompt(comp: Component) -> str:
    """Format a prompt asking the agent to regenerate a component from its model spec."""
    sections = []
    sections.append(f"## Regenerate: {comp.name} ({comp.id})")
    sections.append("")
    sections.append(f"**Contract:** {comp.contract or 'Not specified'}")
    sections.append(f"**Pattern:** {comp.pattern or 'Not specified'}")
    sections.append(f"**Files:** {', '.join(comp.files)}")

    if comp.responsibilities:
        sections.append(f"**Responsibilities:** {'; '.join(comp.responsibilities)}")

    if comp.signatures:
        sections.append("\n**Signatures:**")
        for sig in comp.signatures:
            params = ", ".join(sig.params) if sig.params else ""
            ret = f" -> {sig.returns}" if sig.returns else ""
            decorators = " ".join(f"@{d}" for d in sig.decorators) + " " if sig.decorators else ""
            sections.append(f"  {decorators}def {sig.name}({params}){ret}")
            if sig.body_hint:
                sections.append(f"    # Hint: {sig.body_hint}")

    if comp.symbols:
        sections.append("\n**Classes:**")
        for sym in comp.symbols:
            bases = f"({', '.join(sym.supers)})" if sym.supers else ""
            sections.append(f"  class {sym.name}{bases}")
            if sym.members:
                for m in sym.members[:10]:
                    sections.append(f"    - {m}")

    if comp.constants:
        sections.append("\n**Constants:**")
        for const in comp.constants:
            sections.append(f"  {const.name} = {const.value}")

    if comp.test_contracts:
        sections.append("\n**Expected behavior (from tests):**")
        for tc in comp.test_contracts[:5]:
            sections.append(f"  {tc.test_method}: {tc.assertion}")

    sections.append("\n---")
    sections.append("**Task:** Implement this component using ONLY the specification above.")
    sections.append("Do NOT read source files. Generate the complete implementation.")

    return "\n".join(sections)


def compare_regeneration(original_path: Path, generated_code: str) -> dict[str, Any]:
    """Compare generated code against original source."""
    original_code = original_path.read_text()

    def extract_names(code: str) -> tuple[set[str], set[str]]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return set(), set()
        functions = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        return functions, classes

    orig_funcs, orig_classes = extract_names(original_code)
    gen_funcs, gen_classes = extract_names(generated_code)

    func_match = len(orig_funcs & gen_funcs) / len(orig_funcs) if orig_funcs else 1.0
    class_match = len(orig_classes & gen_classes) / len(orig_classes) if orig_classes else 1.0
    line_ratio = len(generated_code.splitlines()) / max(1, len(original_code.splitlines()))

    return {
        "function_match": func_match,
        "class_match": class_match,
        "line_ratio": line_ratio,
        "original_functions": len(orig_funcs),
        "generated_functions": len(gen_funcs),
        "calibration_score": (func_match * 0.5 + class_match * 0.3 + min(line_ratio, 1.0) * 0.2),
    }


# --- Task 5: Regeneration Proof ---


def format_regeneration_prompt(component_context: dict) -> str:
    """Format a prompt for regenerating a component from model data only."""
    lines = [
        "Regenerate this component from model data only, DO NOT read source files.",
        "",
        f"# Component: {component_context.get('name', 'Unknown')} ({component_context.get('id', '?')})",
        "",
        f"**Contract:** {component_context.get('contract', 'Not specified')}",
        f"**Pattern:** {component_context.get('pattern', 'Not specified')}",
    ]

    responsibilities = component_context.get("responsibilities", [])
    if responsibilities:
        lines.append("\n**Responsibilities:**")
        for r in responsibilities:
            lines.append(f"  - {r}")

    signatures = component_context.get("signatures", [])
    if signatures:
        lines.append("\n**Signatures:**")
        for sig in signatures:
            params = ", ".join(sig.get("params", []))
            ret = f" -> {sig['returns']}" if sig.get("returns") else ""
            lines.append(f"  def {sig['name']}({params}){ret}")

    symbols = component_context.get("symbols", [])
    if symbols:
        lines.append("\n**Symbols:**")
        for sym in symbols:
            members = ", ".join(sym.get("members", []))
            lines.append(f"  {sym.get('kind', 'class')} {sym['name']}: [{members}]")

    constants = component_context.get("constants", [])
    if constants:
        lines.append("\n**Constants:**")
        for c in constants:
            lines.append(f"  {c['name']} = {c['value']}")

    lines.append("\n---")
    lines.append("Provide the complete Python module output.")

    return "\n".join(lines)


def compare_regeneration(original: str, generated: str) -> dict:
    """Compare original and generated source code by public API coverage."""

    def _public_apis(code: str) -> set[str]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return set()
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    names.add(node.name)
        return names

    orig_apis = _public_apis(original)
    gen_apis = _public_apis(generated)

    covered = orig_apis & gen_apis
    coverage = len(covered) / len(orig_apis) if orig_apis else 1.0

    return {
        "api_coverage": coverage,
        "missing_apis": sorted(orig_apis - gen_apis),
        "extra_apis": sorted(gen_apis - orig_apis),
    }


# --- Task 6: Calibration Suite ---


def compute_correlation(data: list[dict]) -> float:
    """Pearson correlation between confidence and regen_quality fields."""
    if len(data) < 2:
        return 0.0
    xs = [d["confidence"] for d in data]
    ys = [d["regen_quality"] for d in data]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)

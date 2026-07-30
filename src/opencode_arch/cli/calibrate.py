"""Calibration command - spot-check confidence by attempting regeneration."""
from __future__ import annotations

import ast
import random
from pathlib import Path
from typing import Any

from architecture_model.core.types import ArchitectureModel, Component


def select_calibration_targets(
    model: ArchitectureModel, *, n: int = 3, min_confidence: float = 0.7
) -> list[Component]:
    """Select N components with confidence >= min_confidence for calibration."""
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

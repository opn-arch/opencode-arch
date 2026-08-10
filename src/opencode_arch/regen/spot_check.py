"""Spot-check regeneration probe.

Regenerates a targeted component/subsystem via LLM, compares against source,
and reports diagnostic results. Feeds failures into learning loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SpotCheckTarget:
    """What to regenerate."""
    component_id: str
    subsystem_id: str = ""  # if targeting a whole subsystem
    files: list[str] = field(default_factory=list)
    model_context: str = ""  # formatted model data for the regen prompt


@dataclass
class SpotCheckDiagnostic:
    """A specific issue found during spot-check."""
    category: str  # MISSING_IMPL, WRONG_CONSTANT, API_MISMATCH, CROSS_DEP, COMPLEX_BEHAVIOR, TEST_INFRA
    severity: str  # critical, warning, info
    message: str
    function_name: str = ""
    suggestion: str = ""  # actionable fix


@dataclass
class SpotCheckResult:
    """Result of a spot-check regeneration."""
    target: SpotCheckTarget
    success: bool
    match_percent: float  # 0-100, structural similarity
    iterations: int
    diagnostics: list[SpotCheckDiagnostic] = field(default_factory=list)
    generated_code: dict[str, str] = field(default_factory=dict)  # file → code
    test_pass_rate: float = 0.0  # 0-100


async def select_target(
    repo_path: Path,
    component_id: str | None = None,
    subsystem_id: str | None = None,
) -> SpotCheckTarget:
    """Select and prepare a spot-check target.
    
    If component_id specified, use that.
    If subsystem_id specified, load that subsystem's model.
    If neither, pick the easiest (highest static score, smallest).
    """
    from architecture_model.core.parser import load_model
    from architecture_model.core.regen_readiness import compute_regen_readiness
    
    model_path = repo_path / ".architecture-model.yaml"
    model = load_model(model_path)
    
    if component_id:
        # Find the specific component
        comp = next((c for c in model.entities.components if c.id == component_id), None)
        if not comp:
            raise ValueError(f"Component {component_id} not found")
        return SpotCheckTarget(
            component_id=component_id,
            files=comp.files,
            model_context=_format_component_context(comp, model),
        )
    
    if subsystem_id:
        # Load subsystem model
        sub_path = repo_path / ".architecture-models" / subsystem_id / ".architecture-model.yaml"
        if sub_path.exists():
            sub_model = load_model(sub_path)
            files = []
            for c in sub_model.entities.components:
                files.extend(c.files)
            return SpotCheckTarget(
                component_id="",
                subsystem_id=subsystem_id,
                files=files,
                model_context=_format_subsystem_context(sub_model),
            )
        raise ValueError(f"Subsystem {subsystem_id} not found")
    
    # Auto-select easiest component
    readiness = compute_regen_readiness(model)
    if not readiness.components:
        raise ValueError("No components to check")
    
    # Pick highest-scoring, smallest component
    best = max(readiness.components, key=lambda c: (c.score, -len([f for comp in model.entities.components if comp.id == c.id for f in comp.files])))
    comp = next(c for c in model.entities.components if c.id == best.id)
    return SpotCheckTarget(
        component_id=best.id,
        files=comp.files,
        model_context=_format_component_context(comp, model),
    )


def _format_component_context(comp: Any, model: Any) -> str:
    """Format component data as an LLM-ready regen prompt."""
    lines = [f"# Regenerate: {comp.name}", ""]
    
    if hasattr(comp, 'signatures') and comp.signatures:
        lines.append("## Signatures")
        for sig in comp.signatures:
            hint = f"  # {sig.body_hint}" if hasattr(sig, 'body_hint') and sig.body_hint else ""
            params = ', '.join(sig.params) if hasattr(sig, 'params') else ""
            returns = sig.returns if hasattr(sig, 'returns') else ""
            lines.append(f"  {sig.name}({params}) -> {returns}{hint}")
        lines.append("")
    
    if hasattr(comp, 'constants') and comp.constants:
        lines.append("## Constants")
        for const in comp.constants:
            lines.append(f"  {const.name} = {const.value}")
        lines.append("")
    
    if hasattr(comp, 'test_contracts') and comp.test_contracts:
        lines.append("## Test Contracts")
        for tc in comp.test_contracts[:50]:  # cap at 50
            lines.append(f"  {tc.test_method}: {tc.assertion}")
        lines.append("")
    
    if hasattr(comp, 'interfaces') and comp.interfaces:
        lines.append("## Interfaces")
        for iface in comp.interfaces:
            lines.append(f"  {iface.kind} {iface.name}: {iface.signature}")
        lines.append("")
    
    return "\n".join(lines)


def _format_subsystem_context(model: Any) -> str:
    """Format a full subsystem model as regen prompt."""
    project = model.meta.get('project', 'unknown') if isinstance(model.meta, dict) else getattr(model.meta, 'project', 'unknown')
    lines = [f"# Regenerate subsystem: {project}", ""]
    for comp in model.entities.components:
        lines.append(_format_component_context(comp, model))
    return "\n".join(lines)


async def run_spot_check(
    target: SpotCheckTarget,
    repo_path: Path,
    *,
    max_iterations: int = 3,
    llm_backend: Any = None,  # injected LLM callable
) -> SpotCheckResult:
    """Run the spot-check: regen target via LLM, diff against source, iterate on failure.
    
    If llm_backend is None, returns a dry-run result showing what WOULD be checked.
    """
    if llm_backend is None:
        # Dry run — just report what would be checked
        return SpotCheckResult(
            target=target,
            success=False,
            match_percent=0.0,
            iterations=0,
            diagnostics=[SpotCheckDiagnostic(
                category="TEST_INFRA",
                severity="info",
                message="Dry run — no LLM backend configured. Use --llm to enable.",
            )],
        )
    
    # Real spot-check loop
    result = SpotCheckResult(target=target, success=False, match_percent=0.0, iterations=0)
    
    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        
        # Generate code via LLM
        prompt = _build_regen_prompt(target, result.diagnostics)
        generated = await llm_backend(prompt)
        result.generated_code = _parse_generated_code(generated)
        
        # Compare against source
        match_pct, diagnostics = _compare_against_source(
            result.generated_code, target.files, repo_path
        )
        result.match_percent = match_pct
        result.diagnostics = diagnostics
        
        if match_pct >= 90.0:
            result.success = True
            break
        
        # Feed diagnostics back for next iteration (self-healing)
        # Pattern classifier determines what's wrong
    
    return result


def _build_regen_prompt(target: SpotCheckTarget, prior_diagnostics: list[SpotCheckDiagnostic]) -> str:
    """Build the LLM prompt for regeneration."""
    prompt = target.model_context
    if prior_diagnostics:
        prompt += "\n\n## Prior attempt failed. Issues:\n"
        for d in prior_diagnostics:
            prompt += f"- [{d.category}] {d.message}\n"
            if d.suggestion:
                prompt += f"  Fix: {d.suggestion}\n"
    return prompt


def _parse_generated_code(raw: str) -> dict[str, str]:
    """Parse LLM output into file→code mapping."""
    # Simple fence-based parsing
    files: dict[str, str] = {}
    current_file = None
    current_lines: list[str] = []
    
    for line in raw.splitlines():
        if line.startswith("```") and current_file is None:
            # Look for filename in fence
            parts = line.split()
            if len(parts) > 1 and ("." in parts[-1] or "/" in parts[-1]):
                current_file = parts[-1]
                current_lines = []
        elif line.startswith("```") and current_file:
            files[current_file] = "\n".join(current_lines)
            current_file = None
            current_lines = []
        elif current_file:
            current_lines.append(line)
    
    return files


def _compare_against_source(
    generated: dict[str, str],
    source_files: list[str],
    repo_path: Path,
) -> tuple[float, list[SpotCheckDiagnostic]]:
    """Compare generated code against actual source files."""
    diagnostics: list[SpotCheckDiagnostic] = []
    
    if not generated:
        diagnostics.append(SpotCheckDiagnostic(
            category="MISSING_IMPL",
            severity="critical",
            message="LLM produced no parseable code output",
        ))
        return 0.0, diagnostics
    
    total_match = 0.0
    count = 0
    
    for filepath in source_files:
        source_path = repo_path / filepath
        if not source_path.exists():
            continue
        
        actual = source_path.read_text(encoding="utf-8", errors="replace")
        
        # Find matching generated file
        gen_code = None
        for gen_name, code in generated.items():
            if Path(gen_name).name == source_path.name:
                gen_code = code
                break
        
        if gen_code is None:
            diagnostics.append(SpotCheckDiagnostic(
                category="MISSING_IMPL",
                severity="warning",
                message=f"No generated code for {filepath}",
            ))
            count += 1
            continue
        
        # Structural comparison (function/class names present)
        match_pct = _structural_similarity(actual, gen_code)
        total_match += match_pct
        count += 1
        
        if match_pct < 70:
            diagnostics.append(SpotCheckDiagnostic(
                category="API_MISMATCH",
                severity="warning",
                message=f"{filepath}: {match_pct:.0f}% structural match",
            ))
    
    overall = (total_match / count) if count > 0 else 0.0
    return overall, diagnostics


def _structural_similarity(actual: str, generated: str) -> float:
    """Compare structural elements (function/class names) between two Python files."""
    import ast
    
    def extract_names(source: str) -> set[str]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return set()
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(f"def:{node.name}")
            elif isinstance(node, ast.ClassDef):
                names.add(f"class:{node.name}")
        return names
    
    actual_names = extract_names(actual)
    gen_names = extract_names(generated)
    
    if not actual_names:
        return 100.0 if not gen_names else 50.0
    
    intersection = actual_names & gen_names
    return (len(intersection) / len(actual_names)) * 100

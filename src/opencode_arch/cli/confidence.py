"""CLI confidence visualization command."""
from __future__ import annotations
from pathlib import Path


def run_confidence(repo_path: str) -> str:
    """Run confidence analysis and return formatted output."""
    root = Path(repo_path)
    model_file = root / ".architecture-model.yaml"
    if not model_file.exists():
        model_file = root / ".architecture-model-extracted.yaml"
    if not model_file.exists():
        return "Error: No model found. Run extraction first."

    try:
        from architecture_model.core.parser import load_model
        from architecture_model.core.confidence import (
            compute_model_confidence,
            aggregate_block_confidence,
            model_confidence_summary,
        )

        model = load_model(model_file)
        compute_model_confidence(model)
        blocks = aggregate_block_confidence(model)
        summary = model_confidence_summary(model)
    except Exception as e:
        return f"Error computing confidence: {e}"

    lines = []
    lines.append(f"# Confidence Report: {model.meta.project}")
    lines.append(f"Overall: {summary['overall']:.0%} | "
                 f"High (>=80%): {summary['high_confidence']} | "
                 f"Low (<30%): {summary['low_confidence']} | "
                 f"Total: {summary['total_entities']}")
    lines.append("")

    lines.append(f"{'Block':<12} {'Avg':>6} {'Min':>6} {'Max':>6} {'Count':>6}")
    lines.append("-" * 42)
    for block_id in sorted(blocks.keys()):
        b = blocks[block_id]
        lines.append(f"{block_id:<12} {b['avg_confidence']:>5.0%} {b['min_confidence']:>5.0%} {b['max_confidence']:>5.0%} {b['entity_count']:>6}")

    lines.append("")

    if summary["gaps"]:
        lines.append("## Top Gaps (lowest confidence)")
        for gap in summary["gaps"]:
            lines.append(f"  {gap['id']:<12} {gap['name']:<25} {gap['confidence']:.0%}")

    lines.append("")
    lines.append("## Entity Detail")
    for comp in model.entities.components:
        missing = []
        if not comp.contract:
            missing.append("contract")
        if not comp.pattern:
            missing.append("pattern")
        if not comp.signatures:
            missing.append("signatures")
        if not comp.test_contracts:
            missing.append("tests")
        gaps_str = ", ".join(missing) if missing else "-"
        lines.append(f"  {comp.id:<12} {comp.name:<25} {comp.confidence:>5.0%}  gaps: {gaps_str}")

    return "\n".join(lines)

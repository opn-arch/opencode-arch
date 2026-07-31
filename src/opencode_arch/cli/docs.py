"""SE Document generation orchestrator."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from architecture_model import load_model, generate_manifest
from architecture_model.core.types import ArchitectureModel

from opencode_arch.artifacts import select_artifacts, assemble_artifact_context, TEMPLATES, get_template, ArtifactSpec, format_capability_detail_context, API_DETAIL_TEMPLATE
from opencode_arch.runner.base import RunnerBackend, RunResult


@dataclass
class DocsResult:
    """Result of a docs generation run."""
    generated: list[str]       # artifact IDs that were generated
    failed: list[str]          # artifact IDs that failed
    output_dir: str            # path to output directory
    time_seconds: float        # total time taken
    error: str | None = None   # top-level error if whole run failed


async def run_docs_generate(
    repo_path: Path,
    runner: RunnerBackend,
    output_dir: Path | None = None,
    artifact_filter: list[str] | None = None,
    model_path: Path | None = None,
) -> DocsResult:
    """Generate SE documentation for a project.

    Flow:
    1. Load model from project (or model_path override)
    2. Generate manifest via generate_manifest()
    3. Call select_artifacts(model, manifest) to determine what to generate
    4. If artifact_filter provided, intersect with selected artifacts
    5. For each artifact:
       a. Get template from TEMPLATES[artifact_id]
       b. Assemble context via assemble_artifact_context(template, model, manifest)
       c. Build full prompt (context + generation instructions)
       d. Call runner.run(prompt, str(repo_path))
       e. Write result to output_dir/filename
    6. Generate index.md linking all artifacts
    7. Return DocsResult
    """
    start_time = time.time()
    repo_path = Path(repo_path).resolve()

    # Determine output directory
    if output_dir is None:
        output_dir = repo_path / "docs" / "se"
    else:
        output_dir = Path(output_dir)

    # Step 1: Load model
    try:
        if model_path:
            model = load_model(Path(model_path))
        else:
            default_model_path = repo_path / ".architecture-model.yaml"
            if default_model_path.exists():
                model = load_model(default_model_path)
            else:
                elapsed = time.time() - start_time
                return DocsResult(
                    generated=[],
                    failed=[],
                    output_dir=str(output_dir),
                    time_seconds=elapsed,
                    error="No architecture model found. Run extraction first.",
                )
    except Exception as e:
        elapsed = time.time() - start_time
        return DocsResult(
            generated=[],
            failed=[],
            output_dir=str(output_dir),
            time_seconds=elapsed,
            error=f"Failed to load model: {e}",
        )

    # Step 2: Generate manifest (best-effort)
    manifest = None
    try:
        manifest = generate_manifest(repo_path)
    except Exception:
        pass  # Manifest is optional — select_artifacts handles None

    # Step 3: Select artifacts
    try:
        selected = select_artifacts(model, manifest)
    except Exception as e:
        elapsed = time.time() - start_time
        return DocsResult(
            generated=[],
            failed=[],
            output_dir=str(output_dir),
            time_seconds=elapsed,
            error=f"Failed to select artifacts: {e}",
        )

    # Step 4: Filter if requested
    if artifact_filter:
        selected = [s for s in selected if s.id in artifact_filter]

    # Ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 5: Generate each artifact
    generated: list[str] = []
    failed: list[str] = []
    generated_artifacts: list[tuple[str, str]] = []  # (artifact_id, filename)

    for spec in selected:
        # Per-capability API detail artifacts use specialized context
        if spec.id.startswith("api-detail-"):
            cap_id = spec.id.replace("api-detail-", "").upper()
            template = API_DETAIL_TEMPLATE
            filename = f"api-detail-{cap_id.lower()}.md"

            # Assemble capability-specific context
            try:
                cap_context = format_capability_detail_context(cap_id, model, manifest)
            except Exception:
                failed.append(spec.id)
                continue

            # Build prompt with template structure + capability data
            prompt = _build_capability_detail_prompt(template, cap_context, spec.name)

            # Call runner
            try:
                result = await runner.run(prompt, str(repo_path))
            except Exception:
                failed.append(spec.id)
                continue

            if not result.success:
                failed.append(spec.id)
                continue

            _write_artifact(output_dir, filename, spec.id, result.output)
            generated.append(spec.id)
            generated_artifacts.append((spec.id, filename))
            continue

        # Standard artifacts
        template = TEMPLATES.get(spec.id)
        if template is None:
            template = get_template(spec.id)
        if template is None:
            failed.append(spec.id)
            continue

        # Assemble context
        try:
            context = assemble_artifact_context(template, model, manifest)
        except Exception:
            failed.append(spec.id)
            continue

        # Build prompt
        prompt = _build_generation_prompt(context, spec.id)

        # Call runner
        try:
            result = await runner.run(prompt, str(repo_path))
        except Exception:
            failed.append(spec.id)
            continue

        if not result.success:
            failed.append(spec.id)
            continue

        # Write artifact
        _write_artifact(output_dir, template.filename, spec.id, result.output)
        generated.append(spec.id)
        generated_artifacts.append((spec.id, template.filename))

    # Step 6: Write index
    if generated_artifacts:
        _write_index(output_dir, generated_artifacts)

    elapsed = time.time() - start_time
    return DocsResult(
        generated=generated,
        failed=failed,
        output_dir=str(output_dir),
        time_seconds=elapsed,
    )


async def run_docs_list(
    repo_path: Path,
    model_path: Path | None = None,
) -> list[dict[str, str]]:
    """List which artifacts would be generated for a project.

    Returns list of dicts: [{"id": ..., "name": ..., "category": ..., "priority": ...}]
    No runner needed — just model analysis.
    """
    repo_path = Path(repo_path).resolve()

    # Load model
    if model_path:
        model = load_model(Path(model_path))
    else:
        default_model_path = repo_path / ".architecture-model.yaml"
        model = load_model(default_model_path)

    # Generate manifest (best-effort)
    manifest = None
    try:
        manifest = generate_manifest(repo_path)
    except Exception:
        pass

    # Select artifacts
    selected = select_artifacts(model, manifest)

    return [
        {
            "id": spec.id,
            "name": spec.name,
            "category": spec.category,
            "priority": str(spec.priority),
        }
        for spec in selected
    ]


def _build_generation_prompt(context: str, template_artifact_id: str) -> str:
    """Build the full prompt sent to the agent.

    Format includes context from assemble_artifact_context followed by
    task instructions for the agent.
    """
    return (
        f"---\n"
        f"{context}\n"
        f"\n"
        f"---\n"
        f"TASK: Generate the '{template_artifact_id}' documentation artifact.\n"
        f"\n"
        f"Write a complete, well-structured markdown document. Use the DATA sections above\n"
        f"as your source of truth. Do NOT invent information not present in the data.\n"
        f"\n"
        f"Output ONLY the markdown content, no code fences or explanations.\n"
        f"---\n"
    )


def _build_capability_detail_prompt(template, cap_context: str, cap_name: str) -> str:
    """Build the prompt for a per-capability API detail artifact.

    Uses the API_DETAIL_TEMPLATE sections as instructions, with the
    capability-specific context as the grounding data.
    """
    sections_instructions = "\n".join(
        f"  {s.heading}: {s.instructions}"
        for s in template.sections
    )

    return (
        f"---\n"
        f"SYSTEM: {template.system_prompt}\n"
        f"\n"
        f"## Architecture Model Data for: {cap_name}\n\n"
        f"{cap_context}\n"
        f"\n"
        f"---\n"
        f"TASK: Generate a detailed API documentation file for this capability.\n"
        f"\n"
        f"Required sections:\n"
        f"{sections_instructions}\n"
        f"\n"
        f"Write a complete, well-structured markdown document. Use the DATA above\n"
        f"as your source of truth. Include exact function signatures, parameters,\n"
        f"return types, algorithm steps, and behavioral sequences.\n"
        f"Do NOT invent information not present in the data.\n"
        f"\n"
        f"Output ONLY the markdown content, no code fences or explanations.\n"
        f"---\n"
    )


def _write_artifact(output_dir: Path, filename: str, artifact_id: str, content: str):
    """Write generated artifact with frontmatter.

    Prepends YAML frontmatter with artifact_id, timestamp, and generator.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    frontmatter = (
        f"---\n"
        f"artifact_id: {artifact_id}\n"
        f"generated_at: {timestamp}\n"
        f"generator: opencode-arch-docs\n"
        f"---\n"
    )
    filepath = output_dir / filename
    filepath.write_text(frontmatter + content)


def _write_index(output_dir: Path, generated_artifacts: list[tuple[str, str]]):
    """Write index.md linking all generated artifacts.

    generated_artifacts: list of (artifact_id, filename) tuples
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# SE Documentation Index",
        "",
        f"Generated: {timestamp}",
        "",
        "## Artifacts",
        "",
        "| Artifact | File | Category |",
        "|----------|------|----------|",
    ]

    for artifact_id, filename in generated_artifacts:
        # Use artifact_id as the display name
        name = artifact_id.replace("-", " ").title()
        lines.append(f"| {name} | [{filename}](./{filename}) | {artifact_id} |")

    lines.append("")
    index_path = output_dir / "index.md"
    index_path.write_text("\n".join(lines))

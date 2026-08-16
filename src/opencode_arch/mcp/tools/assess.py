"""Real-time conversation assessment — extracts requirements, issues, observations."""

from __future__ import annotations

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_REPOS = {
    "logs-db": Path.home() / "Documents/Projects/logs_db",
    "opencode-arch": Path.home() / "Documents/Projects/opencode-arch",
    "architecture-model-standard": Path.home() / "Documents/Projects/architecture-model-standard",
}


async def assess_conversation(
    repo_path: str,
    conversation_text: str,
    scope: str = "all",
) -> dict[str, Any]:
    """Extract requirements, issues, and observations from conversation text.

    CALL THIS after completing a significant piece of work, discovering an issue,
    or when the conversation reveals requirements. Auto-called by architect_gate.

    Args:
        repo_path: Current repository root path.
        conversation_text: Recent conversation context (last few exchanges or summary).
        scope: "all" | "requirements" | "issues" | "cross-repo" — focus dimension.

    Returns:
        {findings_count, findings, stored_to, cross_repo_impacts}
    """
    repo = Path(repo_path)
    arch_dir = repo / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    findings_path = arch_dir / "session_findings.yaml"

    # Load model context for all 3 repos (capability IDs)
    model_contexts = {}
    for sys_name, sys_path in WORKSPACE_REPOS.items():
        model_file = sys_path / ".architecture-model.yaml"
        if model_file.exists():
            try:
                model = yaml.safe_load(model_file.read_text())
                caps = model.get("entities", {}).get("capabilities", [])
                model_contexts[sys_name] = [
                    f"{c.get('id', '?')}: {c.get('name', '?')}" for c in caps[:20]
                ]
            except Exception:
                model_contexts[sys_name] = []

    # Build context block for potential LLM use
    context_block = "\n".join(
        f"[{name}] Capabilities: {', '.join(caps) if caps else 'none'}"
        for name, caps in model_contexts.items()
    )

    # Heuristic extraction (works without LLM)
    findings = _heuristic_extract(conversation_text, scope)

    # Infer system from repo_path
    default_system = "logs-db"
    for sys_name, sys_path in WORKSPACE_REPOS.items():
        if str(sys_path) in repo_path:
            default_system = sys_name
            break

    # Tag findings with default system if not set
    for f in findings:
        if not f.get("system"):
            f["system"] = default_system

    # Load existing findings
    if findings_path.exists():
        existing = yaml.safe_load(findings_path.read_text()) or {}
    else:
        existing = {"findings": [], "synced": []}

    # Append new findings with timestamps
    for f in findings:
        f["timestamp"] = datetime.now(timezone.utc).isoformat()
        f["synced"] = False
        existing.setdefault("findings", []).append(f)

    findings_path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))

    cross_impacts = [f for f in findings if f.get("cross_repo_impact")]

    return {
        "findings_count": len(findings),
        "findings": findings,
        "stored_to": str(findings_path),
        "cross_repo_impacts": len(cross_impacts),
        "model_context": context_block,
        "hint": "Call architect_sync to push findings to logs-db when ready.",
    }


def _heuristic_extract(text: str, scope: str) -> list[dict]:
    """Extract findings using keyword heuristics (no LLM needed)."""
    findings = []
    lines = text.split("\n")

    requirement_markers = [
        "we need",
        "should add",
        "must have",
        "requires",
        "implement",
        "add support for",
        "need to add",
        "want to",
    ]
    issue_markers = [
        "is broken",
        "doesn't work",
        "fails",
        "bug:",
        "issue:",
        "missing",
        "not working",
        "error when",
    ]

    for line in lines:
        lower = line.lower().strip()
        if not lower or len(lower) < 15:
            continue

        if scope in ("all", "requirements"):
            if any(marker in lower for marker in requirement_markers):
                findings.append(
                    {
                        "type": "requirement",
                        "system": "",
                        "title": line.strip()[:120],
                        "description": line.strip(),
                        "capability": "",
                        "priority": "should",
                    }
                )

        if scope in ("all", "issues"):
            if any(marker in lower for marker in issue_markers):
                findings.append(
                    {
                        "type": "issue",
                        "system": "",
                        "title": line.strip()[:120],
                        "description": line.strip(),
                        "capability": "",
                        "priority": "medium",
                    }
                )

    # Deduplicate within batch
    seen = set()
    deduped = []
    for f in findings:
        key = f["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    return deduped

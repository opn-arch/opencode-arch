"""Full 3-repo scorecard evaluation."""

from __future__ import annotations

import os
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_REPOS = {
    "logs-db": Path.home() / "Documents/Projects/logs_db",
    "opencode-arch": Path.home() / "Documents/Projects/opencode-arch",
    "architecture-model-standard": Path.home() / "Documents/Projects/architecture-model-standard",
}


async def evaluate_workspace(
    repo_path: str,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Compute 3-repo scorecard: model quality, requirements, sync status.

    CALL THIS after architect_gate, after completing features, or when you want
    a health check of the full workspace. Auto-triggered after 3+ architect_log calls.

    Args:
        repo_path: Any repo in workspace (used to find .architecture/).
        force_refresh: Recompute even if cache is <5 min old.

    Returns:
        {scorecards: {system: {metrics}}, overall_health, recommendations}
    """
    repo = Path(repo_path)
    arch_dir = repo / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    eval_path = arch_dir / "evaluation.yaml"

    # Check cache freshness
    if not force_refresh and eval_path.exists():
        try:
            existing = yaml.safe_load(eval_path.read_text()) or {}
            last_eval = existing.get("timestamp", "")
            if last_eval:
                last = datetime.fromisoformat(last_eval.replace("Z", "+00:00"))
                age_min = (datetime.now(timezone.utc) - last).total_seconds() / 60
                if age_min < 5:
                    existing["from_cache"] = True
                    existing["cache_age_minutes"] = round(age_min, 1)
                    return existing
        except (ValueError, TypeError, yaml.YAMLError):
            pass

    scorecards = {}
    for sys_name, sys_path in WORKSPACE_REPOS.items():
        scorecards[sys_name] = _evaluate_repo(sys_name, sys_path)

    # Overall health
    scores = [s.get("overall_score", 0) for s in scorecards.values()]
    overall = sum(scores) / len(scores) if scores else 0

    # Recommendations
    recommendations = []
    for sys_name, card in scorecards.items():
        if card.get("model_coverage_pct", 100) < 50:
            recommendations.append(
                f"{sys_name}: Run architect_pipeline to improve model coverage ({card['model_coverage_pct']}%)"
            )
        if card.get("unsynced_findings", 0) > 5:
            recommendations.append(
                f"{sys_name}: {card['unsynced_findings']} findings unsynced — call architect_sync"
            )
        if card.get("stale_model", False):
            recommendations.append(f"{sys_name}: Model >24h old — consider re-running pipeline")

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scorecards": scorecards,
        "overall_health": round(overall, 1),
        "recommendations": recommendations,
        "sil_summary": _collect_sil_summary(repo),
        "freshness_summary": _collect_freshness_summary(repo),
        "from_cache": False,
    }

    eval_path.write_text(yaml.dump(result, default_flow_style=False, sort_keys=False))
    return result


def _collect_sil_summary(repo_path: Path) -> dict:
    """Return per-component SIL rollup dict keyed by component_id.

    Reads ``<repo>/.architecture/sil.sqlite`` if present. Gracefully
    returns ``{}`` when the store is missing or unreadable. Each entry is
    ``{invocations_7d, failure_rate_7d, avg_duration_ms}``.
    """
    sil_db = repo_path / ".architecture" / "sil.sqlite"
    if not sil_db.exists():
        return {}
    try:
        from opencode_arch.sil.store import SILStore

        store = SILStore(sil_db)
        summary: dict[str, dict[str, Any]] = {}
        for comp_id in store.distinct_component_ids():
            summary[comp_id] = {
                "invocations_7d": store.invocations_7d(comp_id),
                "failure_rate_7d": round(store.failure_rate_7d(comp_id), 4),
                "avg_duration_ms": round(store.avg_duration_ms(comp_id), 2),
            }
        return summary
    except Exception:
        return {}


def _collect_freshness_summary(repo_path: Path) -> dict:
    """Return freshness distribution over ``.architecture/lifecycle/artifacts/*``.

    Phase 1 pragmatic implementation (Task 14): AMS Task 10 stamps
    ``ProjectedView.provenance["freshness"]`` in-memory during ``project()``,
    but the OCA rebuild path (``lifecycle_exec/rebuild.py``) writes raw
    renderer bytes to ``<id>.<ext>`` without a provenance sidecar. Nothing
    persisted on disk currently distinguishes fresh/stale/pending.

    Until Phase 2 persists per-artifact provenance, every file found is
    counted as ``unknown`` and the summary always exposes the four keys the
    plan mandates (``fresh``, ``stale``, ``pending``, ``total``) plus an
    ``unknown`` bucket for accurate accounting. Missing artifacts dir → all
    zeros.
    """
    artifacts_dir = repo_path / ".architecture" / "lifecycle" / "artifacts"
    summary = {"fresh": 0, "stale": 0, "pending": 0, "unknown": 0, "total": 0}
    if not artifacts_dir.is_dir():
        return summary
    try:
        for entry in artifacts_dir.iterdir():
            if not entry.is_file():
                continue
            # No persisted freshness marker yet — bucket as unknown.
            summary["unknown"] += 1
            summary["total"] += 1
    except OSError:
        pass
    return summary


def _evaluate_repo(sys_name: str, sys_path: Path) -> dict:
    """Evaluate a single repo's architecture health."""
    card: dict[str, Any] = {"system": sys_name, "overall_score": 0}

    model_path = sys_path / ".architecture-model.yaml"
    if not model_path.exists():
        card["overall_score"] = 10
        card["status"] = "no_model"
        return card

    try:
        model = yaml.safe_load(model_path.read_text())
    except Exception:
        card["overall_score"] = 15
        card["status"] = "model_parse_error"
        return card

    # Capability count
    caps = model.get("entities", {}).get("capabilities", [])
    card["capability_count"] = len(caps)

    # File coverage
    all_files = set()
    for cap in caps:
        for f in cap.get("files", []):
            all_files.add(f if isinstance(f, str) else f.get("path", ""))

    py_files = list(sys_path.rglob("*.py"))
    py_files = [f for f in py_files if ".venv" not in str(f) and "__pycache__" not in str(f)]
    card["model_coverage_pct"] = round(len(all_files) / max(len(py_files), 1) * 100, 1)

    # Relationships
    rels = model.get("entities", {}).get("relationships", [])
    card["relationship_count"] = len(rels)

    # Requirements
    req_path = sys_path / ".architecture" / "requirements.yaml"
    if req_path.exists():
        try:
            reqs = yaml.safe_load(req_path.read_text()) or {}
            card["requirements_count"] = len(reqs.get("requirements", []))
        except Exception:
            card["requirements_count"] = 0
    else:
        card["requirements_count"] = 0

    # Unsynced findings
    findings_path = sys_path / ".architecture" / "session_findings.yaml"
    if findings_path.exists():
        try:
            findings = yaml.safe_load(findings_path.read_text()) or {}
            unsynced = [f for f in findings.get("findings", []) if not f.get("synced")]
            card["unsynced_findings"] = len(unsynced)
        except Exception:
            card["unsynced_findings"] = 0
    else:
        card["unsynced_findings"] = 0

    # Devlog entries
    devlog_path = sys_path / ".architecture" / "devlog.jsonl"
    if devlog_path.exists():
        card["devlog_entries"] = sum(1 for l in devlog_path.read_text().splitlines() if l.strip())
    else:
        card["devlog_entries"] = 0

    # Model staleness
    model_mtime = os.path.getmtime(model_path)
    age_hours = (datetime.now(timezone.utc).timestamp() - model_mtime) / 3600
    card["stale_model"] = age_hours > 24
    card["model_age_hours"] = round(age_hours, 1)

    # Score calculation
    score = 50  # base
    score += min(20, card["capability_count"] * 2)
    score += min(15, card["model_coverage_pct"] / 7)
    score += min(10, card["relationship_count"])
    score += 5 if card["requirements_count"] > 0 else 0
    score -= 10 if card["stale_model"] else 0
    card["overall_score"] = min(100, max(0, round(score)))

    return card

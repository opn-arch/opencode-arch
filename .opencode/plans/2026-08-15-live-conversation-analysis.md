# Live Conversation Analysis MCP Tools — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 3 new MCP tools (architect_assess, architect_evaluate, architect_sync) that bring real-time conversation analysis, 3-repo evaluation, and DB sync to live coding sessions.

**Architecture:** Local-first storage (.architecture/ files) with on-demand sync to logs-db API. Auto-triggers on milestones (gate, pipeline completion). Reuses batch analyzer prompts/logic where possible.

**Tech Stack:** Python, async, YAML, httpx/urllib, opencode-arch MCP framework

---

## Task 1: `architect_assess` — Mini-Analyzer Tool

**Files:**
- Create: `src/opencode_arch/mcp/tools/assess.py`
- Modify: `src/opencode_arch/mcp/server.py` (register tool)

**Step 1: Create assess.py**

```python
"""Real-time conversation assessment — extracts requirements, issues, observations."""
from __future__ import annotations

import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_REPOS = {
    "logs-db": Path.home() / "Documents/Projects/logs_db",
    "opencode-arch": Path.home() / "Documents/Projects/opencode-arch",
    "architecture-model-standard": Path.home() / "Documents/Projects/architecture-model-standard",
}

ASSESS_PROMPT = """Analyze this conversation segment and extract structured findings.

For EACH of the 3 systems (logs-db, opencode-arch, architecture-model-standard), assess:
- Requirements: explicit or implicit needs stated or discovered
- Issues: bugs, gaps, quality problems identified
- Observations: patterns, decisions, architecture insights
- Cross-repo impacts: does this work affect other systems?

Tag each finding with the most relevant capability ID from the model context (e.g., CAP-1, CAP-3).

Output JSON:
{
  "findings": [
    {"type": "requirement|issue|observation", "system": "logs-db|opencode-arch|architecture-model-standard", 
     "title": "...", "description": "...", "capability": "CAP-X", "priority": "must|should|could",
     "cross_repo_impact": null | {"system": "...", "description": "..."}}
  ]
}
"""


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

    # Build prompt with model context
    context_block = "\n".join(
        f"[{name}] Capabilities: {', '.join(caps) if caps else 'none'}"
        for name, caps in model_contexts.items()
    )

    # For now, do local heuristic extraction (LLM call optional via relay)
    # This is the "offline" path — works without LLM
    findings = _heuristic_extract(conversation_text, scope)

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
        "model_context_available": context_block,
        "hint": "Call architect_sync to push findings to logs-db when ready.",
    }


def _heuristic_extract(text: str, scope: str) -> list[dict]:
    """Extract findings using keyword heuristics (no LLM needed)."""
    findings = []
    lines = text.split("\n")

    requirement_keywords = ["need", "must", "should", "require", "want", "add", "implement"]
    issue_keywords = ["bug", "broken", "fail", "error", "missing", "wrong", "issue"]

    for line in lines:
        lower = line.lower().strip()
        if not lower or len(lower) < 10:
            continue

        if scope in ("all", "requirements"):
            if any(kw in lower for kw in requirement_keywords):
                if any(marker in lower for marker in ["we need", "should add", "must have", "requires", "implement"]):
                    findings.append({
                        "type": "requirement",
                        "system": "logs-db",  # default, refined by LLM path
                        "title": line.strip()[:100],
                        "description": line.strip(),
                        "capability": "",
                        "priority": "should",
                    })

        if scope in ("all", "issues"):
            if any(kw in lower for kw in issue_keywords):
                if any(marker in lower for marker in ["is broken", "doesn't work", "fails", "bug:", "issue:", "missing"]):
                    findings.append({
                        "type": "issue",
                        "system": "logs-db",
                        "title": line.strip()[:100],
                        "description": line.strip(),
                        "capability": "",
                        "priority": "medium",
                    })

    return findings
```

**Step 2: Register in server.py**

Add the tool registration. Pattern: look at how other tools are registered.

**Step 3: Commit**

```bash
git add src/opencode_arch/mcp/tools/assess.py
git commit -m "feat: add architect_assess tool — real-time conversation analysis"
```

---

## Task 2: `architect_evaluate` — Full 3-Repo Scorecard

**Files:**
- Create: `src/opencode_arch/mcp/tools/evaluate.py`
- Modify: `src/opencode_arch/mcp/server.py` (register tool)

**Step 1: Create evaluate.py**

```python
"""Full 3-repo scorecard evaluation."""
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


async def evaluate_workspace(
    repo_path: str,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Compute 3-repo scorecard: model quality, tool usage, ingestion quality.

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
        existing = yaml.safe_load(eval_path.read_text()) or {}
        last_eval = existing.get("timestamp", "")
        if last_eval:
            from datetime import datetime as dt
            try:
                last = dt.fromisoformat(last_eval.replace("Z", "+00:00"))
                age_min = (datetime.now(timezone.utc) - last).total_seconds() / 60
                if age_min < 5:
                    existing["from_cache"] = True
                    existing["cache_age_minutes"] = round(age_min, 1)
                    return existing
            except (ValueError, TypeError):
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
            recommendations.append(f"{sys_name}: Run architect_pipeline to improve model coverage ({card['model_coverage_pct']}%)")
        if card.get("unsynced_findings", 0) > 5:
            recommendations.append(f"{sys_name}: {card['unsynced_findings']} findings unsynced — call architect_sync")
        if card.get("stale_model", False):
            recommendations.append(f"{sys_name}: Model hasn't been updated recently — consider re-running pipeline")

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scorecards": scorecards,
        "overall_health": round(overall, 1),
        "recommendations": recommendations,
        "from_cache": False,
    }

    eval_path.write_text(yaml.dump(result, default_flow_style=False, sort_keys=False))
    return result


def _evaluate_repo(sys_name: str, sys_path: Path) -> dict:
    """Evaluate a single repo's architecture health."""
    card = {"system": sys_name, "overall_score": 0}

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

    # Count actual Python files
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
    import os
    model_mtime = os.path.getmtime(model_path)
    age_hours = (datetime.now(timezone.utc).timestamp() - model_mtime) / 3600
    card["stale_model"] = age_hours > 24
    card["model_age_hours"] = round(age_hours, 1)

    # Score calculation
    score = 50  # base
    score += min(20, card["capability_count"] * 2)  # up to 20 for capabilities
    score += min(15, card["model_coverage_pct"] / 7)  # up to 15 for coverage
    score += min(10, card["relationship_count"])  # up to 10 for relationships
    score += 5 if card["requirements_count"] > 0 else 0
    score -= 10 if card["stale_model"] else 0
    card["overall_score"] = min(100, max(0, round(score)))

    return card
```

**Step 2: Register in server.py**

**Step 3: Commit**

```bash
git add src/opencode_arch/mcp/tools/evaluate.py
git commit -m "feat: add architect_evaluate tool — full 3-repo scorecard"
```

---

## Task 3: `architect_sync` — Push Findings to logs-db API

**Files:**
- Create: `src/opencode_arch/mcp/tools/sync.py`
- Modify: `src/opencode_arch/mcp/server.py` (register tool)

**Step 1: Create sync.py**

```python
"""Sync local findings to logs-db API with fuzzy dedup."""
from __future__ import annotations

import json
import yaml
import urllib.request
import urllib.error
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

WORKSPACE_REPOS = {
    "logs-db": Path.home() / "Documents/Projects/logs_db",
    "opencode-arch": Path.home() / "Documents/Projects/opencode-arch",
    "architecture-model-standard": Path.home() / "Documents/Projects/architecture-model-standard",
}

DEFAULT_API_URL = "http://localhost:8000"

# System name → system_id mapping in logs-db
SYSTEM_IDS = {
    "logs-db": 2,
    "opencode-arch": 1,
    "architecture-model-standard": 3,
}


async def sync_findings(
    repo_path: str,
    api_url: str = DEFAULT_API_URL,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Push unsynced findings and devlog entries to logs-db API.

    CALL THIS at end of session, after significant work, or when architect_evaluate
    shows high unsynced count. Performs fuzzy dedup against existing DB entries.

    Args:
        repo_path: Repository root (syncs findings from all 3 repos).
        api_url: logs-db API URL (default http://localhost:8000).
        dry_run: If True, report what would sync without pushing.

    Returns:
        {synced_count, skipped_duplicates, errors, dry_run}
    """
    # Collect findings from all repos
    all_findings = []
    for sys_name, sys_path in WORKSPACE_REPOS.items():
        findings_path = sys_path / ".architecture" / "session_findings.yaml"
        if findings_path.exists():
            try:
                data = yaml.safe_load(findings_path.read_text()) or {}
                for f in data.get("findings", []):
                    if not f.get("synced"):
                        f["_source_system"] = sys_name
                        f["_source_path"] = str(findings_path)
                        all_findings.append(f)
            except Exception:
                pass

        # Also collect from devlog
        devlog_path = sys_path / ".architecture" / "devlog.jsonl"
        if devlog_path.exists():
            for line in devlog_path.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("synced"):
                        continue
                    if entry.get("type") in ("requirement", "issue", "observation"):
                        all_findings.append({
                            "type": entry["type"],
                            "system": sys_name,
                            "title": entry.get("title", ""),
                            "description": entry.get("content", ""),
                            "capability": entry.get("context", {}).get("component_id", ""),
                            "priority": "medium",
                            "_source_system": sys_name,
                            "_source_path": str(devlog_path),
                            "_devlog_id": entry.get("id"),
                        })
                except (json.JSONDecodeError, KeyError):
                    pass

    if not all_findings:
        return {"synced_count": 0, "message": "Nothing to sync"}

    # Load existing DB titles for dedup
    existing_titles = _load_existing_from_api(api_url)

    # Dedup and sync
    synced = 0
    skipped = 0
    errors = 0
    synced_items = []

    for finding in all_findings:
        title = finding.get("title", "")
        if not title:
            continue

        sys_name = finding.get("system") or finding.get("_source_system", "logs-db")
        cap_ref = finding.get("capability", "")

        # Fuzzy dedup
        is_dup = False
        for existing_title in existing_titles.get(sys_name, []):
            sim = SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
            if sim > 0.70:
                is_dup = True
                break

        if is_dup:
            skipped += 1
            continue

        if dry_run:
            synced_items.append({"title": title, "system": sys_name, "type": finding["type"]})
            synced += 1
            continue

        # Push to API
        desc = finding.get("description", "")
        if cap_ref:
            desc = f"[{cap_ref}] {desc}"

        payload = {
            "title": title[:500],
            "description": desc[:2000],
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "log_type": finding["type"],
            "source": "architect_sync",
            "priority": finding.get("priority", "medium"),
            "systems": [sys_name],
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{api_url}/api/logs",
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req)
            synced += 1
            existing_titles.setdefault(sys_name, []).append(title)
            synced_items.append({"title": title, "system": sys_name})
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            errors += 1

    # Mark findings as synced in source files
    if not dry_run and synced > 0:
        _mark_synced(all_findings[:synced + skipped])

    return {
        "synced_count": synced,
        "skipped_duplicates": skipped,
        "errors": errors,
        "dry_run": dry_run,
        "items": synced_items[:20],  # truncate for display
    }


def _load_existing_from_api(api_url: str) -> dict[str, list[str]]:
    """Load existing log titles from API grouped by system."""
    existing = {}
    try:
        for page in range(1, 10):
            req = urllib.request.Request(f"{api_url}/api/logs?page={page}&per_page=50")
            resp = urllib.request.urlopen(req)
            logs = json.loads(resp.read())
            if not logs:
                break
            for log in logs:
                for sys in log.get("systems", []):
                    existing.setdefault(sys["name"], []).append(log["title"])
            if len(logs) < 50:
                break
    except Exception:
        pass
    return existing


def _mark_synced(findings: list[dict]) -> None:
    """Mark findings as synced in their source YAML files."""
    # Group by source path
    by_path = {}
    for f in findings:
        path = f.get("_source_path")
        if path and path.endswith(".yaml"):
            by_path.setdefault(path, []).append(f)

    for path_str, items in by_path.items():
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text()) or {}
            for finding in data.get("findings", []):
                if finding.get("title") in {i.get("title") for i in items}:
                    finding["synced"] = True
            path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        except Exception:
            pass
```

**Step 2: Register in server.py**

**Step 3: Commit**

```bash
git add src/opencode_arch/mcp/tools/sync.py
git commit -m "feat: add architect_sync tool — push findings to logs-db with dedup"
```

---

## Task 4: Wire Auto-Triggers into `architect_gate`

**Files:**
- Modify: `src/opencode_arch/mcp/tools/gate.py`

**What to do:**
After the existing gate checks complete, auto-call `assess_conversation` and `evaluate_workspace`. Include their results in the gate output under `live_assessment` and `workspace_health` keys.

**Step 1: Add imports and calls at end of gate function**

```python
# At end of check_gate(), before returning:
from .assess import assess_conversation
from .evaluate import evaluate_workspace

# Auto-assess (use gate context as conversation text)
assess_result = await assess_conversation(repo_path, conversation_text=f"Gate check for {repo_path}")
eval_result = await evaluate_workspace(repo_path)

result["live_assessment"] = assess_result
result["workspace_health"] = eval_result.get("overall_health")
result["recommendations"] = eval_result.get("recommendations", [])
```

**Step 2: Commit**

```bash
git commit -am "feat: auto-trigger assess+evaluate in architect_gate"
```

---

## Task 5: Register All Tools in server.py

**Files:**
- Modify: `src/opencode_arch/mcp/server.py`

**What to do:**
Add the 3 new tools (architect_assess, architect_evaluate, architect_sync) following the existing registration pattern. Include prescriptive docstrings:

- `architect_assess`: "CALL THIS after completing work, discovering issues, or when conversation reveals requirements. Extracts structured findings from recent context."
- `architect_evaluate`: "CALL THIS for a health check of all 3 systems. Auto-triggered after architect_gate. Shows model coverage, requirement count, and sync status."
- `architect_sync`: "CALL THIS at end of session or when evaluate shows unsynced findings. Pushes local findings to logs-db API with dedup."

**Step 1: Add registrations**

**Step 2: Commit**

```bash
git commit -am "feat: register architect_assess, architect_evaluate, architect_sync in MCP server"
```

---

## Priority Order

| Task | What | Est |
|------|------|-----|
| 1 | architect_assess | 10 min |
| 2 | architect_evaluate | 10 min |
| 3 | architect_sync | 15 min |
| 4 | Wire auto-triggers | 5 min |
| 5 | Register in server.py | 5 min |

**Total: ~45 min**

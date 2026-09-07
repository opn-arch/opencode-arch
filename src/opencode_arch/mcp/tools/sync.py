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
    # A2.3: push unsynced comment stubs to logs-db (back-fills issue_ref).
    comments_pushed: list[dict] = []
    if not dry_run:
        try:
            client = LogsDBClient(api_url)
            comments_pushed = _push_comments(Path(repo_path), client)
        except Exception:
            pass

    # Collect unsynced findings from all repos
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

        # Also collect from devlog (requirement/issue/observation entries only)
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
                        all_findings.append(
                            {
                                "type": entry["type"],
                                "system": sys_name,
                                "title": entry.get("title", ""),
                                "description": entry.get("content", ""),
                                "capability": (entry.get("context") or {}).get("component_id", ""),
                                "priority": "medium",
                                "_source_system": sys_name,
                                "_source_path": str(devlog_path),
                                "_devlog_id": entry.get("id"),
                            }
                        )
                except (json.JSONDecodeError, KeyError):
                    pass

    if not all_findings:
        return {
            "synced_count": 0,
            "skipped_duplicates": 0,
            "errors": 0,
            "message": "Nothing to sync",
            "comments_pushed": comments_pushed,
        }

    # Load existing DB titles for dedup
    existing_titles = _load_existing_from_api(api_url)

    synced = 0
    skipped = 0
    errors = 0
    synced_items = []

    for finding in all_findings:
        title = finding.get("title", "")
        if not title or len(title) < 5:
            continue

        sys_name = finding.get("system") or finding.get("_source_system", "logs-db")
        cap_ref = finding.get("capability", "")

        # Fuzzy dedup against DB
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

        # Push to API via POST /api/logs/bulk or individual POST
        desc = finding.get("description", "")
        if cap_ref:
            desc = f"[{cap_ref}] {desc}"

        payload = json.dumps(
            {
                "title": title[:500],
                "description": desc[:2000],
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "log_type": finding["type"],
                "source": "architect_sync",
                "priority": str(finding.get("priority", "medium")),
                "systems": [sys_name],
            }
        ).encode()

        try:
            req = urllib.request.Request(
                f"{api_url}/api/logs",
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req)
            synced += 1
            existing_titles.setdefault(sys_name, []).append(title)
            synced_items.append({"title": title, "system": sys_name})
        except (urllib.error.HTTPError, urllib.error.URLError):
            errors += 1

    # Mark findings as synced
    if not dry_run and synced > 0:
        _mark_synced(all_findings)

    return {
        "synced_count": synced,
        "skipped_duplicates": skipped,
        "errors": errors,
        "dry_run": dry_run,
        "items": synced_items[:20],
        "comments_pushed": comments_pushed,
    }


def _load_existing_from_api(api_url: str) -> dict[str, list[str]]:
    """Load existing log titles from API grouped by system."""
    existing: dict[str, list[str]] = {}
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
    by_path: dict[str, list[dict]] = {}
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
            titles_to_mark = {i.get("title") for i in items}
            for finding in data.get("findings", []):
                if finding.get("title") in titles_to_mark:
                    finding["synced"] = True
            path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        except Exception:
            pass


from architecture_model.comments.store import list_stubs, set_issue_ref
from architecture_model.comments.models import IssueRef
from architecture_model.lifecycle.journal import Journal, COMMENT_SYNC
from opencode_arch.logs_db.client import LogsDBClient


def _push_comments(repo_path: Path, client: LogsDBClient) -> list[dict]:
    """Push unsynced comment stubs to logs-db, back-fill issue_ref, journal event."""
    journal = Journal(repo_path / ".architecture" / "lifecycle" / "journal.jsonl")
    results: list[dict] = []
    for stub in list_stubs(repo_path):
        if stub.issue_ref and stub.issue_ref.issue_id is not None:
            continue
        title = f"{stub.artifact_id}@{stub.revision}"
        meta = {
            "artifact_id": stub.artifact_id, "view_id": stub.view_id,
            "slice_id": stub.slice_id, "package_id": stub.package_id,
            "revision": stub.revision, "target_entity_id": stub.target_entity_id,
        }
        r = client.create_issue(
            external_key=stub.comment_id, title=title, body=stub.body,
            tags=["mcp-comment"], meta=meta,
        )
        ref = IssueRef(system="logs-db", issue_id=r["issue_id"], synced_at=datetime.now(timezone.utc))
        set_issue_ref(repo_path, stub.comment_id, ref)
        journal.record(COMMENT_SYNC, {
            "comment_id": stub.comment_id,
            "issue_ref": ref.model_dump(mode="json"),
            "direction": "push",
            "actor": "architect_sync",
        })
        results.append({"comment_id": stub.comment_id, "issue_id": r["issue_id"]})
    return results

"""Behavioral-parity coverage for the ``arch_work_issue`` tool.

Exercises the full comment→issue→dev loop on openAG backends: resolve a
logs-db issue to a local comment stub, build + submit a WorkOrder, run the
proposer, apply + publish the resulting generation, commit with trailers, and
close the issue. Asserts the ``@arch_tool`` contract (envelope, observation
spans, mining telemetry), idempotent reuse, the dry-run path, the failed-job
soft envelope, and the error taxonomy. Behavioral coverage, NOT legacy AMS
output-shape equivalence.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from openag.comments.models import CommentStub
from openag.comments.store import write_stub

from opencode_arch.mcp.tools.arch_work_issue import arch_work_issue

# Make the sibling fixtures module importable so proposer plugin refs of the
# form '_openag_proposer_fixtures:valid_patch' resolve.
sys.path.insert(0, str(Path(__file__).parent))
import _openag_proposer_fixtures as fx  # noqa: E402


# ----------------------------------------------------------------------------
# Fakes + seeding helpers
# ----------------------------------------------------------------------------
class FakeClient:
    """Duck-typed stand-in for ``LogsDBClient`` (no live logs-db server)."""

    def __init__(self, issue: dict) -> None:
        self._issue = issue
        self.comments: list[dict] = []
        self.closed: list[dict] = []

    def get_issue(self, issue_id):
        return dict(self._issue)

    def post_comment(self, issue_id, *, author, body):
        rec = {"issue_id": issue_id, "author": author, "body": body}
        self.comments.append(rec)
        return rec

    def close_issue(self, issue_id, *, commit_sha, model_diff_digest, note):
        rec = {
            "issue_id": issue_id,
            "commit_sha": commit_sha,
            "model_diff_digest": model_diff_digest,
            "note": note,
        }
        self.closed.append(rec)
        return rec


def _seed_model(repo: Path) -> None:
    model_dir = repo / ".architecture" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "root.v3.yaml").write_text(
        yaml.safe_dump(
            {
                "meta": {"schema_version": "0.1"},
                "entities": {
                    "components": [
                        {"id": "C1", "name": "One", "kind": "Component"}
                    ]
                },
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )


def _seed_stub(repo: Path, comment_id: str = "cmt-1") -> str:
    stub = CommentStub(
        comment_id=comment_id,
        artifact_id="art-1",
        view_id="view-1",
        slice_id="S1",
        package_id="pkg-1",
        revision="0000001",
        body="Please add a Two component under One.",
        author="reviewer",
        created_at=datetime.now(timezone.utc),
    )
    write_stub(repo, stub)
    return comment_id


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Tester"], check=True
    )


def _issue(issue_id: int = 7, external_key: str = "cmt-1") -> dict:
    return {
        "issue_id": issue_id,
        "external_key": external_key,
        "url": "https://logs-db.example/issues/7",
    }


def _write_config(repo: Path, plugin: str) -> None:
    cfg_dir = repo / ".architecture" / "ai"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "proposer_config.yaml").write_text(
        yaml.safe_dump({"plugin": plugin, "enabled": True}), encoding="utf-8"
    )


def _full_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True)
    _seed_model(repo)
    _seed_stub(repo)
    _init_git(repo)
    return repo


# ----------------------------------------------------------------------------
# Happy path + contract
# ----------------------------------------------------------------------------
def test_parity_work_issue_success(tmp_path):
    repo = _full_repo(tmp_path, "happy")
    client = FakeClient(_issue())

    assert getattr(arch_work_issue, "__wrapped__", None) is not None

    out = asyncio.run(
        arch_work_issue(
            repo_path=str(repo),
            issue_id=7,
            proposer=fx.valid_patch,
            client=client,
        )
    )
    assert out["ok"] is True, out
    assert out["work_order_id"]
    assert out["job_id"]
    assert out["package_revision_to"]  # 7-digit gen id
    assert out["model_diff_digest"].startswith("sha256:")
    assert out["commit_sha"]
    assert out["issue_closed"] is True
    assert client.closed and client.closed[0]["commit_sha"] == out["commit_sha"]

    # @arch_tool spans
    records = read_journal(repo)
    assert any(
        r.get("component_id") == "tool:arch_work_issue"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
        for r in records
    ), records
    assert any(
        r.get("component_id") == "tool:arch_work_issue"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
        for r in records
    ), records

    # mining telemetry
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_work_issue"]
    assert len(drecords) == 1, drecords
    assert drecords[0]["outcome"] == "ok"


def test_parity_work_issue_dry_run(tmp_path):
    repo = _full_repo(tmp_path, "dry")
    client = FakeClient(_issue())
    out = asyncio.run(
        arch_work_issue(
            repo_path=str(repo),
            issue_id=7,
            dry_run=True,
            proposer=fx.valid_patch,
            client=client,
        )
    )
    assert out["ok"] is True, out
    assert out["dry_run"] is True
    assert out["package_revision_to"] is None
    assert out["commit_sha"] is None
    assert out.get("issue_closed") is not True
    assert client.closed == []


def test_parity_work_issue_idempotent_reuse(tmp_path):
    repo = _full_repo(tmp_path, "reuse")
    client = FakeClient(_issue())
    first = asyncio.run(
        arch_work_issue(
            repo_path=str(repo), issue_id=7, proposer=fx.valid_patch,
            client=client,
        )
    )
    assert first["ok"] is True

    second = asyncio.run(
        arch_work_issue(
            repo_path=str(repo), issue_id=7, proposer=fx.valid_patch,
            client=client,
        )
    )
    assert second["ok"] is True
    assert second["reused"] is True
    assert second["job_id"] == first["job_id"]


def test_parity_work_issue_failed_job_soft(tmp_path):
    repo = _full_repo(tmp_path, "failed")
    client = FakeClient(_issue())
    out = asyncio.run(
        arch_work_issue(
            repo_path=str(repo), issue_id=7, proposer=fx.invalid_patch,
            client=client,
        )
    )
    assert out["ok"] is True, out
    assert out["job_state"] == "failed"
    assert out["applied"] is False
    assert out["error"]
    assert out.get("commit_sha") is None
    assert client.closed == []


# ----------------------------------------------------------------------------
# Proposer resolution from config
# ----------------------------------------------------------------------------
def test_parity_work_issue_proposer_from_config(tmp_path):
    repo = _full_repo(tmp_path, "cfg")
    _write_config(repo, "_openag_proposer_fixtures:valid_patch")
    client = FakeClient(_issue())

    out = asyncio.run(
        arch_work_issue(repo_path=str(repo), issue_id=7, client=client)
    )
    assert out["ok"] is True, out
    assert out["issue_closed"] is True


# ----------------------------------------------------------------------------
# Error taxonomy
# ----------------------------------------------------------------------------
def test_parity_work_issue_repo_missing(tmp_path):
    out = asyncio.run(
        arch_work_issue(
            repo_path=str(tmp_path / "nope"), issue_id=7,
            client=FakeClient(_issue()),
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}


def test_parity_work_issue_empty_issue_id(tmp_path):
    repo = _full_repo(tmp_path, "badarg")
    out = asyncio.run(
        arch_work_issue(
            repo_path=str(repo), issue_id="", client=FakeClient(_issue())
        )
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_work_issue_no_external_key(tmp_path):
    repo = _full_repo(tmp_path, "nokey")
    client = FakeClient({"issue_id": 7, "url": "u"})  # no external_key
    out = asyncio.run(
        arch_work_issue(repo_path=str(repo), issue_id=7, client=client)
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "no_external_key"


def test_parity_work_issue_stub_missing(tmp_path):
    repo = tmp_path / "nostub"
    repo.mkdir(parents=True)
    _seed_model(repo)
    _init_git(repo)
    client = FakeClient(_issue(external_key="cmt-absent"))
    out = asyncio.run(
        arch_work_issue(repo_path=str(repo), issue_id=7, client=client)
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
    assert out["error"]["details"]["reason"] == "stub_missing"


def test_parity_work_issue_no_proposer_configured(tmp_path):
    repo = _full_repo(tmp_path, "noprop")
    client = FakeClient(_issue())
    out = asyncio.run(
        arch_work_issue(repo_path=str(repo), issue_id=7, client=client)
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "no_proposer_configured"

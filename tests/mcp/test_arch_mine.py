"""Tests for the ``arch_mine`` MCP tool.

``arch_mine`` exposes openAG's reservoir-mining pass behind the OCA
envelope: it reads opencode session chunks from a sessions SQLite DB,
runs the extract→propagate→reservoir path over the openAG model graph,
and writes PROPOSED promise records to a reservoir JSONL + a ledger.

The LLM provider is injected via the ``provider`` param so the test is
deterministic and offline — a captured-shape extract JSON is replayed
through ``OpencodeProvider``'s ``runner`` seam (no network, no subprocess).
"""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_mine import arch_mine

#: Captured-shape extract reply (mirrors openAG's captured_extract.json).
#: Fenced JSON exercises ``OpencodeProvider._extract_json`` fence handling.
_CAPTURED_EXTRACT = """\
```json
{"items": [
  {"target_node_id": "COMP-ENGINE", "attribute": "intent", "value": "sustain a verified graph", "kind": "attribute", "message_ref": "m2"},
  {"target_node_id": "", "attribute": "requirement", "value": "mine must be resumable", "kind": "requirement", "message_ref": "m1"}
]}
```"""


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def _sessions_db():
    """Return a builder for a minimal opencode sessions SQLite DB.

    Schema mirrors the subset ``openag.mining.sources.iter_chunks`` reads:
    ``project(worktree)``, ``session(id, directory, title)`` and
    ``part(id, session_id, time_created, data)``. The project worktree
    AND session directory basenames are the in-scope tributary slug
    ``openAG`` so ``resolve_scope`` keeps the session and a chunk is mined.
    """

    def _build(repo: Path) -> Path:
        db = Path(repo) / "sessions.sqlite"
        con = sqlite3.connect(db)
        try:
            con.execute("CREATE TABLE project (worktree TEXT)")
            con.execute(
                "CREATE TABLE session (id TEXT, directory TEXT, title TEXT)"
            )
            con.execute(
                "CREATE TABLE part (id TEXT, session_id TEXT, "
                "time_created INTEGER, data TEXT)"
            )
            con.execute(
                "INSERT INTO project (worktree) VALUES (?)",
                ("/home/dev/openAG",),
            )
            con.execute(
                "INSERT INTO session (id, directory, title) VALUES (?, ?, ?)",
                ("ses_a", "/home/dev/openAG", "mining session"),
            )
            con.execute(
                "INSERT INTO part (id, session_id, time_created, data) "
                "VALUES (?, ?, ?, ?)",
                ("p1", "ses_a", 1,
                 '{"type": "text", "text": "we need a resumable mine pass"}'),
            )
            con.commit()
        finally:
            con.close()
        return db

    return _build


@pytest.fixture
def _stub_provider():
    """A deterministic, offline provider replaying a captured extract."""
    from openag.llm.opencode import OpencodeProvider

    return OpencodeProvider(runner=lambda _prompt: _CAPTURED_EXTRACT)


def test_arch_mine_populates_reservoir(
    tmp_path, _seed_model, _sessions_db, _stub_provider
):
    _seed_model(tmp_path)
    db = _sessions_db(tmp_path)
    env = _run(
        arch_mine(
            repo_path=str(tmp_path),
            db=str(db),
            reservoir=str(tmp_path / "res.jsonl"),
            ledger=str(tmp_path / "led.jsonl"),
            provider=_stub_provider,
        )
    )
    assert env["ok"] is True
    assert env["records_added"] >= 1  # meaningful: root-fallback landings
    assert env["sessions_processed"] == 1
    assert "openAG" in env["repos"]
    assert (tmp_path / "res.jsonl").exists()
    assert (tmp_path / "led.jsonl").exists()


def test_arch_mine_missing_required_args_errors(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(
        arch_mine(repo_path=str(tmp_path), db="", reservoir="", ledger="")
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_mine_missing_model_returns_not_found(tmp_path, _sessions_db):
    db = _sessions_db(tmp_path)
    env = _run(
        arch_mine(
            repo_path=str(tmp_path),
            db=str(db),
            reservoir=str(tmp_path / "res.jsonl"),
            ledger=str(tmp_path / "led.jsonl"),
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"

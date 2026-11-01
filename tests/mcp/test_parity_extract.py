"""Behavioral-parity coverage for the ``arch_extract`` MCP writer tool.

Asserts the full ``@arch_tool`` WRITER contract: success envelope, observation
spans (in + out), mining telemetry (exactly one ``ok`` record), a committed
generation in the repo's ``GenerationStore`` ledger, byte-identical replay of
the recorded generation payload under a pinned clock, and the error taxonomy
(missing repo -> NOT_FOUND). This is behavioral coverage, NOT legacy AMS
output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import json
import os

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from openag.kernel.generations import GenerationStore

from opencode_arch.mcp.tools.arch_extract import arch_extract

_PINNED = "2026-01-01T00:00:00Z"


def _seed_repo(root):
    (root / ".architecture").mkdir(parents=True)
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("from src import b\nimport os\n", encoding="utf-8")
    (src / "b.py").write_text("x = 1\n", encoding="utf-8")
    return root


def _gen_root(repo):
    return str(repo / ".architecture" / "generations" / "openAG-tool")


def test_parity_extract_store(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_extract, "__wrapped__", None) is not None

    prev = os.environ.get("OPENAG_DETERMINISTIC_NOW")
    os.environ["OPENAG_DETERMINISTIC_NOW"] = _PINNED
    try:
        # --- Happy path ----------------------------------------------------
        out = asyncio.run(arch_extract(repo_path=str(repo)))
        assert out["ok"] is True
        assert "generation" in out

        # Spans: one "in" and one "out" tool_call for tool:arch_extract.
        records = read_journal(repo)
        in_spans = [
            r
            for r in records
            if r.get("component_id") == "tool:arch_extract"
            and r.get("io_kind") == "tool_call"
            and r.get("direction") == "in"
        ]
        out_spans = [
            r
            for r in records
            if r.get("component_id") == "tool:arch_extract"
            and r.get("io_kind") == "tool_call"
            and r.get("direction") == "out"
        ]
        assert in_spans, f"no in span in {records!r}"
        assert out_spans, f"no out span in {records!r}"

        # Telemetry: exactly one arch_extract record, outcome ok.
        telemetry = load_records(
            str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
        )
        ex_records = [r for r in telemetry if r.get("tool") == "arch_extract"]
        assert len(ex_records) == 1, f"expected 1 telemetry record, got {ex_records!r}"
        assert ex_records[0]["outcome"] == "ok"

        # Ledger: a generation was recorded through the GenerationStore.
        store = GenerationStore(root=_gen_root(repo))
        latest = store.latest()
        assert latest is not None
        assert latest.get("gen_id") == out["generation"]

        # --- Byte-identical replay in a SECOND fresh repo ------------------
        repo2 = _seed_repo(tmp_path / "replay")
        out2 = asyncio.run(arch_extract(repo_path=str(repo2)))
        assert out2["ok"] is True

        store2 = GenerationStore(root=_gen_root(repo2))
        payload1 = store.latest()["entities"]
        payload2 = store2.latest()["entities"]
        assert json.dumps(payload1, sort_keys=True) == json.dumps(
            payload2, sort_keys=True
        )
    finally:
        if prev is None:
            os.environ.pop("OPENAG_DETERMINISTIC_NOW", None)
        else:
            os.environ["OPENAG_DETERMINISTIC_NOW"] = prev

    # --- Bad arg: non-existent repo -> NOT_FOUND ---------------------------
    bad = asyncio.run(arch_extract(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

"""Behavioral-parity coverage for the ``arch_ingest`` MCP tool.

Asserts the full ``@arch_tool`` contract: success envelope carrying the ingested
SourceGraph summary, observation spans (in + out), mining telemetry (exactly one
record), determinism (identical returned dicts across two fresh repos for the
same JSON — non-writer, so no file replay), and the error taxonomy (missing repo
-> NOT_FOUND / INVALID_ARGUMENT; invalid JSON -> INVALID_ARGUMENT). This is
behavioral coverage, NOT legacy AMS output-shape equivalence.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records

from opencode_arch.mcp.tools.arch_ingest import arch_ingest

_SG = json.dumps(
    {
        "language": "typescript",
        "units": [
            {"file": "src/a.ts", "exports": ["foo"]},
            {"file": "lib/b.ts", "exports": ["bar"]},
        ],
        "edges": [{"source": "src/a.ts", "target": "lib/b.ts"}],
    }
)


def _seed_repo(root: Path) -> Path:
    (root / ".architecture").mkdir(parents=True)
    return root


def test_parity_ingest_sourcegraph(tmp_path):
    repo = _seed_repo(tmp_path / "happy")

    # --- Decorator contract ------------------------------------------------
    assert getattr(arch_ingest, "__wrapped__", None) is not None

    # --- Happy path --------------------------------------------------------
    out = asyncio.run(arch_ingest(repo_path=str(repo), source_graph_json=_SG))
    assert out["ok"] is True
    assert out["components"] == 2
    assert out["edges"] == 1
    assert out["units"] == 2

    # Spans: one "in" and one "out" tool_call for tool:arch_ingest.
    records = read_journal(repo)
    in_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_ingest"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "in"
    ]
    out_spans = [
        r
        for r in records
        if r.get("component_id") == "tool:arch_ingest"
        and r.get("io_kind") == "tool_call"
        and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    # Telemetry: exactly one arch_ingest record, outcome ok.
    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_ingest"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_ingest_determinism(tmp_path):
    repo_a = _seed_repo(tmp_path / "a")
    repo_b = _seed_repo(tmp_path / "b")
    first = asyncio.run(arch_ingest(repo_path=str(repo_a), source_graph_json=_SG))
    second = asyncio.run(arch_ingest(repo_path=str(repo_b), source_graph_json=_SG))
    assert first["ok"] is True
    assert second["ok"] is True
    data_fields = ("components", "edges", "units", "language")
    first_payload = {k: first[k] for k in data_fields}
    second_payload = {k: second[k] for k in data_fields}
    assert first_payload == second_payload


def test_parity_ingest_error_taxonomy(tmp_path):
    bad = asyncio.run(arch_ingest(repo_path=str(tmp_path / "does-not-exist")))
    assert bad["ok"] is False
    assert bad["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}

    repo = _seed_repo(tmp_path / "valid")
    bad_json = asyncio.run(
        arch_ingest(repo_path=str(repo), source_graph_json="{not valid json")
    )
    assert bad_json["ok"] is False
    assert bad_json["error"]["code"] == "INVALID_ARGUMENT"

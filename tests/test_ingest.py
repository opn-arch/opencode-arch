"""Tests for architect_ingest tool."""
import json
import pytest
from opencode_arch.mcp.tools.ingest import ingest_source_graph


@pytest.fixture
def tmp_repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("export function main() {}")
    (tmp_path / "src" / "utils.ts").write_text("export function helper() {}")
    return tmp_path


@pytest.mark.asyncio
async def test_ingest_basic(tmp_repo):
    graph_data = {
        "language": "typescript",
        "units": [
            {"file": "src/main.ts", "exports": [{"name": "main", "kind": "function"}]},
            {"file": "src/utils.ts", "exports": ["helper"]},
        ],
        "edges": [{"source": "src/main.ts", "target": "src/utils.ts", "symbols": ["helper"]}],
    }
    result = await ingest_source_graph(str(tmp_repo), json.dumps(graph_data))
    assert result["stored"] is True
    assert result["components"] >= 1
    assert result["units"] == 2
    assert result["edges"] == 1
    assert result["language"] == "typescript"
    assert (tmp_repo / ".architecture-model-extracted.yaml").exists()
    assert (tmp_repo / ".architecture-models" / "source-graph.json").exists()


@pytest.mark.asyncio
async def test_ingest_invalid_json(tmp_repo):
    result = await ingest_source_graph(str(tmp_repo), "not json{{{")
    assert "error" in result


@pytest.mark.asyncio
async def test_ingest_empty_graph(tmp_repo):
    result = await ingest_source_graph(str(tmp_repo), json.dumps({"units": [], "edges": []}))
    assert "error" in result


@pytest.mark.asyncio
async def test_ingest_with_interfaces(tmp_repo):
    """Cross-component edges produce interface contracts."""
    graph_data = {
        "language": "go",
        "units": [
            {"file": "pkg/auth/auth.go", "exports": [{"name": "Authenticate", "kind": "function"}]},
            {"file": "pkg/auth/token.go", "exports": [{"name": "ValidateToken", "kind": "function"}]},
            {"file": "pkg/api/handler.go", "exports": [{"name": "Handler", "kind": "class"}]},
            {"file": "pkg/main.go", "exports": [{"name": "main", "kind": "function"}]},
        ],
        "edges": [
            {"source": "pkg/api/handler.go", "target": "pkg/auth/auth.go", "symbols": ["Authenticate"]},
        ],
    }
    result = await ingest_source_graph(str(tmp_repo), json.dumps(graph_data))
    assert result["stored"] is True
    assert result["interfaces"] >= 2  # at least provides + requires

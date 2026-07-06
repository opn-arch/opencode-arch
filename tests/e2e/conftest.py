"""E2E test configuration and fixtures."""
from __future__ import annotations

import pytest
from pathlib import Path

# Default benchmark repos (small, fast tests)
BENCHMARK_REPOS = [
    {"name": "python-dotenv", "subdir": "src/dotenv", "url": "https://github.com/theskumar/python-dotenv"},
    {"name": "colorama", "subdir": "colorama", "url": "https://github.com/tartley/colorama"},
    {"name": "aiofiles", "subdir": "src/aiofiles", "url": "https://github.com/aio-libs/aiofiles"},
    {"name": "tqdm", "subdir": "tqdm", "url": "https://github.com/tqdm/tqdm"},
    {"name": "structlog", "subdir": "src/structlog", "url": "https://github.com/hynek/structlog"},
]

CLONE_DIR = Path("/tmp/test-repos")
# Project dir where MCP tools are available (not opencode-arch, which confuses
# the agent into reading tool source code instead of calling MCP tools)
PROJECT_DIR = Path(__file__).parent.parent.parent.parent / "architecture-model-standard"


def pytest_addoption(parser):
    parser.addoption("--e2e", action="store_true", default=False, help="Run expensive E2E benchmarks")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--e2e"):
        skip = pytest.mark.skip(reason="E2E tests require --e2e flag")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def project_dir():
    """Project directory where MCP tools are configured."""
    return PROJECT_DIR


@pytest.fixture(scope="session")
def results_dir():
    """Results output directory."""
    d = Path(__file__).parent.parent.parent / "results"
    d.mkdir(exist_ok=True)
    return d


@pytest.fixture(scope="session")
def clone_dir():
    """Directory where benchmark repos are cloned."""
    if not CLONE_DIR.exists():
        pytest.skip(f"Benchmark repos not cloned at {CLONE_DIR}")
    return CLONE_DIR


@pytest.fixture(params=[r["name"] for r in BENCHMARK_REPOS], scope="function")
def repo_info(request, clone_dir):
    """Parameterized fixture providing repo info + path."""
    name = request.param
    info = next(r for r in BENCHMARK_REPOS if r["name"] == name)
    repo_path = clone_dir / name
    if not repo_path.exists():
        pytest.skip(f"Repo {name} not cloned at {repo_path}")
    return {**info, "path": repo_path}

# Contributing to opencode-arch

Thanks for your interest in contributing! This guide will help you get started.

## Prerequisites

- Python 3.11+
- git
- [architecture-model-standard](https://github.com/anomalyco/architecture-model-standard) >= 1.0.0

## Development Setup

```bash
# Clone the repository
git clone https://github.com/anomalyco/opencode-arch.git
cd opencode-arch

# Install in editable mode with dev and mcp dependencies
pip install -e ".[dev,mcp]"
```

## Running Tests

```bash
# Run the full test suite (278 tests, ~20s)
pytest tests/ -v

# Skip end-to-end tests (faster iteration)
pytest tests/ -v -m "not e2e"

# Run a specific test file
pytest tests/test_scan.py -v
```

All tests must pass before submitting a PR. No regressions allowed.

## Code Style

- Standard Python conventions (PEP 8)
- Type hints on all public function signatures
- Docstrings on public modules, classes, and functions
- Keep functions focused and testable
- Telemetry failures must never block tool operation (swallow exceptions)

## Project Architecture

See [CONTEXT.md](./CONTEXT.md) for a full description of the project internals,
package structure, design decisions, and tool APIs.

Key principles:
- No external model calls — tools provide context only
- Token arbitrage — compress repos into minimal token budgets
- Graceful degradation — tools work without `.architecture-model.yaml`
- MCP optional — tools work as standalone async functions

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Write tests for your changes (TDD preferred)
4. Ensure all tests pass (`pytest tests/ -v`)
5. Commit with a clear message describing the "why"
6. Open a PR against `main`

PRs should:
- Include tests for new functionality
- Not break existing tests
- Have a clear description of what changed and why

## Reporting Issues

Report bugs and feature requests on [GitHub Issues](https://github.com/anomalyco/opencode-arch/issues).

Include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant error output

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

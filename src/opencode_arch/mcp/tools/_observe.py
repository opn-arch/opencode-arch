"""Proprioceptive instrumentation wrapper for OCA ``arch_*`` tool handlers.

``observe_tool_call(repo_path, tool_name)`` is a sync context manager that OCA
tool handlers wrap their body in. It does two things:

1. **Binds the repo observation context** via
   :func:`openag.observe.decorator.bind_repo` so that any downstream openAG
   kernel call made inside the wrapped body emits its observations into the
   same repo's journal (``<repo>/.architecture/observations.jsonl``).
2. **Emits one ``tool_call`` observation** tagged
   ``component_id=f"oca:{tool_name}"`` at entry.

openAG imports are **lazy** (resolved inside the function body) and
**fail-soft**: this module stays importable even if openAG is absent, and
instrumentation NEVER changes a tool's success/failure outcome. If the repo
cannot be resolved (bad/missing path), the context manager is a pure no-op
that still yields — the wrapped tool body then runs and raises its own
validation error so the existing envelope error handling produces the
correct ``INVALID_ARGUMENT`` / ``NOT_FOUND`` code.

Note: this helper is deliberately NOT named with a ``*_tool`` suffix — that
suffix is reserved in this package for SI&L-instrumented MCP tool *handlers*
(enforced by ``tests/mcp/test_instrumentation.py``), and this context
manager is a wrapper used BY handlers, not a handler itself.
"""
from __future__ import annotations

import contextlib


@contextlib.contextmanager
def observe_tool_call(repo_path: str, tool_name: str):
    """Bind repo observation context + emit one ``tool_call`` observation.

    On a resolvable repo: binds the openAG observation context and emits a
    ``tool_call`` observation before yielding inside the bound scope. On any
    resolve/import failure: a pure no-op that still yields (never raises,
    never binds, never emits).
    """
    try:
        from opencode_arch.mcp.envelope import resolve_repo
        from openag.observe.decorator import bind_repo, emit

        resolved = resolve_repo(repo_path)
    except (ValueError, FileNotFoundError, NotADirectoryError, ImportError):
        # Bad/missing repo or openAG absent: pure no-op, still yield so the
        # wrapped body runs and raises its own validation error. These are
        # exactly the repo-validation errors tool_result maps (plus
        # ImportError for openAG absence) — a narrow catch so genuine
        # programmer bugs in resolve_repo/imports still surface.
        yield
        return

    with bind_repo(resolved):
        emit("oca:" + tool_name, "tool_call", "in", tool_name)
        yield

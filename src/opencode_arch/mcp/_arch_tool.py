"""The ``@arch_tool`` decorator for OCA ``arch_*`` MCP tool handlers.

``arch_tool`` composes three concerns around an ``async def`` handler whose
repo is passed as ``repo_path`` (positional ``args[0]`` or keyword):

1. **Envelope normalization** — the handler's return value and any raised
   exception are normalized into the uniform envelope shape by reusing
   :func:`opencode_arch.mcp.envelope.tool_result` (composed, never forked, so
   the nested envelope + exception→code mapping stays identical).
2. **Proprioceptive spans** — on a resolvable repo, an ``in`` span is emitted
   before the handler runs and an ``out`` span after, both tagged
   ``component_id=f"tool:{name}"``, ``io_kind="tool_call"`` (the MCP-tool
   distinction is carried by the ``tool:`` component_id prefix vs the legacy
   ``oca:`` prefix).
3. **Mining telemetry** — one append-only record per invocation is written to
   the repo's tool-telemetry reservoir, carrying a unique ``content_hash`` so
   every invocation is recorded (not deduped).

All side effects (bind / span / telemetry) are **fail-soft**: no exception
from them can alter or replace the returned envelope. If the repo cannot be
resolved (the same narrow repo-validation errors ``_observe`` catches, plus
``ImportError`` for openAG absence), the handler still runs through envelope
normalization — just without binding / emitting / telemetry.
"""
from __future__ import annotations

import functools
import hashlib
import uuid
from typing import Any, Awaitable, Callable

from opencode_arch.mcp.envelope import tool_result


def _best_effort_digest(value: Any) -> str:
    """Return a stable short digest for ``value``; never raises."""
    try:
        from openag.observe.decorator import _digest

        return _digest(value)
    except Exception:
        try:
            return hashlib.sha1(repr(value).encode("utf-8", "replace")).hexdigest()
        except Exception:
            return ""


def arch_tool(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[dict]]:
    """Decorate an async MCP tool: envelope + spans + mining telemetry."""

    name = func.__name__
    normalized = tool_result(func)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> dict:
        repo_path = args[0] if args else kwargs.get("repo_path")
        args_digest = _best_effort_digest((args, kwargs))

        resolved = None
        bind_cm = None
        emit = None
        try:
            from opencode_arch.mcp.envelope import resolve_repo
            from openag.observe.decorator import bind_repo, emit as _emit

            resolved = resolve_repo(repo_path)
            bind_cm = bind_repo(resolved)
            emit = _emit
        except (ValueError, FileNotFoundError, NotADirectoryError, ImportError):
            # Bad/missing repo or openAG absent: run the handler through
            # envelope normalization with NO side effects.
            return await normalized(*args, **kwargs)

        try:
            with bind_cm:
                _safe_emit(emit, name, "in", args_digest)
                envelope = await normalized(*args, **kwargs)
                _safe_emit(emit, name, "out", _best_effort_digest(envelope))
                _safe_append_telemetry(resolved, name, envelope, args_digest)
                return envelope
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # Side-effect bootstrap (e.g. bind) failed: fall back to a plain
            # normalized run so the envelope is never altered.
            return await normalized(*args, **kwargs)

    return wrapper


def _safe_emit(emit, name: str, direction: str, digest: str) -> None:
    try:
        emit("tool:" + name, "tool_call", direction, name, digest)
    except Exception:
        pass


def _safe_append_telemetry(resolved, name: str, envelope: dict, args_digest: str) -> None:
    try:
        from openag.mining.reservoir import append_records
        from openag.observe._fields import now_iso

        outcome = "ok" if envelope.get("ok") else envelope["error"]["code"]
        record = {
            "tool": name,
            "outcome": outcome,
            "repo": str(resolved),
            "ts": now_iso(),
            "args_digest": args_digest,
        }
        record["content_hash"] = hashlib.sha256(
            (repr(sorted(record.items())) + uuid.uuid4().hex).encode("utf-8", "replace")
        ).hexdigest()
        path = str(resolved / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
        append_records(path, [record])
    except Exception:
        pass

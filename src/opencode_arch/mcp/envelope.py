"""MCP result envelope helpers.

Provides ``ok`` / ``err`` builders, standard error codes, ``resolve_repo``
path validation, and the ``tool_result`` decorator that normalizes async
MCP tool return values and exceptions into a uniform envelope shape.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Awaitable, Callable

ERROR_CODES: frozenset[str] = frozenset({
    "NOT_FOUND",
    "INVALID_ARGUMENT",
    "SCHEMA_VIOLATION",
    "PRECONDITION_FAILED",
    "INTERNAL",
    "PHASE1_MISMATCH",
})


def ok(data: dict | None = None) -> dict:
    """Return a success envelope, merging ``data`` into the result."""
    if data is None:
        return {"ok": True}
    if "ok" in data:
        raise ValueError("data must not contain reserved key 'ok'")
    return {"ok": True, **data}


def err(code: str, message: str, **details: Any) -> dict:
    """Return an error envelope with the given code, message, and details."""
    if code not in ERROR_CODES:
        raise ValueError(
            f"Unknown error code {code!r}. Valid codes: {sorted(ERROR_CODES)}"
        )
    return {
        "ok": False,
        "error": {"code": code, "message": message, "details": details},
    }


def resolve_repo(repo_path: str) -> Path:
    """Resolve and validate a repository path."""
    if not repo_path or not isinstance(repo_path, str):
        raise ValueError("repo_path must be a non-empty string")
    resolved = Path(repo_path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"repo_path does not exist: {resolved}")
    if not resolved.is_dir():
        raise NotADirectoryError(f"repo_path is not a directory: {resolved}")
    return resolved


def tool_result(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[dict]]:
    """Decorate an async MCP tool to normalize returns and exceptions."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> dict:
        try:
            result = await func(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except ValueError as exc:
            return err("INVALID_ARGUMENT", str(exc))
        except FileNotFoundError as exc:
            return err("NOT_FOUND", str(exc))
        except NotADirectoryError as exc:
            return err("INVALID_ARGUMENT", str(exc))
        except Exception as exc:
            try:
                import jsonschema

                if isinstance(exc, jsonschema.ValidationError):
                    return err(
                        "SCHEMA_VIOLATION",
                        exc.message,
                        path=list(exc.path),
                    )
            except ImportError:
                pass
            return err("INTERNAL", f"{type(exc).__name__}: {exc}")

        if isinstance(result, dict) and "ok" in result:
            return result
        return ok(result if isinstance(result, dict) else None)

    return wrapper

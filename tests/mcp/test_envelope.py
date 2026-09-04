"""Tests for MCP result envelope helpers."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from opencode_arch.mcp.envelope import (
    ERROR_CODES,
    err,
    ok,
    resolve_repo,
    tool_result,
)


def test_ok_empty_returns_ok_true():
    assert ok() == {"ok": True}


def test_ok_merges_data():
    result = ok({"foo": 1, "bar": [1, 2]})
    assert result == {"ok": True, "foo": 1, "bar": [1, 2]}


def test_ok_rejects_ok_key_in_data():
    with pytest.raises(ValueError):
        ok({"ok": False})


def test_err_valid_code():
    result = err("NOT_FOUND", "gone")
    assert result == {
        "ok": False,
        "error": {"code": "NOT_FOUND", "message": "gone", "details": {}},
    }


def test_err_with_details():
    result = err("NOT_FOUND", "gone", package_id="p1")
    assert result["error"]["details"] == {"package_id": "p1"}


def test_err_unknown_code_raises():
    with pytest.raises(ValueError) as ei:
        err("BAD_CODE", "x")
    for code in ERROR_CODES:
        assert code in str(ei.value)


def test_error_codes_frozen():
    assert isinstance(ERROR_CODES, frozenset)
    assert ERROR_CODES == frozenset({
        "NOT_FOUND",
        "INVALID_ARGUMENT",
        "SCHEMA_VIOLATION",
        "PRECONDITION_FAILED",
        "INTERNAL",
        "PHASE1_MISMATCH",
    })


def test_resolve_repo_returns_absolute_path(tmp_path):
    result = resolve_repo(str(tmp_path))
    assert result == tmp_path.resolve()
    assert result.is_absolute()


def test_resolve_repo_empty_string_raises():
    with pytest.raises(ValueError):
        resolve_repo("")


def test_resolve_repo_none_raises():
    with pytest.raises(ValueError):
        resolve_repo(None)  # type: ignore[arg-type]


def test_resolve_repo_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_repo(str(tmp_path / "does_not_exist"))


def test_resolve_repo_not_directory_raises(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hi")
    with pytest.raises(NotADirectoryError):
        resolve_repo(str(f))


def test_tool_result_wraps_return_dict_without_ok_key():
    @tool_result
    async def f():
        return {"x": 1}

    assert asyncio.run(f()) == {"ok": True, "x": 1}


def test_tool_result_passes_through_envelope():
    envelope = {"ok": False, "error": {"code": "NOT_FOUND", "message": "m", "details": {}}}

    @tool_result
    async def f():
        return envelope

    assert asyncio.run(f()) == envelope


def test_tool_result_catches_value_error():
    @tool_result
    async def f():
        raise ValueError("bad arg")

    result = asyncio.run(f())
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ARGUMENT"
    assert result["error"]["message"] == "bad arg"


def test_tool_result_catches_file_not_found():
    @tool_result
    async def f():
        raise FileNotFoundError("missing")

    result = asyncio.run(f())
    assert result["error"]["code"] == "NOT_FOUND"


def test_tool_result_catches_not_a_directory():
    @tool_result
    async def f():
        raise NotADirectoryError("not dir")

    result = asyncio.run(f())
    assert result["error"]["code"] == "INVALID_ARGUMENT"


def test_tool_result_catches_generic_exception():
    @tool_result
    async def f():
        raise RuntimeError("boom")

    result = asyncio.run(f())
    assert result["error"]["code"] == "INTERNAL"
    assert "RuntimeError" in result["error"]["message"]
    assert "boom" in result["error"]["message"]


def test_tool_result_catches_jsonschema_violation():
    import jsonschema

    @tool_result
    async def f():
        raise jsonschema.ValidationError("bad", path=["a", "b"])

    result = asyncio.run(f())
    assert result["error"]["code"] == "SCHEMA_VIOLATION"
    assert result["error"]["message"] == "bad"
    assert result["error"]["details"]["path"] == ["a", "b"]


def test_tool_result_does_not_catch_keyboard_interrupt():
    @tool_result
    async def f():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        asyncio.run(f())


def test_tool_result_does_not_catch_system_exit():
    @tool_result
    async def f():
        raise SystemExit()

    with pytest.raises(SystemExit):
        asyncio.run(f())


def test_tool_result_preserves_name_and_doc():
    @tool_result
    async def my_tool():
        """docstring here"""
        return {}

    assert my_tool.__name__ == "my_tool"
    assert my_tool.__doc__ == "docstring here"


def test_tool_result_supports_async():
    @tool_result
    async def f():
        await asyncio.sleep(0)
        return {"async": True}

    assert asyncio.run(f()) == {"ok": True, "async": True}

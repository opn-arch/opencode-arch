"""Guardrail: every MCP tool handler must be SI&L-instrumented."""


def test_every_mcp_tool_handler_is_instrumented():
    import pkgutil, importlib
    import opencode_arch.mcp.tools as pkg
    missing = []
    for info in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        m = importlib.import_module(info.name)
        for name, fn in vars(m).items():
            if name.endswith("_tool") and callable(fn):
                if getattr(fn, "__module__", None) != info.name:
                    continue  # re-exports handled at definition site
                if not getattr(fn, "__sil_instrumented__", False):
                    missing.append(f"{info.name}:{name}")
    assert not missing, f"un-instrumented tools: {missing}"

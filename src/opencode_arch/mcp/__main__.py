"""Allow running as: python -m opencode_arch.mcp"""
from opencode_arch.mcp.server import mcp

if mcp is not None:
    mcp.run()
else:
    print("Error: mcp package not installed. Install with: pip install 'opencode-arch[mcp]'")
    raise SystemExit(1)

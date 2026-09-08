# src/opencode_arch/session.py
import os
import uuid


def resolve_session_id() -> str:
    v = os.environ.get("OPENCODE_SESSION_ID")
    if v:
        return v
    return f"session:{uuid.uuid4()}-cli"

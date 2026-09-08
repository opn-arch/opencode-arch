# tests/test_session.py
import os
from opencode_arch.session import resolve_session_id

def test_resolves_from_env(monkeypatch):
    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_abc")
    assert resolve_session_id() == "ses_abc"

def test_synthesises_when_absent(monkeypatch):
    monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
    v = resolve_session_id()
    assert v.startswith("session:") and v.endswith("-cli")

import respx, httpx, pytest
from opencode_arch.logs_db.client import LogsDBClient, LogsDBUnreachable

@respx.mock
def test_create_issue_ok():
    route = respx.post("http://logs.local/issues").mock(
        return_value=httpx.Response(200, json={"issue_id": 42, "url": "http://x/42", "created_at": "2026-09-05T00:00:00Z"})
    )
    c = LogsDBClient("http://logs.local")
    r = c.create_issue(external_key="c-1", title="t", body="b", tags=["x"], meta={"k": "v"})
    assert r["issue_id"] == 42
    assert route.called

@respx.mock
def test_create_issue_conflict_returns_existing():
    respx.post("http://logs.local/issues").mock(
        return_value=httpx.Response(409, json={"issue_id": 42, "reason": "duplicate_external_key"})
    )
    r = LogsDBClient("http://logs.local").create_issue(
        external_key="c-1", title="t", body="b", tags=[], meta={}
    )
    assert r["issue_id"] == 42

@respx.mock
def test_unreachable_raises():
    respx.post("http://logs.local/issues").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(LogsDBUnreachable):
        LogsDBClient("http://logs.local", retries=1).create_issue(
            external_key="c", title="t", body="b", tags=[], meta={}
        )

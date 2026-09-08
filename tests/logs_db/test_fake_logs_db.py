from tests.fixtures.fake_logs_db import FakeLogsDB

def test_fake_create_get_close():
    with FakeLogsDB() as fake:
        c = fake.client
        r = c.create_issue(external_key="c-1", title="t", body="b", tags=[], meta={})
        iid = r["issue_id"]
        assert c.get_issue(iid)["state"] == "open"
        c.close_issue(iid, commit_sha="deadbeef", model_diff_digest="sha256:00", note="ok")
        assert c.get_issue(iid)["state"] == "closed"

def test_fake_duplicate_returns_existing():
    with FakeLogsDB() as fake:
        c = fake.client
        r1 = c.create_issue(external_key="c-x", title="a", body="b", tags=[], meta={})
        r2 = c.create_issue(external_key="c-x", title="a", body="b", tags=[], meta={})
        assert r1["issue_id"] == r2["issue_id"]

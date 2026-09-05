"""HTTP client for logs-db (Plan A consumed surface)."""

from __future__ import annotations

import time
from typing import Any, Mapping, Sequence

import httpx


class LogsDBError(RuntimeError):
    pass


class LogsDBUnreachable(LogsDBError):
    pass


class LogsDBConflict(LogsDBError):
    pass


class LogsDBForbidden(LogsDBError):
    pass


class LogsDBClient:
    def __init__(
        self,
        base_url: str,
        *,
        auth_token: str | None = None,
        timeout: float = 10.0,
        retries: int = 3,
        backoff: Sequence[float] = (0.5, 2.0, 8.0),
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self._client = httpx.Client(timeout=timeout, headers=self._headers)
        self._retries = retries
        self._backoff = backoff

    def _request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None) -> httpx.Response:
        url = f"{self._base}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._retries):
            try:
                r = self._client.request(method, url, json=json)
            except httpx.ConnectError as e:
                last_exc = e
                if attempt < self._retries - 1:
                    time.sleep(self._backoff[min(attempt, len(self._backoff) - 1)])
                    continue
                raise LogsDBUnreachable(str(e)) from e
            if r.status_code < 500:
                return r
            last_exc = LogsDBError(f"{r.status_code}: {r.text[:200]}")
            if attempt < self._retries - 1:
                time.sleep(self._backoff[min(attempt, len(self._backoff) - 1)])
        assert last_exc is not None
        raise last_exc

    def create_issue(
        self, *, external_key: str, title: str, body: str,
        tags: Sequence[str], meta: Mapping[str, Any],
    ) -> dict:
        r = self._request("POST", "/issues", json={
            "external_key": external_key, "title": title,
            "body": body, "tags": list(tags), "meta": dict(meta),
        })
        if r.status_code == 409:
            data = r.json()
            if "issue_id" in data:
                return data
            raise LogsDBConflict(r.text)
        if r.status_code == 403:
            raise LogsDBForbidden(r.text)
        r.raise_for_status()
        return r.json()

    def get_issue(self, issue_id: int | str) -> dict:
        r = self._request("GET", f"/issues/{issue_id}")
        r.raise_for_status()
        return r.json()

    def post_comment(self, issue_id: int | str, *, author: str, body: str) -> dict:
        r = self._request("POST", f"/issues/{issue_id}/comments",
                          json={"author": author, "body": body})
        r.raise_for_status()
        return r.json()

    def close_issue(
        self, issue_id: int | str, *, commit_sha: str, model_diff_digest: str, note: str,
    ) -> dict:
        r = self._request("POST", f"/issues/{issue_id}/close", json={
            "commit_sha": commit_sha, "model_diff_digest": model_diff_digest, "note": note,
        })
        r.raise_for_status()
        return r.json()

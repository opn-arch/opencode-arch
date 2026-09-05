"""In-process FakeLogsDB served over Werkzeug for contract tests."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from wsgiref.simple_server import make_server, WSGIRequestHandler

from flask import Flask, jsonify, request

from opencode_arch.logs_db.client import LogsDBClient


class _SilentHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: D401
        return


class FakeLogsDB:
    def __init__(self, port: int = 0):
        self._port = port
        self._app = Flask(__name__)
        self._issues: dict[int, dict] = {}
        self._by_key: dict[str, int] = {}
        self._next_id = 1
        self._register_routes()

    def _register_routes(self):
        app = self._app

        @app.post("/issues")
        def create():
            data = request.get_json(force=True)
            key = data["external_key"]
            if key in self._by_key:
                iid = self._by_key[key]
                return jsonify(self._issues[iid]), 409
            iid = self._next_id
            self._next_id += 1
            issue = {
                "issue_id": iid,
                "external_key": key,
                "title": data["title"],
                "body": data["body"],
                "tags": data.get("tags", []),
                "meta": data.get("meta", {}),
                "state": "open",
                "comments": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "url": f"http://fake/issues/{iid}",
            }
            self._issues[iid] = issue
            self._by_key[key] = iid
            return jsonify(issue), 200

        @app.get("/issues/<int:iid>")
        def get(iid):
            return jsonify(self._issues[iid])

        @app.post("/issues/<int:iid>/comments")
        def comment(iid):
            data = request.get_json(force=True)
            entry = {
                "comment_id": len(self._issues[iid]["comments"]) + 1,
                "author": data["author"], "body": data["body"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._issues[iid]["comments"].append(entry)
            return jsonify(entry)

        @app.post("/issues/<int:iid>/close")
        def close(iid):
            data = request.get_json(force=True)
            self._issues[iid]["state"] = "closed"
            self._issues[iid]["close_meta"] = data
            return jsonify({"issue_id": iid, "state": "closed"})

    def __enter__(self):
        self._server = make_server("127.0.0.1", self._port, self._app, handler_class=_SilentHandler)
        self._port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.client = LogsDBClient(f"http://127.0.0.1:{self._port}", retries=1)
        return self

    def __exit__(self, *a):
        self._server.shutdown()
        self._server.server_close()

    @property
    def issues(self) -> dict[int, dict]:
        return self._issues

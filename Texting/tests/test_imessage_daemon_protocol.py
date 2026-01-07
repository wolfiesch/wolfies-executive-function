import json
import os
import tempfile
import threading
import time
from pathlib import Path

import socket

import pytest


from gateway.imessage_daemon import DaemonServer


class FakeService:
    def health(self):
        return {"ok": True}

    def unread_count(self):
        return {"count": 1}

    def unread_messages(self, *, limit=20):
        return {"messages": [{"text": "hi"}][:limit]}

    def recent(self, *, limit=10):
        return {"messages": [{"text": "recent"}][:limit]}

    def text_search(self, *, query, limit=20, since=None):
        return {"results": [{"q": query}][:limit]}

    def messages_by_phone(self, *, phone, limit=20):
        return {"messages": [{"phone": phone}][:limit]}

    def bundle(self, params):
        return {"meta": {"params": params}}


def _call(socket_path: Path, payload: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(socket_path))
        s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        buf = bytearray()
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
            if b"\n" in chunk:
                break
        line = bytes(buf).split(b"\n", 1)[0]
        return json.loads(line.decode("utf-8"))

def _short_socket_path() -> Path:
    # macOS AF_UNIX has a short path length limit; pytest tmp_path can exceed it.
    d = Path(tempfile.mkdtemp(prefix="wolfies-imsgd-", dir="/tmp"))
    return d / "daemon.sock"


def test_daemon_unknown_method(tmp_path: Path):
    sock = _short_socket_path()
    server = DaemonServer(sock, FakeService())
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        resp = _call(sock, {"id": "1", "v": 1, "method": "nope", "params": {}})
        assert resp["id"] == "1"
        assert resp["ok"] is False
        assert resp["error"]["code"] == "UNKNOWN_METHOD"
    finally:
        server.shutdown()
        server.server_close()
        try:
            sock.parent.rmdir()
        except Exception:
            pass


def test_daemon_text_search_requires_query(tmp_path: Path):
    sock = _short_socket_path()
    server = DaemonServer(sock, FakeService())
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        resp = _call(sock, {"id": "2", "v": 1, "method": "text_search", "params": {"limit": 1}})
        assert resp["ok"] is False
        assert "query is required" in resp["error"]["message"]
    finally:
        server.shutdown()
        server.server_close()
        try:
            sock.parent.rmdir()
        except Exception:
            pass


def test_daemon_health_ok(tmp_path: Path):
    sock = _short_socket_path()
    server = DaemonServer(sock, FakeService())
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        resp = _call(sock, {"id": "3", "v": 1, "method": "health", "params": {}})
        assert resp["ok"] is True
        assert resp["result"]["ok"] is True
        assert "meta" in resp and "server_ms" in resp["meta"]
    finally:
        server.shutdown()
        server.server_close()
        try:
            sock.parent.rmdir()
        except Exception:
            pass

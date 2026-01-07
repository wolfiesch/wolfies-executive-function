#!/usr/bin/env python3
"""
Thin client for the iMessage daemon (stdlib-only).

Design goal:
- keep per-call overhead minimal (no heavy imports, no SQLite)
- send one request over a UNIX socket and print JSON to stdout

Spec:
- Texting/gateway/DAEMON_SPEC.md
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import uuid
from pathlib import Path
from typing import Any


DEFAULT_SOCKET_PATH = Path.home() / ".wolfies-imessage" / "daemon.sock"


def _json_dumps(obj: Any, *, pretty: bool) -> str:
    if pretty:
        return json.dumps(obj, indent=2, default=str)
    return json.dumps(obj, separators=(",", ":"), default=str)


def _call_daemon(socket_path: Path, request: dict[str, Any], *, timeout_s: float) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout_s)
        s.connect(str(socket_path))
        data = (_json_dumps(request, pretty=False) + "\n").encode("utf-8")
        s.sendall(data)

        # Read one NDJSON response line.
        buf = bytearray()
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
            if b"\n" in chunk:
                break
        line = bytes(buf).split(b"\n", 1)[0]
        if not line:
            raise RuntimeError("empty response from daemon")
        return json.loads(line.decode("utf-8"))


def _emit_response(resp: dict[str, Any], *, raw: bool, pretty: bool) -> None:
    if raw:
        print(_json_dumps(resp, pretty=pretty))
        return
    if not resp.get("ok"):
        # Print a stable error shape for tool runners.
        err = resp.get("error") or {"code": "ERROR", "message": "unknown error", "details": None}
        out = {"ok": False, "error": err}
        print(_json_dumps(out, pretty=pretty))
        return
    print(_json_dumps(resp.get("result"), pretty=pretty))


def _build_request(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(uuid.uuid4()), "v": 1, "method": method, "params": params}


def main() -> int:
    parser = argparse.ArgumentParser(description="Wolfies iMessage daemon thin client")
    parser.add_argument("--socket", default=str(DEFAULT_SOCKET_PATH), help="UNIX socket path")
    parser.add_argument("--timeout", type=float, default=2.0, help="Socket timeout seconds")
    parser.add_argument("--raw-response", action="store_true", help="Print the full response wrapper")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON (increases token cost)")
    parser.add_argument("--compact", action="store_true", help="Ask daemon to reduce output fields (LLM-friendly)")
    parser.add_argument("--minimal", action="store_true", help="Ask daemon for minimal JSON preset (lowest token cost)")
    parser.add_argument("--fields", default=None, help="Comma-separated allowlist of JSON fields to include")
    parser.add_argument("--max-text-chars", type=int, default=None, help="Truncate large text fields (e.g., 200)")

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="Daemon health check")

    sub.add_parser("unread-count", help="Unread count only")

    p_unread = sub.add_parser("unread", help="Unread messages (bounded)")
    p_unread.add_argument("--limit", type=int, default=20)

    p_recent = sub.add_parser("recent", help="Recent messages (bounded)")
    p_recent.add_argument("--limit", type=int, default=10)

    p_search = sub.add_parser("text-search", help="Keyword search (bounded)")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.add_argument("--since", default=None, help="ISO date/time, e.g. 2026-01-01 or 2026-01-01T00:00:00")

    p_msgs = sub.add_parser("messages-by-phone", help="Last N messages for a phone number")
    p_msgs.add_argument("phone")
    p_msgs.add_argument("--limit", type=int, default=20)

    p_bundle = sub.add_parser("bundle", help="Canonical multi-op bundle workload")
    p_bundle.add_argument("--include", default=None, help="Comma-separated sections to include")
    p_bundle.add_argument("--unread-limit", type=int, default=20)
    p_bundle.add_argument("--recent-limit", type=int, default=10)
    p_bundle.add_argument("--query", default=None)
    p_bundle.add_argument("--search-limit", type=int, default=20)
    p_bundle.add_argument("--phone", default=None)
    p_bundle.add_argument("--messages-limit", type=int, default=20)

    args = parser.parse_args()
    socket_path = Path(args.socket)

    # Friendly error when daemon isn't running.
    if not socket_path.exists():
        out = {
            "ok": False,
            "error": {
                "code": "DAEMON_NOT_RUNNING",
                "message": f"Socket not found: {socket_path}",
                "details": {"socket": str(socket_path)},
            },
        }
        print(_json_dumps(out, pretty=args.pretty))
        return 2

    if args.cmd == "health":
        req = _build_request("health", {})
    elif args.cmd == "unread-count":
        req = _build_request("unread_count", {})
    elif args.cmd == "unread":
        req = _build_request(
            "unread_messages",
            {
                "limit": args.limit,
                "compact": bool(args.compact),
                "minimal": bool(args.minimal),
                "fields": args.fields,
                "max_text_chars": args.max_text_chars,
            },
        )
    elif args.cmd == "recent":
        req = _build_request(
            "recent",
            {
                "limit": args.limit,
                "compact": bool(args.compact),
                "minimal": bool(args.minimal),
                "fields": args.fields,
                "max_text_chars": args.max_text_chars,
            },
        )
    elif args.cmd == "text-search":
        req = _build_request(
            "text_search",
            {
                "query": args.query,
                "limit": args.limit,
                "since": args.since,
                "compact": bool(args.compact),
                "minimal": bool(args.minimal),
                "fields": args.fields,
                "max_text_chars": args.max_text_chars,
            },
        )
    elif args.cmd == "messages-by-phone":
        req = _build_request(
            "messages_by_phone",
            {
                "phone": args.phone,
                "limit": args.limit,
                "compact": bool(args.compact),
                "minimal": bool(args.minimal),
                "fields": args.fields,
                "max_text_chars": args.max_text_chars,
            },
        )
    elif args.cmd == "bundle":
        params = {
            "include": args.include,
            "unread_limit": args.unread_limit,
            "recent_limit": args.recent_limit,
            "query": args.query,
            "search_limit": args.search_limit,
            "phone": args.phone,
            "messages_limit": args.messages_limit,
            "compact": bool(args.compact),
            "minimal": bool(args.minimal),
            "fields": args.fields,
            "max_text_chars": args.max_text_chars,
        }
        req = _build_request("bundle", params)
    else:  # pragma: no cover
        raise SystemExit("unknown command")

    try:
        resp = _call_daemon(socket_path, req, timeout_s=float(args.timeout))
    except Exception as exc:
        out = {
            "ok": False,
            "error": {
                "code": "CONNECT_FAILED",
                "message": str(exc),
                "details": {
                    "socket_path": str(socket_path),
                    "exception_type": type(exc).__name__,
                    "exception_args": exc.args,
                },
            },
        }
        print(_json_dumps(out, pretty=args.pretty))
        return 2

    _emit_response(resp, raw=bool(args.raw_response), pretty=bool(args.pretty))
    return 0 if resp.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

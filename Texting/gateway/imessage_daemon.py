#!/usr/bin/env python3
"""
iMessage daemon (Python) - warm, low-latency read path.

This daemon keeps expensive resources hot (imports, SQLite connection, caches)
and serves requests over a UNIX domain socket using NDJSON framing.

Spec:
- Texting/gateway/DAEMON_SPEC.md
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import socketserver
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from gateway.output_utils import apply_output_controls, parse_fields


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))


DEFAULT_STATE_DIR = Path.home() / ".wolfies-imessage"
DEFAULT_SOCKET_PATH = DEFAULT_STATE_DIR / "daemon.sock"
DEFAULT_PID_PATH = DEFAULT_STATE_DIR / "daemon.pid"

def _now_iso() -> str:
    return datetime.now().isoformat()


def _json_line(obj: Any) -> bytes:
    return (json.dumps(obj, separators=(",", ":"), default=str) + "\n").encode("utf-8")


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except Exception:
        return None


def _is_socket_listening(socket_path: Path, timeout_s: float = 0.15) -> bool:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect(str(socket_path))
        return True
    except Exception:
        return False


def _extract_controls(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "compact": bool(params.get("compact", False)),
        "minimal": bool(params.get("minimal", False)),
        "fields": parse_fields(params.get("fields")),
        "max_text_chars": int(params["max_text_chars"]) if params.get("max_text_chars") is not None else None,
    }


@dataclass
class DaemonConfig:
    """Daemon configuration."""

    socket_path: Path
    pid_path: Path


class DaemonService:
    """
    The daemon's method surface.

    This class is intentionally isolated so we can unit-test request dispatch by
    injecting a fake service implementation.
    """

    def __init__(self, *, started_at: str, socket_path: Path):
        self.started_at = started_at
        self.socket_path = socket_path

        # Lazy import so the daemon can at least start and print helpful errors.
        from src.messages_interface import MessagesInterface  # type: ignore

        self._mi = MessagesInterface()

        # v1: keep MessagesInterface as-is. We will refactor to persistent SQLite
        # connections/caches once the daemon plumbing is proven.

    def health(self) -> dict[str, Any]:
        can_read_db = True
        try:
            # Lightweight read that exercises chat.db access.
            _ = self._mi.get_unread_count()
        except Exception:
            can_read_db = False

        return {
            "pid": os.getpid(),
            "started_at": self.started_at,
            "version": "v1",
            "socket": str(self.socket_path),
            "chat_db": str(getattr(self._mi, "messages_db_path", "")),
            "can_read_db": can_read_db,
        }

    def unread_count(self) -> dict[str, Any]:
        return {"count": self._mi.get_unread_count()}

    def unread_messages(self, *, limit: int = 20) -> dict[str, Any]:
        return {"messages": self._mi.get_unread_messages(limit=limit)}

    def recent(self, *, limit: int = 10) -> dict[str, Any]:
        return {"messages": self._mi.get_all_recent_conversations(limit=limit)}

    def text_search(
        self,
        *,
        query: str,
        limit: int = 20,
        since: Optional[str] = None,
    ) -> dict[str, Any]:
        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since)
        return {"results": self._mi.search_messages(query=query, limit=limit, since=since_dt)}

    def messages_by_phone(self, *, phone: str, limit: int = 20) -> dict[str, Any]:
        return {"messages": self._mi.get_messages_by_phone(phone, limit=limit)}

    def bundle(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Server-side bundle wrapper.

        v1 delegates to MessagesInterface methods and does not yet apply output shaping.
        Output shaping will be moved server-side once we integrate the gateway output helpers.
        """
        include_raw = (params.get("include") or "").strip() or None
        include = None
        if include_raw:
            include = {s.strip() for s in include_raw.split(",") if s.strip()}
            include.add("meta")

        unread_limit = int(params.get("unread_limit") or 20)
        recent_limit = int(params.get("recent_limit") or 10)
        search_limit = int(params.get("search_limit") or 20)
        messages_limit = int(params.get("messages_limit") or 20)
        query = params.get("query")
        phone = params.get("phone")

        payload: dict[str, Any] = {
            "meta": {
                "generated_at": _now_iso(),
                "query": query,
                "limits": {
                    "unread_limit": unread_limit,
                    "recent_limit": recent_limit,
                    "search_limit": search_limit,
                    "messages_limit": messages_limit,
                },
            }
        }

        if include is None or "unread_count" in include or "unread_messages" in include:
            payload["unread"] = {}
            if include is None or "unread_count" in include:
                payload["unread"]["count"] = self._mi.get_unread_count()
            if include is None or "unread_messages" in include:
                payload["unread"]["messages"] = self._mi.get_unread_messages(limit=unread_limit)

        if include is None or "recent" in include:
            payload["recent"] = self._mi.get_all_recent_conversations(limit=recent_limit)

        if query and (include is None or "search" in include):
            payload["search"] = {"results": self._mi.search_messages(query=str(query), limit=search_limit)}

        if phone and messages_limit and (include is None or "contact_messages" in include):
            payload["contact_messages"] = {"messages": self._mi.get_messages_by_phone(str(phone), limit=messages_limit)}

        return payload


class RequestHandler(socketserver.StreamRequestHandler):
    """NDJSON request handler for the daemon."""

    server: "DaemonServer"

    def handle(self) -> None:
        raw = self.rfile.readline()
        if not raw:
            return

        started = time.perf_counter()
        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            resp = {
                "id": None,
                "ok": False,
                "result": None,
                "error": {"code": "INVALID_JSON", "message": str(exc), "details": None},
                "meta": {"server_ms": (time.perf_counter() - started) * 1000, "protocol_v": 1},
            }
            self.wfile.write(_json_line(resp))
            return

        resp = self.server.dispatch(req, started_at=started)
        self.wfile.write(_json_line(resp))


class DaemonServer(socketserver.UnixStreamServer):
    """Unix stream server with a simple dispatcher."""

    def __init__(self, socket_path: Path, service: DaemonService):
        self.socket_path = socket_path
        self.service = service
        super().__init__(str(socket_path), RequestHandler)

    def dispatch(self, req: dict[str, Any], *, started_at: float) -> dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        v = req.get("v", 1)

        try:
            if not isinstance(method, str) or not method:
                raise ValueError("missing method")
            if not isinstance(params, dict):
                raise ValueError("params must be an object")

            if method == "health":
                result = self.service.health()
            elif method == "unread_count":
                result = self.service.unread_count()
            elif method == "unread_messages":
                controls = _extract_controls(params)
                msgs = self.service.unread_messages(limit=int(params.get("limit") or 20)).get("messages") or []
                shaped = apply_output_controls(
                    msgs,
                    fields=controls["fields"],
                    max_text_chars=controls["max_text_chars"],
                    compact=controls["compact"],
                    minimal=controls["minimal"],
                    default_fields=["date", "phone", "text", "days_old", "group_id", "group_name"],
                )
                result = {"messages": shaped}
            elif method == "recent":
                controls = _extract_controls(params)
                msgs = self.service.recent(limit=int(params.get("limit") or 10)).get("messages") or []
                shaped = apply_output_controls(
                    msgs,
                    fields=controls["fields"],
                    max_text_chars=controls["max_text_chars"],
                    compact=controls["compact"],
                    minimal=controls["minimal"],
                    default_fields=["date", "is_from_me", "phone", "text", "group_id"],
                )
                result = {"messages": shaped}
            elif method == "text_search":
                q = params.get("query")
                if not isinstance(q, str) or not q:
                    raise ValueError("query is required")
                controls = _extract_controls(params)
                results = self.service.text_search(
                    query=q,
                    limit=int(params.get("limit") or 20),
                    since=params.get("since"),
                ).get("results") or []
                shaped = apply_output_controls(
                    results,
                    fields=controls["fields"],
                    max_text_chars=controls["max_text_chars"],
                    compact=controls["compact"],
                    minimal=controls["minimal"],
                    default_fields=["date", "is_from_me", "phone", "text", "match_snippet", "group_id"],
                )
                result = {"results": shaped}
            elif method == "messages_by_phone":
                phone = params.get("phone")
                if not isinstance(phone, str) or not phone:
                    raise ValueError("phone is required")
                controls = _extract_controls(params)
                msgs = self.service.messages_by_phone(phone=phone, limit=int(params.get("limit") or 20)).get("messages") or []
                shaped = apply_output_controls(
                    msgs,
                    fields=controls["fields"],
                    max_text_chars=controls["max_text_chars"],
                    compact=controls["compact"],
                    minimal=controls["minimal"],
                    default_fields=["date", "is_from_me", "text", "group_id"],
                )
                result = {"messages": shaped}
            elif method == "bundle":
                controls = _extract_controls(params)
                bundle = self.service.bundle(params)
                # Shape common sections if present. Keep meta intact by default.
                if isinstance(bundle, dict):
                    unread = bundle.get("unread")
                    if isinstance(unread, dict) and isinstance(unread.get("messages"), list):
                        unread["messages"] = apply_output_controls(
                            unread["messages"],
                            fields=controls["fields"],
                            max_text_chars=controls["max_text_chars"],
                            compact=controls["compact"],
                            minimal=controls["minimal"],
                            default_fields=["date", "phone", "text", "days_old", "group_id", "group_name"],
                        )
                    if isinstance(bundle.get("recent"), list):
                        bundle["recent"] = apply_output_controls(
                            bundle["recent"],
                            fields=controls["fields"],
                            max_text_chars=controls["max_text_chars"],
                            compact=controls["compact"],
                            minimal=controls["minimal"],
                            default_fields=["date", "is_from_me", "phone", "text", "group_id"],
                        )
                    search = bundle.get("search")
                    if isinstance(search, dict) and isinstance(search.get("results"), list):
                        search["results"] = apply_output_controls(
                            search["results"],
                            fields=controls["fields"],
                            max_text_chars=controls["max_text_chars"],
                            compact=controls["compact"],
                            minimal=controls["minimal"],
                            default_fields=["date", "is_from_me", "phone", "text", "match_snippet", "group_id"],
                        )
                    cm = bundle.get("contact_messages")
                    if isinstance(cm, dict) and isinstance(cm.get("messages"), list):
                        cm["messages"] = apply_output_controls(
                            cm["messages"],
                            fields=controls["fields"],
                            max_text_chars=controls["max_text_chars"],
                            compact=controls["compact"],
                            minimal=controls["minimal"],
                            default_fields=["date", "is_from_me", "text", "group_id"],
                        )
                result = bundle
            else:
                return {
                    "id": req_id,
                    "ok": False,
                    "result": None,
                    "error": {"code": "UNKNOWN_METHOD", "message": method, "details": None},
                    "meta": {"server_ms": (time.perf_counter() - started_at) * 1000, "protocol_v": v},
                }

            return {
                "id": req_id,
                "ok": True,
                "result": result,
                "error": None,
                "meta": {"server_ms": (time.perf_counter() - started_at) * 1000, "protocol_v": v},
            }
        except Exception as exc:
            return {
                "id": req_id,
                "ok": False,
                "result": None,
                "error": {"code": "ERROR", "message": str(exc), "details": None},
                "meta": {"server_ms": (time.perf_counter() - started_at) * 1000, "protocol_v": v},
            }


def _ensure_state_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def cmd_start(args: argparse.Namespace) -> int:
    cfg = DaemonConfig(socket_path=Path(args.socket), pid_path=Path(args.pidfile))
    _ensure_state_dir(cfg.socket_path)
    _ensure_state_dir(cfg.pid_path)

    if cfg.socket_path.exists() and _is_socket_listening(cfg.socket_path):
        print(f"Daemon already running at {cfg.socket_path}", file=sys.stderr)
        return 1
    if cfg.socket_path.exists():
        try:
            cfg.socket_path.unlink()
        except Exception:
            pass

    def _handle_sig(_signum: int, _frame) -> None:
        try:
            server.server_close()
        finally:
            raise SystemExit(0)

    if args.foreground:
        started_at = _now_iso()
        service = DaemonService(started_at=started_at, socket_path=cfg.socket_path)
        server = DaemonServer(cfg.socket_path, service)
        os.chmod(cfg.socket_path, 0o600)
        cfg.pid_path.write_text(str(os.getpid()))

        signal.signal(signal.SIGTERM, _handle_sig)
        signal.signal(signal.SIGINT, _handle_sig)

        print(f"[daemon] started pid={os.getpid()} socket={cfg.socket_path}", file=sys.stderr)
        server.serve_forever()
        return 0

    # Minimal detach: use a child process to own the server.
    pid = os.fork()
    if pid > 0:
        cfg.pid_path.write_text(str(pid))
        print(f"Started daemon pid={pid} socket={cfg.socket_path}")
        return 0

    os.setsid()
    # Detach from parent stdio. If the parent was started with capture_output,
    # inherited pipes would keep communicate() from seeing EOF and can hang.
    try:
        with open(os.devnull, "rb", buffering=0) as devnull_in, open(os.devnull, "ab", buffering=0) as devnull_out:
            os.dup2(devnull_in.fileno(), 0)
            os.dup2(devnull_out.fileno(), 1)
            os.dup2(devnull_out.fileno(), 2)
    except Exception:
        pass

    started_at = _now_iso()
    service = DaemonService(started_at=started_at, socket_path=cfg.socket_path)
    server = DaemonServer(cfg.socket_path, service)
    os.chmod(cfg.socket_path, 0o600)

    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)

    server.serve_forever()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    socket_path = Path(args.socket)
    pid_path = Path(args.pidfile)
    pid = _read_text(pid_path)
    running = socket_path.exists() and _is_socket_listening(socket_path)
    if running:
        print(f"running pid={pid or 'unknown'} socket={socket_path}")
        return 0
    print(f"not running (socket={socket_path})")
    return 1


def cmd_stop(args: argparse.Namespace) -> int:
    socket_path = Path(args.socket)
    pid_path = Path(args.pidfile)
    pid_s = _read_text(pid_path)
    if not pid_s:
        if socket_path.exists():
            print("pidfile missing; removing stale socket", file=sys.stderr)
            try:
                socket_path.unlink()
            except Exception:
                pass
        print("not running")
        return 1

    try:
        pid = int(pid_s)
    except ValueError:
        print("invalid pidfile", file=sys.stderr)
        return 2

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print("process not found; cleaning stale files", file=sys.stderr)
    except Exception as exc:
        print(f"failed to signal daemon: {exc}", file=sys.stderr)
        return 2

    try:
        pid_path.unlink()
    except Exception:
        pass
    try:
        if socket_path.exists():
            socket_path.unlink()
    except Exception:
        pass
    print("stopped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Wolfies iMessage daemon (Python)")
    parser.add_argument("--socket", default=str(DEFAULT_SOCKET_PATH), help="UNIX socket path")
    parser.add_argument("--pidfile", default=str(DEFAULT_PID_PATH), help="pidfile path")

    sub = parser.add_subparsers(dest="cmd", required=True)
    p_start = sub.add_parser("start", help="Start daemon")
    p_start.add_argument("--foreground", action="store_true", help="Run in foreground (recommended while developing)")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="Check daemon status")
    p_status.set_defaults(func=cmd_status)

    p_stop = sub.add_parser("stop", help="Stop daemon")
    p_stop.set_defaults(func=cmd_stop)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

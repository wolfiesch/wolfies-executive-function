#!/usr/bin/env python3
"""
Google API daemon (Python) - warm, low-latency access to Gmail and Calendar.

This daemon keeps expensive resources hot (OAuth tokens, API services, caches)
and serves requests over a UNIX domain socket using NDJSON framing.

Combines Gmail and Calendar into a single daemon since they share OAuth credentials,
eliminating redundant token refreshes and API discovery calls.

CHANGELOG (recent first, max 5 entries):
01/08/2026 - Initial daemon implementation following iMessage pattern (Claude)
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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, List, Dict


SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_STATE_DIR = Path.home() / ".wolfies-google"
DEFAULT_SOCKET_PATH = DEFAULT_STATE_DIR / "daemon.sock"
DEFAULT_PID_PATH = DEFAULT_STATE_DIR / "daemon.pid"
DEFAULT_CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"


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
    """Check if a socket is listening (fast detection for prewarm)."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect(str(socket_path))
        return True
    except Exception:
        return False


def _coerce_limit(value: Any, *, default: int, min_value: int = 1, max_value: int = 500) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = default
    return max(min_value, min(max_value, num))


@dataclass
class DaemonConfig:
    """Daemon configuration."""
    socket_path: Path
    pid_path: Path
    credentials_dir: Path


class GoogleDaemonService:
    """
    The daemon's method surface for Gmail and Calendar APIs.

    Keeps Gmail and Calendar clients warm with shared OAuth credentials.
    """

    def __init__(self, *, started_at: str, socket_path: Path, credentials_dir: Path):
        self.started_at = started_at
        self.socket_path = socket_path
        self.credentials_dir = credentials_dir

        # Lazy imports to allow daemon to start and show errors
        self._gmail_client = None
        self._calendar_client = None
        self._init_error = None

        # Initialize clients
        try:
            self._init_clients()
        except Exception as e:
            self._init_error = str(e)
            print(f"[daemon] Warning: Failed to initialize clients: {e}", file=sys.stderr)

    def _init_clients(self) -> None:
        """Initialize Gmail and Calendar clients with shared OAuth."""
        from src.integrations.gmail.gmail_client import GmailClient
        from src.integrations.google_calendar.calendar_client import GoogleCalendarClient

        # Initialize Gmail client (handles its own OAuth)
        self._gmail_client = GmailClient(str(self.credentials_dir))

        # Initialize Calendar client (separate OAuth flow but same credentials dir)
        self._calendar_client = GoogleCalendarClient(str(self.credentials_dir))
        self._calendar_client.authenticate()

    def health(self) -> Dict[str, Any]:
        """Health check with status of both services."""
        gmail_ok = False
        calendar_ok = False

        if self._gmail_client:
            try:
                self._gmail_client.get_unread_count()
                gmail_ok = True
            except Exception:
                pass

        if self._calendar_client and self._calendar_client.service:
            try:
                self._calendar_client.list_events(max_results=1)
                calendar_ok = True
            except Exception:
                pass

        return {
            "pid": os.getpid(),
            "started_at": self.started_at,
            "version": "v1",
            "socket": str(self.socket_path),
            "credentials_dir": str(self.credentials_dir),
            "gmail_ok": gmail_ok,
            "calendar_ok": calendar_ok,
            "init_error": self._init_error,
        }

    # =========================================================================
    # GMAIL METHODS
    # =========================================================================

    def gmail_unread_count(self) -> Dict[str, Any]:
        """Get unread email count."""
        if not self._gmail_client:
            raise RuntimeError("Gmail client not initialized")
        count = self._gmail_client.get_unread_count()
        return {"unread_count": count}

    def gmail_list(
        self,
        *,
        count: int = 10,
        unread_only: bool = False,
        label: Optional[str] = None,
        sender: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List emails with optional filters."""
        if not self._gmail_client:
            raise RuntimeError("Gmail client not initialized")

        emails = self._gmail_client.list_emails(
            max_results=count,
            unread_only=unread_only,
            label=label,
            sender=sender,
            after_date=after,
            before_date=before,
        )
        return {"emails": emails, "count": len(emails)}

    def gmail_search(self, *, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search emails by query."""
        if not self._gmail_client:
            raise RuntimeError("Gmail client not initialized")

        emails = self._gmail_client.search_emails(query=query, max_results=max_results)
        return {"query": query, "emails": emails, "count": len(emails)}

    def gmail_get(self, *, message_id: str) -> Dict[str, Any]:
        """Get full email by ID."""
        if not self._gmail_client:
            raise RuntimeError("Gmail client not initialized")

        email = self._gmail_client.get_email(message_id)
        if not email:
            raise ValueError(f"Email not found: {message_id}")
        return email

    def gmail_send(self, *, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email."""
        if not self._gmail_client:
            raise RuntimeError("Gmail client not initialized")

        result = self._gmail_client.send_email(to=to, subject=subject, body=body)
        return result

    def gmail_mark_read(self, *, message_id: str) -> Dict[str, Any]:
        """Mark email as read."""
        if not self._gmail_client:
            raise RuntimeError("Gmail client not initialized")

        success = self._gmail_client.mark_as_read(message_id)
        return {"success": success, "message_id": message_id}

    # =========================================================================
    # CALENDAR METHODS
    # =========================================================================

    def calendar_today(self) -> Dict[str, Any]:
        """Get today's events."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        now = datetime.now(timezone.utc)
        end_of_day = now.replace(hour=23, minute=59, second=59)

        events = self._calendar_client.list_events(
            time_min=now,
            time_max=end_of_day,
            max_results=50,
        )
        return {"events": events, "count": len(events), "date": now.strftime("%Y-%m-%d")}

    def calendar_week(self) -> Dict[str, Any]:
        """Get this week's events."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        now = datetime.now(timezone.utc)
        end_of_week = now + timedelta(days=7)

        events = self._calendar_client.list_events(
            time_min=now,
            time_max=end_of_week,
            max_results=100,
        )
        return {
            "events": events,
            "count": len(events),
            "start": now.strftime("%Y-%m-%d"),
            "end": end_of_week.strftime("%Y-%m-%d"),
        }

    def calendar_events(
        self,
        *,
        count: int = 10,
        days: int = 7,
    ) -> Dict[str, Any]:
        """List upcoming events."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        now = datetime.now(timezone.utc)
        end_time = now + timedelta(days=days)

        events = self._calendar_client.list_events(
            time_min=now,
            time_max=end_time,
            max_results=count,
        )
        return {"events": events, "count": len(events)}

    def calendar_get(self, *, event_id: str) -> Dict[str, Any]:
        """Get event by ID."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        event = self._calendar_client.get_event(event_id)
        if not event:
            raise ValueError(f"Event not found: {event_id}")
        return event

    def calendar_free(
        self,
        *,
        duration: int = 60,
        days: int = 7,
        limit: int = 10,
        work_start: int = 9,
        work_end: int = 17,
    ) -> Dict[str, Any]:
        """Find free time slots."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        now = datetime.now(timezone.utc)
        end_time = now + timedelta(days=days)

        slots = self._calendar_client.find_free_time(
            duration_minutes=duration,
            time_min=now,
            time_max=end_time,
            working_hours_start=work_start,
            working_hours_end=work_end,
        )

        # Limit results
        slots = slots[:limit]

        return {"free_slots": slots, "count": len(slots), "duration_minutes": duration}

    def calendar_create(
        self,
        *,
        title: str,
        start: str,
        end: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        from dateutil import parser as date_parser

        start_dt = date_parser.parse(start)
        end_dt = date_parser.parse(end)

        event = self._calendar_client.create_event(
            summary=title,
            start_time=start_dt,
            end_time=end_dt,
            description=description,
            location=location,
            attendees=attendees,
        )

        if not event:
            raise RuntimeError("Failed to create event")
        return {"success": True, "event": event}

    def calendar_delete(self, *, event_id: str) -> Dict[str, Any]:
        """Delete a calendar event."""
        if not self._calendar_client or not self._calendar_client.service:
            raise RuntimeError("Calendar client not initialized")

        success = self._calendar_client.delete_event(event_id)
        return {"success": success, "event_id": event_id}


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

    def __init__(self, socket_path: Path, service: GoogleDaemonService):
        self.socket_path = socket_path
        self.service = service
        super().__init__(str(socket_path), RequestHandler)

    def dispatch(self, req: Dict[str, Any], *, started_at: float) -> Dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        v = req.get("v", 1)

        try:
            if not isinstance(method, str) or not method:
                raise ValueError("missing method")
            if not isinstance(params, dict):
                raise ValueError("params must be an object")

            # Route to appropriate method
            if method == "health":
                result = self.service.health()

            # Gmail methods
            elif method == "gmail.unread_count":
                result = self.service.gmail_unread_count()
            elif method == "gmail.list":
                result = self.service.gmail_list(
                    count=_coerce_limit(params.get("count"), default=10),
                    unread_only=bool(params.get("unread_only", False)),
                    label=params.get("label"),
                    sender=params.get("sender"),
                    after=params.get("after"),
                    before=params.get("before"),
                )
            elif method == "gmail.search":
                q = params.get("query")
                if not isinstance(q, str) or not q:
                    raise ValueError("query is required")
                result = self.service.gmail_search(
                    query=q,
                    max_results=_coerce_limit(params.get("max_results"), default=10),
                )
            elif method == "gmail.get":
                msg_id = params.get("message_id")
                if not isinstance(msg_id, str) or not msg_id:
                    raise ValueError("message_id is required")
                result = self.service.gmail_get(message_id=msg_id)
            elif method == "gmail.send":
                to = params.get("to")
                subject = params.get("subject")
                body = params.get("body")
                if not all([to, subject, body]):
                    raise ValueError("to, subject, and body are required")
                result = self.service.gmail_send(to=to, subject=subject, body=body)
            elif method == "gmail.mark_read":
                msg_id = params.get("message_id")
                if not isinstance(msg_id, str) or not msg_id:
                    raise ValueError("message_id is required")
                result = self.service.gmail_mark_read(message_id=msg_id)

            # Calendar methods
            elif method == "calendar.today":
                result = self.service.calendar_today()
            elif method == "calendar.week":
                result = self.service.calendar_week()
            elif method == "calendar.events":
                result = self.service.calendar_events(
                    count=_coerce_limit(params.get("count"), default=10),
                    days=_coerce_limit(params.get("days"), default=7, max_value=365),
                )
            elif method == "calendar.get":
                event_id = params.get("event_id")
                if not isinstance(event_id, str) or not event_id:
                    raise ValueError("event_id is required")
                result = self.service.calendar_get(event_id=event_id)
            elif method == "calendar.free":
                result = self.service.calendar_free(
                    duration=_coerce_limit(params.get("duration"), default=60, max_value=480),
                    days=_coerce_limit(params.get("days"), default=7, max_value=30),
                    limit=_coerce_limit(params.get("limit"), default=10, max_value=50),
                    work_start=_coerce_limit(params.get("work_start"), default=9, min_value=0, max_value=23),
                    work_end=_coerce_limit(params.get("work_end"), default=17, min_value=1, max_value=24),
                )
            elif method == "calendar.create":
                title = params.get("title")
                start = params.get("start")
                end = params.get("end")
                if not all([title, start, end]):
                    raise ValueError("title, start, and end are required")
                result = self.service.calendar_create(
                    title=title,
                    start=start,
                    end=end,
                    description=params.get("description"),
                    location=params.get("location"),
                    attendees=params.get("attendees"),
                )
            elif method == "calendar.delete":
                event_id = params.get("event_id")
                if not isinstance(event_id, str) or not event_id:
                    raise ValueError("event_id is required")
                result = self.service.calendar_delete(event_id=event_id)

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
    cfg = DaemonConfig(
        socket_path=Path(args.socket),
        pid_path=Path(args.pidfile),
        credentials_dir=Path(args.credentials_dir),
    )
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

    if args.foreground:
        started_at = _now_iso()
        service = GoogleDaemonService(
            started_at=started_at,
            socket_path=cfg.socket_path,
            credentials_dir=cfg.credentials_dir,
        )
        server = DaemonServer(cfg.socket_path, service)
        os.chmod(cfg.socket_path, 0o600)
        cfg.pid_path.write_text(str(os.getpid()))

        def _handle_sig(_signum: int, _frame) -> None:
            try:
                server.server_close()
            finally:
                raise SystemExit(0)

        signal.signal(signal.SIGTERM, _handle_sig)
        signal.signal(signal.SIGINT, _handle_sig)

        print(f"[daemon] started pid={os.getpid()} socket={cfg.socket_path}", file=sys.stderr)
        server.serve_forever()
        return 0

    # Background mode: fork
    if os.name != "posix":
        print("Background mode only supported on Unix. Use --foreground.", file=sys.stderr)
        return 1

    pid = os.fork()
    if pid > 0:
        cfg.pid_path.write_text(str(pid))
        print(f"Started daemon pid={pid} socket={cfg.socket_path}")
        return 0

    os.setsid()
    try:
        with open(os.devnull, "rb", buffering=0) as devnull_in, \
             open(os.devnull, "ab", buffering=0) as devnull_out:
            os.dup2(devnull_in.fileno(), 0)
            os.dup2(devnull_out.fileno(), 1)
            os.dup2(devnull_out.fileno(), 2)
    except Exception:
        pass

    started_at = _now_iso()
    service = GoogleDaemonService(
        started_at=started_at,
        socket_path=cfg.socket_path,
        credentials_dir=cfg.credentials_dir,
    )
    server = DaemonServer(cfg.socket_path, service)
    os.chmod(cfg.socket_path, 0o600)

    def _handle_sig(_signum: int, _frame) -> None:
        try:
            server.server_close()
        finally:
            raise SystemExit(0)

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
    parser = argparse.ArgumentParser(description="Wolfies Google API daemon (Gmail + Calendar)")
    parser.add_argument("--socket", default=str(DEFAULT_SOCKET_PATH), help="UNIX socket path")
    parser.add_argument("--pidfile", default=str(DEFAULT_PID_PATH), help="pidfile path")
    parser.add_argument(
        "--credentials-dir",
        default=str(DEFAULT_CREDENTIALS_DIR),
        help="Path to Google OAuth credentials directory",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="Start daemon")
    p_start.add_argument("--foreground", action="store_true", help="Run in foreground")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="Check daemon status")
    p_status.set_defaults(func=cmd_status)

    p_stop = sub.add_parser("stop", help="Stop daemon")
    p_stop.set_defaults(func=cmd_stop)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

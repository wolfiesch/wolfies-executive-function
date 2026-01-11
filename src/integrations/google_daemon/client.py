#!/usr/bin/env python3
"""
Google daemon thin client - low-latency access to warm Gmail/Calendar daemon.

This client communicates with the Google daemon over Unix socket using NDJSON.
Falls back to direct API access if daemon is not running.

CHANGELOG (recent first, max 5 entries):
01/08/2026 - Initial client implementation following iMessage pattern (Claude)
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_SOCKET_PATH = Path.home() / ".wolfies-google" / "daemon.sock"
DEFAULT_PID_PATH = Path.home() / ".wolfies-google" / "daemon.pid"
DEFAULT_TIMEOUT = 30.0  # seconds


class DaemonConnectionError(Exception):
    """Raised when unable to connect to daemon."""
    pass


class DaemonRequestError(Exception):
    """Raised when daemon returns an error response."""
    def __init__(self, code: str, message: str, details: Any = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"{code}: {message}")


def is_daemon_running(
    socket_path: Path = DEFAULT_SOCKET_PATH,
    pid_path: Path = DEFAULT_PID_PATH,
    timeout_s: float = 0.005,
) -> bool:
    """
    Fast check if daemon is running (<10ms target).

    Algorithm:
    1. Socket exists? (<1ms)
    2. PID file valid and process alive? (<0.1ms)
    3. Socket listening? (5ms timeout)
    """
    # Level 1: Socket exists?
    if not socket_path.exists():
        return False

    # Level 2: PID alive?
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, 0)  # Signal 0 = check if alive
        except (ValueError, ProcessLookupError, PermissionError):
            return False  # Stale PID file
        except Exception:
            pass  # Continue to socket check

    # Level 3: Socket listening?
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect(str(socket_path))
        return True
    except Exception:
        return False


def call_daemon(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    socket_path: Path = DEFAULT_SOCKET_PATH,
    timeout: float = DEFAULT_TIMEOUT,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call a daemon method and return the result.

    Args:
        method: Method name (e.g., "gmail.list", "calendar.today")
        params: Method parameters
        socket_path: Path to daemon socket
        timeout: Request timeout in seconds
        request_id: Optional request ID for correlation

    Returns:
        Result dictionary from daemon

    Raises:
        DaemonConnectionError: If unable to connect to daemon
        DaemonRequestError: If daemon returns an error response
    """
    if params is None:
        params = {}

    request = {
        "id": request_id or f"req_{int(time.time() * 1000)}",
        "method": method,
        "params": params,
        "v": 1,
    }

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(str(socket_path))

            # Send request as NDJSON
            request_line = json.dumps(request, separators=(",", ":")) + "\n"
            s.sendall(request_line.encode("utf-8"))

            # Read response
            response_data = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in response_data:
                    break

            if not response_data:
                raise DaemonConnectionError("Empty response from daemon")

            response = json.loads(response_data.decode("utf-8").strip())

    except socket.timeout:
        raise DaemonConnectionError(f"Request timeout after {timeout}s")
    except FileNotFoundError:
        raise DaemonConnectionError(f"Daemon socket not found: {socket_path}")
    except ConnectionRefusedError:
        raise DaemonConnectionError(f"Connection refused: {socket_path}")
    except json.JSONDecodeError as e:
        raise DaemonConnectionError(f"Invalid JSON response: {e}")
    except Exception as e:
        raise DaemonConnectionError(f"Connection error: {e}")

    # Check for errors
    if not response.get("ok"):
        error = response.get("error", {})
        raise DaemonRequestError(
            code=error.get("code", "UNKNOWN"),
            message=error.get("message", "Unknown error"),
            details=error.get("details"),
        )

    return response.get("result", {})


class GoogleDaemonClient:
    """
    High-level client for the Google daemon.

    Provides typed methods for Gmail and Calendar operations.
    """

    def __init__(
        self,
        socket_path: Path = DEFAULT_SOCKET_PATH,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.socket_path = socket_path
        self.timeout = timeout

    def _call(self, method: str, **params) -> Dict[str, Any]:
        """Call daemon method with parameters."""
        # Filter out None values
        filtered_params = {k: v for k, v in params.items() if v is not None}
        return call_daemon(
            method,
            filtered_params,
            socket_path=self.socket_path,
            timeout=self.timeout,
        )

    # =========================================================================
    # HEALTH
    # =========================================================================

    def health(self) -> Dict[str, Any]:
        """Check daemon health and service status."""
        return self._call("health")

    # =========================================================================
    # GMAIL METHODS
    # =========================================================================

    def gmail_unread_count(self) -> int:
        """Get unread email count."""
        result = self._call("gmail.unread_count")
        return result.get("unread_count", 0)

    def gmail_list(
        self,
        count: int = 10,
        unread_only: bool = False,
        label: Optional[str] = None,
        sender: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List emails with optional filters."""
        return self._call(
            "gmail.list",
            count=count,
            unread_only=unread_only,
            label=label,
            sender=sender,
            after=after,
            before=before,
        )

    def gmail_search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search emails by query."""
        return self._call("gmail.search", query=query, max_results=max_results)

    def gmail_get(self, message_id: str) -> Dict[str, Any]:
        """Get full email by ID."""
        return self._call("gmail.get", message_id=message_id)

    def gmail_send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email."""
        return self._call("gmail.send", to=to, subject=subject, body=body)

    def gmail_mark_read(self, message_id: str) -> Dict[str, Any]:
        """Mark email as read."""
        return self._call("gmail.mark_read", message_id=message_id)

    # =========================================================================
    # CALENDAR METHODS
    # =========================================================================

    def calendar_today(self) -> Dict[str, Any]:
        """Get today's events."""
        return self._call("calendar.today")

    def calendar_week(self) -> Dict[str, Any]:
        """Get this week's events."""
        return self._call("calendar.week")

    def calendar_events(self, count: int = 10, days: int = 7) -> Dict[str, Any]:
        """List upcoming events."""
        return self._call("calendar.events", count=count, days=days)

    def calendar_get(self, event_id: str) -> Dict[str, Any]:
        """Get event by ID."""
        return self._call("calendar.get", event_id=event_id)

    def calendar_free(
        self,
        duration: int = 60,
        days: int = 7,
        limit: int = 10,
        work_start: int = 9,
        work_end: int = 17,
    ) -> Dict[str, Any]:
        """Find free time slots."""
        return self._call(
            "calendar.free",
            duration=duration,
            days=days,
            limit=limit,
            work_start=work_start,
            work_end=work_end,
        )

    def calendar_create(
        self,
        title: str,
        start: str,
        end: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        return self._call(
            "calendar.create",
            title=title,
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendees,
        )

    def calendar_delete(self, event_id: str) -> Dict[str, Any]:
        """Delete a calendar event."""
        return self._call("calendar.delete", event_id=event_id)


# Convenience functions for direct use
def gmail_unread_count() -> int:
    """Quick access to unread count via daemon."""
    return GoogleDaemonClient().gmail_unread_count()


def gmail_list(count: int = 10, **kwargs) -> Dict[str, Any]:
    """Quick access to email list via daemon."""
    return GoogleDaemonClient().gmail_list(count=count, **kwargs)


def calendar_today() -> Dict[str, Any]:
    """Quick access to today's events via daemon."""
    return GoogleDaemonClient().calendar_today()


def calendar_week() -> Dict[str, Any]:
    """Quick access to this week's events via daemon."""
    return GoogleDaemonClient().calendar_week()

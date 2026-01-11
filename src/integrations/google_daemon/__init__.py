"""
Google API Daemon - Shared daemon for Gmail and Calendar APIs.

Provides warm, low-latency access to Google services by keeping OAuth tokens
and API services initialized.

Usage:
    # Start daemon
    python -m src.integrations.google_daemon.server start

    # Use client
    from src.integrations.google_daemon.client import GoogleDaemonClient, is_daemon_running

    if is_daemon_running():
        client = GoogleDaemonClient()
        emails = client.gmail_list(count=10)
        events = client.calendar_today()
"""

from .client import (
    GoogleDaemonClient,
    is_daemon_running,
    call_daemon,
    DaemonConnectionError,
    DaemonRequestError,
)

__all__ = [
    "GoogleDaemonClient",
    "is_daemon_running",
    "call_daemon",
    "DaemonConnectionError",
    "DaemonRequestError",
]

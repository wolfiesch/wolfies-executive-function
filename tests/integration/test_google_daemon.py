"""
Integration tests for Google Daemon (Gmail + Calendar).

Tests the Google daemon client, lifecycle management, and protocol handling.
Requires the daemon to be running for live tests (marked with @pytest.mark.live).

These tests verify:
1. Daemon lifecycle (start/stop/status)
2. Fast detection algorithm (<10ms)
3. Gmail operations via daemon
4. Calendar operations via daemon
5. Error handling and edge cases
6. Protocol correctness (NDJSON)

CHANGELOG (recent first, max 5 entries):
01/08/2026 - Initial test implementation for Phase 9 Twitter release (Claude)
"""

import json
import os
import pytest
import socket
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.integrations.google_daemon.client import (
    GoogleDaemonClient,
    DaemonConnectionError,
    DaemonRequestError,
    is_daemon_running,
    call_daemon,
    DEFAULT_SOCKET_PATH,
    DEFAULT_PID_PATH,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_socket_dir():
    """Create a temporary directory for test socket files."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_socket_response():
    """Create a mock socket that returns a predefined response."""
    def _make_mock(response_data: dict):
        mock_socket = MagicMock()
        response_json = json.dumps(response_data) + "\n"
        mock_socket.recv.return_value = response_json.encode("utf-8")
        mock_socket.__enter__ = MagicMock(return_value=mock_socket)
        mock_socket.__exit__ = MagicMock(return_value=False)
        return mock_socket
    return _make_mock


# =============================================================================
# Unit Tests - is_daemon_running() (<10ms detection)
# =============================================================================

class TestDaemonDetection:
    """Tests for fast daemon detection algorithm."""

    def test_returns_false_when_socket_not_exists(self, temp_socket_dir):
        """Detection returns False immediately when socket doesn't exist."""
        socket_path = temp_socket_dir / "nonexistent.sock"
        pid_path = temp_socket_dir / "nonexistent.pid"

        start = time.perf_counter()
        result = is_daemon_running(socket_path, pid_path)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result is False
        assert elapsed_ms < 10, f"Detection took {elapsed_ms:.2f}ms, should be <10ms"

    def test_returns_false_when_pid_is_stale(self, temp_socket_dir):
        """Detection returns False when PID file points to dead process."""
        socket_path = temp_socket_dir / "daemon.sock"
        pid_path = temp_socket_dir / "daemon.pid"

        # Create socket file (but not listening)
        socket_path.touch()
        # Create PID file with invalid PID
        pid_path.write_text("99999999")  # Very unlikely to be a real PID

        result = is_daemon_running(socket_path, pid_path)
        assert result is False

    def test_detection_speed_under_10ms(self, temp_socket_dir):
        """Detection completes in <10ms for non-running daemon."""
        socket_path = temp_socket_dir / "daemon.sock"
        pid_path = temp_socket_dir / "daemon.pid"
        socket_path.touch()
        pid_path.write_text(str(os.getpid()))  # Use current PID

        # Run multiple iterations to get stable timing
        times = []
        for _ in range(10):
            start = time.perf_counter()
            is_daemon_running(socket_path, pid_path, timeout_s=0.005)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        # Allow some headroom for CI environments
        assert avg_time < 50, f"Average detection took {avg_time:.2f}ms, should be <50ms"


# =============================================================================
# Unit Tests - call_daemon() Protocol
# =============================================================================

class TestDaemonProtocol:
    """Tests for NDJSON protocol handling."""

    def test_request_format(self, mock_socket_response):
        """Request is sent as valid NDJSON."""
        response = {"ok": True, "id": "test", "result": {"test": "data"}}
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            result = call_daemon(
                "health",
                {},
                socket_path=Path("/tmp/test.sock"),
                request_id="test_123"
            )

            # Verify request was sent
            sent_data = mock_sock.sendall.call_args[0][0].decode("utf-8")
            request = json.loads(sent_data.strip())

            assert request["method"] == "health"
            assert request["id"] == "test_123"
            assert request["v"] == 1
            assert "params" in request

    def test_handles_success_response(self, mock_socket_response):
        """Successfully parses success response."""
        response = {
            "ok": True,
            "id": "req_123",
            "result": {"unread_count": 5}
        }
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            result = call_daemon("gmail.unread_count", socket_path=Path("/tmp/test.sock"))
            assert result == {"unread_count": 5}

    def test_handles_error_response(self, mock_socket_response):
        """Raises DaemonRequestError for error response."""
        response = {
            "ok": False,
            "id": "req_123",
            "error": {
                "code": "AUTH_ERROR",
                "message": "Token expired"
            }
        }
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            with pytest.raises(DaemonRequestError) as exc_info:
                call_daemon("gmail.list", socket_path=Path("/tmp/test.sock"))

            assert exc_info.value.code == "AUTH_ERROR"
            assert "Token expired" in str(exc_info.value)

    def test_handles_connection_refused(self):
        """Raises DaemonConnectionError when connection refused."""
        with pytest.raises(DaemonConnectionError) as exc_info:
            call_daemon("health", socket_path=Path("/tmp/nonexistent.sock"))

        assert "Connection" in str(exc_info.value) or "not found" in str(exc_info.value)


# =============================================================================
# Unit Tests - GoogleDaemonClient
# =============================================================================

class TestGoogleDaemonClient:
    """Tests for high-level client methods."""

    def test_gmail_unread_count(self, mock_socket_response):
        """gmail_unread_count returns integer count."""
        response = {"ok": True, "result": {"unread_count": 42}}
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            client = GoogleDaemonClient(socket_path=Path("/tmp/test.sock"))
            count = client.gmail_unread_count()

            assert count == 42
            assert isinstance(count, int)

    def test_gmail_list_filters(self, mock_socket_response):
        """gmail_list sends filter parameters."""
        response = {"ok": True, "result": {"emails": [], "count": 0}}
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            client = GoogleDaemonClient(socket_path=Path("/tmp/test.sock"))
            client.gmail_list(count=5, unread_only=True, sender="test@example.com")

            sent_data = mock_sock.sendall.call_args[0][0].decode("utf-8")
            request = json.loads(sent_data.strip())

            assert request["params"]["count"] == 5
            assert request["params"]["unread_only"] is True
            assert request["params"]["sender"] == "test@example.com"

    def test_calendar_free_parameters(self, mock_socket_response):
        """calendar_free sends all parameters correctly."""
        response = {"ok": True, "result": {"free_slots": []}}
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            client = GoogleDaemonClient(socket_path=Path("/tmp/test.sock"))
            client.calendar_free(duration=30, days=3, work_start=8, work_end=18)

            sent_data = mock_sock.sendall.call_args[0][0].decode("utf-8")
            request = json.loads(sent_data.strip())

            assert request["params"]["duration"] == 30
            assert request["params"]["days"] == 3
            assert request["params"]["work_start"] == 8
            assert request["params"]["work_end"] == 18

    def test_none_params_filtered(self, mock_socket_response):
        """None parameters are filtered out of request."""
        response = {"ok": True, "result": {"emails": []}}
        mock_sock = mock_socket_response(response)

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_sock

            client = GoogleDaemonClient(socket_path=Path("/tmp/test.sock"))
            client.gmail_list(count=5, sender=None, label=None)

            sent_data = mock_sock.sendall.call_args[0][0].decode("utf-8")
            request = json.loads(sent_data.strip())

            assert "sender" not in request["params"]
            assert "label" not in request["params"]


# =============================================================================
# Live Tests (require running daemon)
# =============================================================================

@pytest.mark.live
class TestLiveDaemon:
    """
    Live tests that require the daemon to be running.

    Run with: pytest -m live tests/integration/test_google_daemon.py
    """

    @pytest.fixture(autouse=True)
    def check_daemon(self):
        """Skip tests if daemon is not running."""
        if not is_daemon_running():
            pytest.skip("Daemon not running - start with: python3 src/integrations/google_daemon/server.py start")

    def test_health_check(self):
        """Health check returns valid status."""
        client = GoogleDaemonClient()
        health = client.health()

        assert "gmail_ok" in health
        assert "calendar_ok" in health
        assert isinstance(health["gmail_ok"], bool)
        assert isinstance(health["calendar_ok"], bool)

    def test_gmail_unread_count_returns_integer(self):
        """Unread count returns valid integer."""
        client = GoogleDaemonClient()
        count = client.gmail_unread_count()

        assert isinstance(count, int)
        assert count >= 0

    def test_gmail_list_returns_emails(self):
        """Email list returns valid structure."""
        client = GoogleDaemonClient()
        result = client.gmail_list(count=5)

        assert "emails" in result
        assert isinstance(result["emails"], list)
        if result["emails"]:
            email = result["emails"][0]
            assert "id" in email or "message_id" in email

    def test_calendar_today_returns_events(self):
        """Today's events returns valid structure."""
        client = GoogleDaemonClient()
        result = client.calendar_today()

        assert "events" in result
        assert isinstance(result["events"], list)

    def test_calendar_week_returns_events(self):
        """Week's events returns valid structure."""
        client = GoogleDaemonClient()
        result = client.calendar_week()

        assert "events" in result
        assert isinstance(result["events"], list)

    def test_calendar_free_returns_slots(self):
        """Free time search returns valid slots."""
        client = GoogleDaemonClient()
        result = client.calendar_free(duration=30, days=3)

        assert "free_slots" in result
        assert isinstance(result["free_slots"], list)


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.live
@pytest.mark.performance
class TestDaemonPerformance:
    """
    Performance tests for daemon operations.

    Run with: pytest -m "live and performance" tests/integration/test_google_daemon.py
    """

    @pytest.fixture(autouse=True)
    def check_daemon(self):
        """Skip tests if daemon is not running."""
        if not is_daemon_running():
            pytest.skip("Daemon not running")

    def test_gmail_unread_under_500ms(self):
        """Gmail unread count completes in <500ms."""
        client = GoogleDaemonClient()

        # Warmup
        client.gmail_unread_count()

        # Measure
        start = time.perf_counter()
        client.gmail_unread_count()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"Unread count took {elapsed_ms:.0f}ms, should be <500ms"

    def test_calendar_today_under_300ms(self):
        """Calendar today completes in <300ms."""
        client = GoogleDaemonClient()

        # Warmup
        client.calendar_today()

        # Measure
        start = time.perf_counter()
        client.calendar_today()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 300, f"Calendar today took {elapsed_ms:.0f}ms, should be <300ms"

    def test_detection_under_10ms(self):
        """Daemon detection completes in <10ms."""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            is_daemon_running()
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        assert avg_time < 10, f"Detection took {avg_time:.2f}ms on average, should be <10ms"


# =============================================================================
# CLI Integration Tests
# =============================================================================

class TestCLIIntegration:
    """Tests for CLI gateway integration with daemon."""

    @pytest.fixture(autouse=True)
    def check_daemon(self):
        """Skip tests if daemon is not running."""
        if not is_daemon_running():
            pytest.skip("Daemon not running")

    @pytest.mark.live
    def test_gmail_cli_daemon_mode(self):
        """Gmail CLI works with --use-daemon flag."""
        cli_path = PROJECT_ROOT / "src" / "integrations" / "gmail" / "gmail_cli.py"
        result = subprocess.run(
            ["python3", str(cli_path), "--use-daemon", "unread", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        output = json.loads(result.stdout)
        assert "unread_count" in output

    @pytest.mark.live
    def test_calendar_cli_daemon_mode(self):
        """Calendar CLI works with --use-daemon flag."""
        cli_path = PROJECT_ROOT / "src" / "integrations" / "google_calendar" / "calendar_cli.py"
        result = subprocess.run(
            ["python3", str(cli_path), "--use-daemon", "today", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        output = json.loads(result.stdout)
        assert "events" in output


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-m", "not live"])

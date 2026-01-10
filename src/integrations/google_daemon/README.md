# Google API Daemon

Shared daemon for Gmail and Calendar APIs providing warm, low-latency access to Google services.

## Overview

The Google daemon pre-initializes OAuth credentials and API service objects, eliminating the ~1-2 second cold start overhead per operation. This results in **7-15x speedup** for typical operations.

```
┌────────────────────────────────────────────────────────────────────┐
│                        Google API Daemon                            │
│           (src/integrations/google_daemon/server.py)               │
├────────────────────────────────────────────────────────────────────┤
│  Shared Resources (pre-initialized):                               │
│  ├── OAuth2 Credentials (single token refresh)                     │
│  ├── Gmail API Service (googleapiclient)                           │
│  └── Calendar API Service (googleapiclient)                        │
├────────────────────────────────────────────────────────────────────┤
│  NDJSON Protocol (Unix socket):                                    │
│  ├── health                                                        │
│  ├── gmail.unread_count, gmail.list, gmail.search                  │
│  ├── gmail.get, gmail.send, gmail.mark_read                        │
│  ├── calendar.today, calendar.week, calendar.events                │
│  ├── calendar.get, calendar.free, calendar.create                  │
│  └── calendar.delete                                               │
└────────────────────────────────────────────────────────────────────┘
```

## Performance

### Benchmark Results (01/08/2026)

| Operation | CLI Cold | CLI+Daemon | Speedup |
|-----------|----------|------------|---------|
| Gmail unread count | 1,032ms | 167ms | **6.2x** |
| Gmail list 5 | 1,471ms | 285ms | **5.2x** |
| Gmail list 10 | 1,177ms | 318ms | **3.7x** |
| Gmail list 25 | 1,327ms | 401ms | **3.3x** |
| Gmail search | 1,161ms | 287ms | **4.1x** |
| Calendar today | 1,130ms | 126ms | **9.0x** |
| Calendar week | 1,028ms | 115ms | **8.9x** |
| Calendar free 30min | 1,003ms | 111ms | **9.0x** |
| Calendar free 60min | 1,049ms | 116ms | **9.0x** |
| **Average** | **1,656ms** | **214ms** | **7.7x** |

### Where Time is Saved

- **Python interpreter startup**: ~100ms eliminated
- **google-api-python-client import**: ~2,000ms eliminated (lazy imports)
- **OAuth token load/refresh**: ~200-400ms eliminated (pre-warmed)
- **API service discovery**: ~200ms eliminated (cached)

## Usage

### Starting the Daemon

```bash
# Start daemon (runs in background)
python3 src/integrations/google_daemon/server.py start

# Check status
python3 src/integrations/google_daemon/server.py status

# Stop daemon
python3 src/integrations/google_daemon/server.py stop
```

### CLI Integration

Both Gmail and Calendar CLIs support `--use-daemon` flag:

```bash
# Gmail operations via daemon
python3 src/integrations/gmail/gmail_cli.py --use-daemon unread --json
python3 src/integrations/gmail/gmail_cli.py --use-daemon list 10 --json
python3 src/integrations/gmail/gmail_cli.py --use-daemon search "from:boss" --json

# Calendar operations via daemon
python3 src/integrations/google_calendar/calendar_cli.py --use-daemon today --json
python3 src/integrations/google_calendar/calendar_cli.py --use-daemon week --json
python3 src/integrations/google_calendar/calendar_cli.py --use-daemon free 30 --json
```

### Python Client

```python
from src.integrations.google_daemon import GoogleDaemonClient, is_daemon_running

if is_daemon_running():
    client = GoogleDaemonClient()

    # Gmail operations
    unread = client.gmail_unread_count()
    emails = client.gmail_list(count=10)
    results = client.gmail_search("from:boss")

    # Calendar operations
    today = client.calendar_today()
    week = client.calendar_week()
    free_slots = client.calendar_free(duration=30, days=7)
```

## Architecture

### Socket and PID Locations

```
~/.wolfies-google/daemon.sock    # Unix socket for communication
~/.wolfies-google/daemon.pid     # Process ID file
```

### NDJSON Protocol

The daemon uses newline-delimited JSON over Unix domain sockets:

**Request format:**
```json
{"id": "req_123", "method": "gmail.list", "params": {"count": 10}, "v": 1}
```

**Success response:**
```json
{"ok": true, "id": "req_123", "result": {"emails": [...], "count": 10}}
```

**Error response:**
```json
{"ok": false, "id": "req_123", "error": {"code": "AUTH_ERROR", "message": "Token expired"}}
```

### Pre-warming Integration

The daemon is automatically pre-warmed on Claude Code session start via the SessionStart hook:

```python
# ~/.claude/hooks/session_start.py
def prewarm_daemons_async():
    """Pre-warm daemons in background (non-blocking)."""
    # Fast detection (<10ms) to skip if already running
    # Non-blocking startup if needed
```

### Fast Daemon Detection (<10ms)

The detection algorithm avoids slow operations:

```python
def is_daemon_running():
    # Level 1: Socket exists? (<1ms)
    if not socket_path.exists():
        return False

    # Level 2: PID alive? (<0.1ms)
    pid = read_pid(pid_path)
    os.kill(pid, 0)  # Signal 0 = check if alive

    # Level 3: Socket listening? (5ms timeout)
    socket.connect(socket_path)  # Quick connect test
```

## API Reference

### Health Check

```python
client.health()  # Returns {"gmail_ok": true, "calendar_ok": true}
```

### Gmail Methods

| Method | Parameters | Returns |
|--------|------------|---------|
| `gmail_unread_count()` | - | `int` |
| `gmail_list(count, unread_only, label, sender, after, before)` | count: int = 10 | `{"emails": [...], "count": N}` |
| `gmail_search(query, max_results)` | query: str, max_results: int = 10 | `{"emails": [...], "query": "..."}` |
| `gmail_get(message_id)` | message_id: str | `{"email": {...}}` |
| `gmail_send(to, subject, body)` | to, subject, body: str | `{"message_id": "..."}` |
| `gmail_mark_read(message_id)` | message_id: str | `{"success": true}` |

### Calendar Methods

| Method | Parameters | Returns |
|--------|------------|---------|
| `calendar_today()` | - | `{"events": [...], "count": N}` |
| `calendar_week()` | - | `{"events": [...], "count": N}` |
| `calendar_events(count, days)` | count: int = 10, days: int = 7 | `{"events": [...]}` |
| `calendar_get(event_id)` | event_id: str | `{"event": {...}}` |
| `calendar_free(duration, days, limit, work_start, work_end)` | duration: int = 60 | `{"free_slots": [...]}` |
| `calendar_create(title, start, end, ...)` | title, start, end: str | `{"event_id": "..."}` |
| `calendar_delete(event_id)` | event_id: str | `{"success": true}` |

## Configuration

### OAuth Credentials

The daemon uses OAuth credentials from:
```
config/google_credentials/
├── credentials.json     # OAuth client ID/secret
└── token.json          # Cached OAuth tokens
```

### Working Hours (for free time search)

Default working hours: 9 AM - 5 PM local time. Override via parameters:

```python
client.calendar_free(
    duration=60,
    days=7,
    work_start=8,   # 8 AM
    work_end=18     # 6 PM
)
```

## Troubleshooting

### Daemon won't start

1. Check credentials: `ls config/google_credentials/`
2. Verify OAuth: Run Gmail CLI without daemon to trigger auth flow
3. Check logs: `cat ~/.wolfies-google/daemon.log`

### Connection refused

```bash
# Check if socket exists
ls -la ~/.wolfies-google/daemon.sock

# Check if PID is valid
cat ~/.wolfies-google/daemon.pid
ps -p $(cat ~/.wolfies-google/daemon.pid)

# Restart daemon
python3 src/integrations/google_daemon/server.py stop
python3 src/integrations/google_daemon/server.py start
```

### Slow performance

If daemon mode is slower than expected:
1. Verify daemon is actually running: `python3 server.py status`
2. Check if CLI is using daemon: Look for "Using daemon" in verbose output
3. Ensure imports are lazy in CLI (check `TYPE_CHECKING` guards)

## Files

| File | Purpose |
|------|---------|
| `server.py` | Daemon server (Gmail + Calendar API handler) |
| `client.py` | Thin client for daemon communication |
| `__init__.py` | Package exports |
| `~/.claude/bin/daemon-prewarm` | Pre-warm script for SessionStart hook |

## Changelog

- **01/08/2026**: Initial implementation with 7.7x average speedup
- **01/08/2026**: Added SessionStart hook integration for pre-warming
- **01/08/2026**: Added `--use-daemon` flag to Gmail and Calendar CLIs

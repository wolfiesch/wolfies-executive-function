# CLAUDE.md

This file provides guidance to Claude Code when working with the Reminders MCP server.

## Project Overview

Apple Reminders MCP server for macOS. Create, list, complete, and delete reminders through Claude with automatic logging to Life Planner database.

**Hybrid architecture:**
- AppleScript for creating reminders (simple, reliable)
- EventKit (PyObjC) for reading, completing, deleting (robust querying)

## Build & Test Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# Initialize database schema
python3 scripts/init_db.py

# Run test suite
python3 scripts/test_mcp_protocol.py

# Run unit tests
pytest tests/ -v

# Start MCP server manually (for debugging)
python3 mcp_server/server.py

# Verify MCP server registration
claude mcp list
```

## Architecture

### MCP Server Flow

```
Claude Code ──(JSON-RPC/stdio)──> mcp_server/server.py
                                        │
                                        ├── reminder_manager.py
                                        │       └── Validates inputs, auto-logs to DB
                                        │
                                        └── reminders_interface.py
                                                ├── AppleScript → Reminders.app (create)
                                                ├── PyObjC EventKit → EKEventStore (read, complete, delete)
                                                └── SQLite → ../data/database/planner.db (logging)
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `create_reminder` | Create reminder with optional due date and notes |
| `list_reminders` | List reminders from default list |
| `complete_reminder` | Mark reminder as complete |
| `delete_reminder` | Delete reminder permanently |

### Path Resolution (Critical)

MCP servers are started from arbitrary working directories. All paths in `server.py` use:

```python
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "mcp_server.json"
```

Always use absolute paths resolved from `PROJECT_ROOT`, never relative paths.

### Import Pattern

The server uses `sys.path` insertion to enable imports from `src/`:

```python
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.reminders_interface import RemindersInterface
```

This is necessary because MCP servers run as standalone processes, not as installed packages.

## Key Files

| File | Purpose |
|------|---------|
| `mcp_server/server.py` | MCP server entry point, tool handlers |
| `src/reminders_interface.py` | Core interface (AppleScript + EventKit) |
| `src/reminder_manager.py` | Business logic, validation, DB logging |
| `src/reminder_sync.py` | PyObjC EventKit utilities |
| `config/mcp_server.json` | Server configuration |
| `scripts/init_db.py` | Database initialization |

## EventKit Integration

### Date Conversions

EventKit uses Objective-C types that need conversion:

```python
# NSDate → Python datetime
from src.reminder_sync import EventKitHelper
dt = EventKitHelper.convert_nsdate_to_datetime(nsdate)

# NSDateComponents → Python datetime
dt = EventKitHelper.convert_nsdatecomponents_to_datetime(components)

# Python datetime → NSDate
nsdate = EventKitHelper.convert_datetime_to_nsdate(dt)
```

### Async Callbacks

EventKit fetching is asynchronous. We use `threading.Event` to synchronize:

```python
fetch_complete = threading.Event()
event_store.fetchRemindersMatchingPredicate_completion_(predicate, callback)
fetch_complete.wait(timeout=10.0)
```

## AppleScript Security

### Injection Prevention

**CRITICAL:** Always escape user inputs before AppleScript execution:

```python
from src.reminders_interface import escape_applescript_string

escaped_title = escape_applescript_string(user_title)
script = f'set name of newReminder to "{escaped_title}"'
```

**Why:** Prevents shell command injection via malicious inputs.

**Attack vector:**
```python
title = 'Test" & do shell script "rm -rf /" & "'
# Without escaping: DANGEROUS - executes shell command
# With escaping: Safe - treated as literal string
```

## Database Logging

All reminder interactions are logged to `reminder_interactions` table:

```python
def _log_interaction(action, reminder_id, title, **kwargs):
    cursor.execute("""
        INSERT INTO reminder_interactions
        (timestamp, action, reminder_id, title, metadata)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, action, reminder_id, title, json.dumps(kwargs)))
```

**Security:** Always use parameterized queries (never string interpolation).

## Validation Patterns

All inputs are validated before processing:

```python
from src.reminder_manager import (
    validate_non_empty_string,
    validate_iso_datetime,
    validate_positive_int
)

# Validate title
title, error = validate_non_empty_string(user_input, "title")
if error:
    return {"success": False, "error": error}

# Validate due date
due_dt, error = validate_iso_datetime(date_string, "due_date")
if error:
    return {"success": False, "error": error}
```

## macOS Permissions

### Required Permissions

1. **Reminders Access (EventKit)**
   - System Settings → Privacy & Security → Reminders → Enable Terminal

2. **Automation (AppleScript)**
   - System Settings → Privacy & Security → Automation → Terminal → Reminders

### Permission Check

```python
interface = RemindersInterface()
permissions = interface.check_permissions()

if not permissions['reminders_authorized']:
    # EventKit access denied

if not permissions['applescript_ready']:
    # AppleScript automation denied
```

## Troubleshooting

**MCP tools not appearing:**
```bash
# Check server is registered
claude mcp list

# Re-register if needed
claude mcp add -t stdio reminders-life-planner -- \
  python3 /Users/wolfgangschoenberger/LIFE-PLANNER/Reminders/mcp_server/server.py

# Check logs
tail -f logs/mcp_server.log
```

**"Reminder not found":**
- Reminder ID is stale or invalid
- Use `list_reminders` to get current IDs

**EventKit async timeout:**
- Increase timeout in `list_reminders` (default: 10 seconds)
- Check permissions are granted

**AppleScript errors:**
- Ensure Reminders.app is running
- Verify automation permissions granted
- Check for special characters in input (should be escaped)

## Configuration

`config/mcp_server.json`:

```json
{
  "reminders": {
    "default_list": "Reminders"  // Change to your preferred list
  },
  "features": {
    "auto_interaction_logging": true  // Set to false to disable DB logging
  }
}
```

## Dependencies

Core: `mcp>=1.0.0`, `pyobjc-framework-EventKit>=12.0`, `pyobjc-core`

Install: `pip3 install -r requirements.txt`

## Future Extensions

### T1 (Planned)
- Multi-list support
- Recurring reminders
- Priority and tags

### T2 (Planned)
- Natural language date parsing
- Smart scheduling
- Analytics and insights
- Bidirectional task sync with Life Planner

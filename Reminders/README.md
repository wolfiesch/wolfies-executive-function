# Apple Reminders MCP Server

> **ℹ️ LOCAL-ONLY INTEGRATION**
>
> This is a **macOS-specific local MCP server** that interfaces directly with Apple Reminders.app.
>
> **NOT available via Rube/Composio** - Apple Reminders requires local macOS EventKit access and is not a cloud service.
>
> Use the MCP tools prefixed with `mcp__reminders-life-planner__*` (e.g., `create_reminder`, `list_reminders`)
>
> ---

An MCP (Model Context Protocol) server that enables Claude Code to create, list, complete, and delete reminders in macOS Reminders.app with automatic logging to the Life Planner database.

## Features (T0)

✅ **Create reminders** with optional due dates and notes
✅ **List reminders** from your default reminder list
✅ **Complete reminders** to mark tasks as done
✅ **Delete reminders** permanently
✅ **Auto-logging** to Life Planner database for analytics

## Architecture

**Hybrid Approach:**
- **AppleScript** for creating reminders (simple, reliable)
- **EventKit framework** (PyObjC) for reading, completing, deleting (robust querying)

**Data Flow:**
```
Claude Code → MCP Protocol → server.py → reminder_manager.py → reminders_interface.py
                                                                  ├── AppleScript → Reminders.app
                                                                  ├── EventKit → EKEventStore
                                                                  └── SQLite → planner.db
```

## Installation

### 1. Install Dependencies

```bash
cd /Users/wolfgangschoenberger/LIFE-PLANNER/Reminders
pip3 install -r requirements.txt
```

**Dependencies:**
- `mcp>=1.0.0` - MCP protocol server
- `pyobjc-framework-EventKit>=12.0` - EventKit bindings
- `pyobjc-core` - PyObjC core
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting

### 2. Initialize Database

```bash
python3 scripts/init_db.py
```

This creates the `reminder_interactions` table in your Life Planner database for logging reminder activity.

### 3. Grant macOS Permissions

**Required permissions:**

#### A. Reminders Access (EventKit)
1. Open **System Settings** → **Privacy & Security** → **Reminders**
2. Enable access for **Terminal.app** (or Claude Code if bundled)
3. ✅ Verify: `Reminders authorized: True`

#### B. Automation Permissions (AppleScript)
1. Open **System Settings** → **Privacy & Security** → **Automation**
2. Find **Terminal** → Enable **Reminders**
3. ✅ Verify: `AppleScript ready: True`

**Verify permissions:**
```bash
python3 scripts/test_mcp_protocol.py
```

### 4. Register MCP Server

```bash
claude mcp add -t stdio reminders-life-planner -- \
  python3 /Users/wolfgangschoenberger/LIFE-PLANNER/Reminders/mcp_server/server.py
```

**Verify registration:**
```bash
claude mcp list
```

You should see `✓ reminders-life-planner` in the output.

## Usage

### Create a Reminder

```python
# Via Claude Code:
"Create a reminder to call John tomorrow at 2pm"

# Translates to MCP tool:
create_reminder(
    title="Call John",
    due_date="2025-01-01T14:00:00",
    notes="Discuss project timeline"
)
```

**Returns:**
```json
{
  "success": true,
  "reminder_id": "x-apple-reminder://ABC123...",
  "error": null
}
```

### List Reminders

```python
# Via Claude Code:
"What reminders do I have?"

# Translates to MCP tool:
list_reminders(limit=50, completed=False)
```

**Returns:**
```json
{
  "reminders": [
    {
      "reminder_id": "x-apple-reminder://ABC123...",
      "title": "Call John",
      "completed": false,
      "due_date": "2025-01-01T14:00:00+00:00",
      "notes": "Discuss project timeline",
      "creation_date": "2025-12-31T21:00:00+00:00",
      "list_name": "Reminders",
      "priority": 0
    }
  ],
  "count": 1
}
```

### Complete a Reminder

```python
# Via Claude Code:
"Mark the 'Call John' reminder as done"

# Translates to MCP tool:
complete_reminder(reminder_id="x-apple-reminder://ABC123...")
```

**Returns:**
```json
{
  "success": true,
  "error": null
}
```

### Delete a Reminder

```python
# Via Claude Code:
"Delete the 'Call John' reminder"

# Translates to MCP tool:
delete_reminder(reminder_id="x-apple-reminder://ABC123...")
```

**Returns:**
```json
{
  "success": true,
  "error": null
}
```

## Configuration

Edit `config/mcp_server.json`:

```json
{
  "server_name": "reminders-life-planner",
  "paths": {
    "life_planner_db": "../data/database/planner.db"
  },
  "reminders": {
    "default_list": "Reminders"  // Change to your preferred list
  },
  "features": {
    "auto_interaction_logging": true  // Disable to skip DB logging
  }
}
```

## Database Schema

The `reminder_interactions` table logs all reminder operations:

```sql
CREATE TABLE reminder_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('created', 'completed', 'deleted', 'updated')),
    reminder_id TEXT NOT NULL,
    title TEXT NOT NULL,
    due_date DATETIME,
    completion_date DATETIME,
    metadata TEXT  -- JSON for additional fields
);
```

**Indexes:**
- `idx_reminder_interactions_timestamp` - Fast time-range queries
- `idx_reminder_interactions_action` - Filter by action type
- `idx_reminder_interactions_reminder_id` - Lookup by reminder ID

## Testing

### Run Test Suite

```bash
python3 scripts/test_mcp_protocol.py
```

**Test sequence:**
1. ✓ Check permissions (EventKit + AppleScript)
2. ✓ Create test reminder
3. ✓ List reminders
4. ✓ Complete reminder
5. ✓ Delete reminder

### Unit Tests

```bash
cd /Users/wolfgangschoenberger/LIFE-PLANNER/Reminders
pytest tests/ -v
```

## Troubleshooting

### "Reminders not authorized"
**Solution:** Grant EventKit access in System Settings → Privacy → Reminders → Enable Terminal

### "AppleScript ready: False"
**Solution:** Grant automation permission in System Settings → Automation → Terminal → Reminders

### "MCP tools not appearing"
**Solution:**
```bash
# Re-register server
claude mcp add -t stdio reminders-life-planner -- \
  python3 /Users/wolfgangschoenberger/LIFE-PLANNER/Reminders/mcp_server/server.py

# Restart Claude Code
# Verify: claude mcp list
```

### "Reminder not found"
**Cause:** Invalid reminder_id (stale or incorrect ID)
**Solution:** Use `list_reminders` to get current reminder IDs

### "Database locked"
**Cause:** Concurrent writes to SQLite
**Solution:** The system handles this automatically with retries. If persistent, check for other processes accessing the database.

## Security

### AppleScript Injection Prevention
All user inputs are escaped before AppleScript execution:
```python
escape_applescript_string(title)  # Escapes \ then "
```

**Attack vector blocked:**
```python
title = 'Test" & do shell script "rm -rf /" & "'
# Safe: 'Test\" & do shell script \"rm -rf /\" & \"'
```

### SQL Injection Prevention
All database operations use parameterized queries:
```python
cursor.execute("INSERT INTO table (col) VALUES (?)", (value,))
# Never: f"INSERT INTO table (col) VALUES ('{value}')"
```

## Future Extensions (Planned)

### T1 Features
- ✨ **Multi-list support** - Create reminders in any list
- 🔁 **Recurring reminders** - Daily, weekly, monthly patterns
- 🏷️ **Priority & tags** - Organize with priorities and custom tags

### T2 Features
- 🧠 **Natural language parsing** - "Remind me tomorrow at 3pm"
- 🔄 **Task sync** - Bidirectional sync with Life Planner tasks
- 📊 **Analytics** - Completion rates, productivity insights
- 🎯 **Smart scheduling** - Suggest optimal reminder times

## Technical Details

### Hybrid Architecture Rationale

**Why AppleScript for creation?**
- Simple, reliable, well-documented
- Handles all reminder properties (due date, notes, priority)
- No async callback complexity

**Why EventKit for reading?**
- Robust querying with predicates
- Type-safe data structures
- Proper date/time handling
- Complete reminder metadata access

**Why avoid direct database access?**
- Reminders uses SQLite with WAL mode (Write-Ahead Logging)
- Direct access can cause database corruption
- Apple's APIs handle synchronization properly

### PyObjC Integration

**Date conversions:**
```python
# NSDate → Python datetime
timestamp = nsdate.timeIntervalSince1970()
dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

# NSDateComponents → Python datetime
year, month, day = components.year(), components.month(), components.day()
dt = datetime(year, month, day, tzinfo=timezone.utc)
```

**Async callbacks:**
EventKit uses async callbacks for fetching reminders. We handle this with `threading.Event`:
```python
fetch_complete = threading.Event()
event_store.fetchRemindersMatchingPredicate_completion_(predicate, callback)
fetch_complete.wait(timeout=10.0)
```

## Project Structure

```
Reminders/
├── config/
│   ├── mcp_server.json      # Server configuration
│   └── lists.json           # Reminder lists config (T1)
├── mcp_server/
│   └── server.py            # MCP entry point
├── src/
│   ├── __init__.py
│   ├── reminders_interface.py  # Core interface (AppleScript + EventKit)
│   ├── reminder_manager.py     # Business logic, validation
│   └── reminder_sync.py        # PyObjC EventKit utilities
├── scripts/
│   ├── init_db.py              # Database initialization
│   └── test_mcp_protocol.py    # Integration tests
├── tests/
│   └── (unit tests)
├── logs/
│   └── mcp_server.log          # Server logs
├── requirements.txt
├── README.md                   # This file
└── CLAUDE.md                   # Project guidance for Claude Code
```

## References

- [PyObjC EventKit Documentation](https://pyobjc.readthedocs.io/en/latest/apinotes/EventKit.html)
- [Apple EventKit Framework](https://developer.apple.com/documentation/eventkit)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## License

Part of the Life Planner system. See top-level LICENSE file.

---

**Current timestamp:** 12/31/2025 09:15 PM PST (via pst-timestamp)

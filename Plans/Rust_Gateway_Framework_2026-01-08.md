# Rust Gateway Framework: Unified Life Planner Architecture

**Goal**: Convert all Life Planner MCP servers and agentic tools to a unified Rust gateway framework with a centralized daemon.

**Status**: Planning
**Created**: 01/08/2026 02:30 AM PST

---

## Executive Summary

The iMessage Texting daemon demonstrated that a Rust thin client reduces spawn overhead from ~35ms to ~2.8ms (12x improvement). This plan extends that pattern to all Life Planner integrations via a **unified Rust gateway framework**.

### Key Insight from iMessage Benchmarks

| Metric | Python MCP | Python Daemon | Rust Daemon Client |
|--------|------------|---------------|-------------------|
| Spawn overhead | 763ms | 35ms | 2.8ms |
| End-to-end (simple op) | 800ms+ | 40ms | ~5ms |
| Improvement | baseline | 19x | **270x** |

The Rust client achieves sub-5ms end-to-end latency for simple operations. Applying this pattern across Gmail, Calendar, and Reminders would yield similar gains.

---

## Current State Analysis

### Inventory of Services to Migrate

| Service | Current Protocol | LOC | Tools/Commands | External API |
|---------|------------------|-----|----------------|--------------|
| **Texting Daemon** | UNIX socket (NDJSON) | 724 | 7 methods | SQLite (local) |
| **Reminders MCP** | MCP stdio | 393 | 6 tools | AppleScript/EventKit |
| **Gmail MCP** | MCP stdio | 620 | 5 tools | Google Gmail API |
| **Calendar MCP** | MCP stdio | 716 | 4 tools | Google Calendar API |
| **Texting CLI** | CLI (Bash) | 2,419 | 27 commands | SQLite + AppleScript |

### Current Pain Points

1. **MCP Spawn Overhead**: Each MCP tool call spawns a Python process (~35-100ms overhead)
2. **Duplicate Initialization**: Each call re-imports libraries, re-parses configs, re-establishes connections
3. **No Connection Pooling**: Google API OAuth token refresh happens per-process
4. **Inconsistent Protocols**: Mix of MCP stdio, UNIX socket, and direct CLI
5. **No Shared State**: Each service maintains separate caches

---

## Proposed Architecture

### Option A: Multi-Daemon (Current Pattern Extended)

Each service gets its own warm daemon:

```
┌──────────────────────────────────────────────────────────────┐
│                      Claude Code                              │
│    (invokes thin Rust clients via Bash tool)                 │
└──────────────────────────────────────────────────────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ wolfies-    │      │ wolfies-    │      │ wolfies-    │
│ imessage    │      │ gmail       │      │ calendar    │
│             │      │             │      │             │
│ (Rust CLI)  │      │ (Rust CLI)  │      │ (Rust CLI)  │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ imessage-   │      │ gmail-      │      │ calendar-   │
│ daemon.py   │      │ daemon.py   │      │ daemon.py   │
│             │      │             │      │             │
│ (UNIX sock) │      │ (UNIX sock) │      │ (UNIX sock) │
└─────────────┘      └─────────────┘      └─────────────┘
```

**Pros**:
- Fault isolation (one daemon crash doesn't affect others)
- Simpler development (independent deployment)
- Already proven with iMessage

**Cons**:
- Multiple socket files to manage
- Multiple processes consuming memory
- No shared OAuth token cache

---

### Option B: Unified Daemon (Recommended)

Single daemon with multiple service backends:

```
┌──────────────────────────────────────────────────────────────┐
│                      Claude Code                              │
│    (invokes thin Rust client via Bash tool)                  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  ┌─────────────────────┐
                  │  wolfies-client     │
                  │  (Rust universal)   │
                  │                     │
                  │  Subcommands:       │
                  │  - imessage <cmd>   │
                  │  - gmail <cmd>      │
                  │  - calendar <cmd>   │
                  │  - reminders <cmd>  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  wolfies-daemon     │
                  │  (Python unified)   │
                  │                     │
                  │  Services:          │
                  │  ├── iMessage       │
                  │  ├── Gmail          │
                  │  ├── Calendar       │
                  │  └── Reminders      │
                  │                     │
                  │  Shared:            │
                  │  ├── OAuth cache    │
                  │  ├── Config loader  │
                  │  └── Logging        │
                  └─────────────────────┘
                             │
          ┌─────────────┬────┴────┬─────────────┐
          ▼             ▼         ▼             ▼
     ┌────────┐   ┌─────────┐ ┌─────────┐  ┌─────────┐
     │SQLite  │   │Gmail API│ │Calendar │  │EventKit │
     │chat.db │   │         │ │   API   │  │AppleScpt│
     └────────┘   └─────────┘ └─────────┘  └─────────┘
```

**Pros**:
- Single process, single socket
- Shared OAuth token cache (no duplicate refreshes)
- Unified configuration and logging
- Simpler process management
- Cross-service operations possible (e.g., "schedule email reminder")

**Cons**:
- More complex daemon implementation
- Single point of failure (mitigated by watchdog)
- Larger initial development effort

**Recommendation**: **Option B (Unified Daemon)** for long-term maintainability and performance.

---

## Rust Shared Library Design

### Crate Structure

```
Texting/gateway/wolfies-client/
├── Cargo.toml                 # Workspace root
├── crates/
│   ├── wolfies-core/          # Shared types, protocol, socket client
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── protocol.rs    # Request/Response types
│   │       ├── client.rs      # DaemonClient (socket communication)
│   │       ├── output.rs      # Output formatting (emit_response)
│   │       └── error.rs       # ClientError enum
│   │
│   ├── wolfies-imessage/      # iMessage-specific commands
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       └── commands.rs    # health, unread, recent, search, bundle
│   │
│   ├── wolfies-gmail/         # Gmail-specific commands
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       └── commands.rs    # list, get, search, send, unread-count
│   │
│   ├── wolfies-calendar/      # Calendar-specific commands
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       └── commands.rs    # list, get, create, find-free-time
│   │
│   └── wolfies-reminders/     # Reminders-specific commands
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           └── commands.rs    # create, list, complete, delete
│
└── src/
    └── main.rs                # Unified CLI entry point
```

### Shared Code (wolfies-core)

The `wolfies-core` crate contains:

```rust
// protocol.rs - Shared request/response types
#[derive(Serialize)]
pub struct Request {
    pub id: String,
    pub v: u8,
    pub service: String,  // "imessage", "gmail", "calendar", "reminders"
    pub method: String,
    pub params: serde_json::Value,
}

#[derive(Deserialize)]
pub struct Response {
    pub id: String,
    pub ok: bool,
    pub result: Option<serde_json::Value>,
    pub error: Option<ErrorPayload>,
    pub meta: Option<Meta>,
}

// Output controls (shared across all services)
#[derive(Clone, Default)]
pub struct OutputControls {
    pub compact: bool,
    pub minimal: bool,
    pub fields: Option<Vec<String>>,
    pub max_text_chars: Option<usize>,
    pub pretty: bool,
}
```

```rust
// client.rs - Shared socket client
pub struct DaemonClient {
    socket_path: PathBuf,
    timeout: Duration,
}

impl DaemonClient {
    pub fn call(&self, request: &Request) -> Result<Response, ClientError> {
        // NDJSON over UNIX socket (same as iMessage implementation)
    }
}
```

### CLI Design (Unified)

```bash
# iMessage operations
wolfies-client imessage health
wolfies-client imessage unread --limit 10 --minimal
wolfies-client imessage text-search "meeting" --limit 20

# Gmail operations
wolfies-client gmail list --limit 20 --unread
wolfies-client gmail get <message-id>
wolfies-client gmail search "from:boss subject:urgent" --limit 10

# Calendar operations
wolfies-client calendar list --days 7
wolfies-client calendar create "Team standup" --start "2026-01-09T10:00:00"
wolfies-client calendar find-free-time --duration 60 --days 3

# Reminders operations
wolfies-client reminders list
wolfies-client reminders create "Call dentist" --due "tomorrow 2pm"
wolfies-client reminders complete <reminder-id>

# Global flags (apply to all services)
wolfies-client --socket /path/to/socket --timeout 5 --minimal gmail list
```

---

## Python Unified Daemon Design

### Architecture

```python
# wolfies_daemon.py

class UnifiedDaemon:
    """Single daemon serving all Life Planner services."""

    def __init__(self, socket_path: Path, config: Config):
        self.socket_path = socket_path
        self.config = config

        # Service backends (lazy-loaded)
        self._imessage: Optional[IMessageBackend] = None
        self._gmail: Optional[GmailBackend] = None
        self._calendar: Optional[CalendarBackend] = None
        self._reminders: Optional[RemindersBackend] = None

        # Shared state
        self._oauth_cache: Dict[str, OAuth2Credentials] = {}

    def get_backend(self, service: str) -> ServiceBackend:
        """Lazy-load and cache service backends."""
        if service == "imessage":
            if self._imessage is None:
                self._imessage = IMessageBackend(self.config)
            return self._imessage
        elif service == "gmail":
            if self._gmail is None:
                self._gmail = GmailBackend(self.config, self._oauth_cache)
            return self._gmail
        # ... etc

    async def handle_request(self, request: Request) -> Response:
        """Route request to appropriate backend."""
        backend = self.get_backend(request.service)
        return await backend.dispatch(request.method, request.params)
```

### Service Backend Interface

```python
class ServiceBackend(Protocol):
    """Interface all service backends must implement."""

    async def dispatch(self, method: str, params: dict) -> Response:
        """Route method call to handler."""
        ...

    def health(self) -> dict:
        """Health check for this service."""
        ...
```

### Shared Components

```python
# Shared OAuth cache (eliminates duplicate token refreshes)
class OAuthCache:
    def __init__(self, credentials_dir: Path):
        self.credentials_dir = credentials_dir
        self._cache: Dict[str, google.oauth2.credentials.Credentials] = {}

    def get_gmail_credentials(self) -> Credentials:
        if "gmail" not in self._cache:
            self._cache["gmail"] = self._load_credentials("gmail_token.json")
        return self._cache["gmail"]

    def get_calendar_credentials(self) -> Credentials:
        # Share same credentials if scopes allow
        return self.get_gmail_credentials()
```

---

## Implementation Phases

### Phase 0: Foundation (This PR - Complete)
- [x] Rust daemon client for iMessage
- [x] Benchmark harness integration
- [x] 12x spawn overhead reduction validated

### Phase 1: Rust Workspace Refactor (1-2 days)
Convert single-crate Rust client to workspace with shared `wolfies-core`:

1. Create workspace structure
2. Extract protocol.rs, client.rs, output.rs to wolfies-core
3. Create wolfies-imessage crate (move existing code)
4. Verify benchmarks unchanged

**Files to create:**
- `wolfies-client/Cargo.toml` (workspace)
- `wolfies-client/crates/wolfies-core/`
- `wolfies-client/crates/wolfies-imessage/`

### Phase 2: Gmail Integration (2-3 days)
Add Gmail support to unified daemon:

1. Create `wolfies-gmail` Rust crate with commands
2. Add Gmail backend to unified daemon
3. Migrate existing Gmail MCP tools to daemon methods
4. Benchmark: expect ~10-15x improvement over MCP

**Methods:**
- `list_emails` - Recent/unread emails
- `get_email` - Full email content
- `search_emails` - Gmail search syntax
- `send_email` - Plain text sending
- `unread_count` - Unread count

### Phase 3: Calendar Integration (2-3 days)
Add Calendar support:

1. Create `wolfies-calendar` Rust crate
2. Add Calendar backend (shares OAuth with Gmail)
3. Migrate Calendar MCP tools
4. Test shared OAuth token caching

**Methods:**
- `list_events` - Upcoming events
- `get_event` - Event details
- `create_event` - New event
- `find_free_time` - Available slots

### Phase 4: Reminders Integration (1-2 days)
Add Reminders support:

1. Create `wolfies-reminders` Rust crate
2. Add Reminders backend (AppleScript/EventKit)
3. Migrate Reminders MCP tools

**Methods:**
- `list_reminders` - All reminders
- `list_lists` - Reminder lists
- `create_reminder` - New reminder
- `complete_reminder` - Mark done
- `delete_reminder` - Remove

### Phase 5: Unified Daemon Consolidation (2-3 days)
Merge individual daemons into unified daemon:

1. Create `wolfies_daemon.py` with service multiplexing
2. Update Rust client to use service prefix in requests
3. Implement shared OAuth cache
4. Add comprehensive health checks
5. Add watchdog process management

**Socket path:** `~/.wolfies-life-planner/daemon.sock`

### Phase 6: Deprecate MCP Servers (1 day)
After unified daemon is stable:

1. Archive MCP servers (like Texting MCP)
2. Update Claude Code skill definitions
3. Remove MCP registrations from `~/.claude.json`
4. Document migration for any external users

---

## Protocol Extension

### Service-Aware Request Format

```json
{
  "id": "uuid-1234",
  "v": 1,
  "service": "gmail",
  "method": "list_emails",
  "params": {
    "limit": 20,
    "unread": true
  }
}
```

### Response Format (Unchanged)

```json
{
  "id": "uuid-1234",
  "ok": true,
  "result": { ... },
  "meta": {
    "duration_ms": 12.5,
    "service": "gmail"
  }
}
```

### Health Check (Cross-Service)

```bash
wolfies-client health
```

Response:
```json
{
  "ok": true,
  "result": {
    "services": {
      "imessage": { "status": "ok", "db_connected": true },
      "gmail": { "status": "ok", "token_valid": true, "expires_in": 3500 },
      "calendar": { "status": "ok", "token_valid": true },
      "reminders": { "status": "ok", "eventkit_available": true }
    },
    "daemon": {
      "uptime_s": 3600,
      "requests_served": 1250,
      "memory_mb": 45
    }
  }
}
```

---

## Expected Performance Gains

| Service | Current (MCP) | After (Rust+Daemon) | Expected Gain |
|---------|---------------|---------------------|---------------|
| Gmail list | ~800ms | ~50ms | **16x** |
| Gmail send | ~900ms | ~150ms | **6x** |
| Calendar list | ~700ms | ~40ms | **17x** |
| Calendar create | ~800ms | ~200ms | **4x** |
| Reminders list | ~600ms | ~30ms | **20x** |
| Reminders create | ~700ms | ~100ms | **7x** |

*Note: Estimates based on iMessage benchmarks. Actual gains depend on API latency.*

---

## Risk Mitigation

### Risk 1: OAuth Token Complexity
**Concern**: Sharing OAuth tokens between services may cause scope conflicts.
**Mitigation**: Request combined scopes upfront (`gmail.readonly`, `gmail.send`, `calendar.events`).

### Risk 2: Daemon Stability
**Concern**: Single daemon crash affects all services.
**Mitigation**: Implement watchdog process with automatic restart. Log crashes for debugging.

### Risk 3: Migration Disruption
**Concern**: Breaking existing workflows during migration.
**Mitigation**: Keep MCP servers running in parallel until daemon is validated. Gradual deprecation.

### Risk 4: Apple Sandbox Restrictions
**Concern**: EventKit/AppleScript may behave differently in daemon context.
**Mitigation**: Test thoroughly. Fall back to subprocess AppleScript if needed.

---

## Success Criteria

1. **Performance**: <10ms spawn overhead for all services (currently 35-100ms)
2. **Reliability**: 99.9% uptime with automatic recovery
3. **Simplicity**: Single socket, single process, unified CLI
4. **Observability**: Structured logging, health checks, metrics
5. **Maintainability**: Shared Rust core, DRY Python backends

---

## Files to Create/Modify

### New Files

| Path | Purpose |
|------|---------|
| `Texting/gateway/wolfies-client/Cargo.toml` | Workspace root |
| `Texting/gateway/wolfies-client/crates/wolfies-core/` | Shared Rust library |
| `Texting/gateway/wolfies-client/crates/wolfies-gmail/` | Gmail commands |
| `Texting/gateway/wolfies-client/crates/wolfies-calendar/` | Calendar commands |
| `Texting/gateway/wolfies-client/crates/wolfies-reminders/` | Reminders commands |
| `Texting/gateway/wolfies_daemon.py` | Unified Python daemon |
| `Texting/gateway/backends/gmail_backend.py` | Gmail service backend |
| `Texting/gateway/backends/calendar_backend.py` | Calendar service backend |
| `Texting/gateway/backends/reminders_backend.py` | Reminders service backend |

### Modified Files

| Path | Changes |
|------|---------|
| `Texting/gateway/rust_client/` | Refactor to workspace structure |
| `Texting/gateway/imessage_daemon.py` | Extract to backend class |
| `src/integrations/gmail/server.py` | Archive after migration |
| `src/integrations/google_calendar/server.py` | Archive after migration |
| `Reminders/mcp_server/server.py` | Archive after migration |

---

## Change Log

| Date | Change |
|------|--------|
| 01/08/2026 02:30 AM PST | Initial plan created |


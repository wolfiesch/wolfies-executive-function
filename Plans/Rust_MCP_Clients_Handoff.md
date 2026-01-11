# Rust MCP Client Refactor - Handoff Prompt

**For:** Fresh Claude agent
**Project:** LIFE-PLANNER
**Date:** 01/08/2026

---

## Context

We successfully built a high-performance iMessage CLI using the **Rust client + Python daemon** pattern, achieving **19x faster performance** than the original MCP-based approach (40ms vs 763ms per operation).

The architecture:
- **Rust CLI** (`wolfies-imessage`): Fast ~3ms spawn, sends requests via Unix socket
- **Python daemon** (`imessage_daemon.py`): Warm process handling iMessage operations
- **Protocol**: JSON-RPC over Unix socket at `~/.wolfies-imessage/daemon.sock`

This is now distributed via Homebrew (`brew install wolfiesch/executive-function/wolfies-imessage`).

---

## Task: Extend Pattern to Other MCP Servers

Three Python MCP servers currently exist that could benefit from Rust CLI wrappers:

| Module | Current Location | MCP Tools |
|--------|-----------------|-----------|
| **Gmail** | `src/integrations/gmail/server.py` | list_emails, get_email, search_emails, send_email, get_unread_count |
| **Calendar** | `src/integrations/google_calendar/server.py` | list_events, get_event, create_event, find_free_time |
| **Reminders** | `Reminders/mcp_server/server.py` | create_reminder, list_reminders, complete_reminder, delete_reminder, list_reminder_lists |

---

## Reference Implementation

Study these files to understand the pattern:

### Rust Client (shared library + iMessage binary)
```
Texting/gateway/wolfies-client/
├── Cargo.toml                    # Workspace definition
├── crates/
│   ├── wolfies-core/             # Shared library
│   │   ├── src/lib.rs           # Protocol, client, response types
│   │   └── Cargo.toml
│   └── wolfies-imessage/         # iMessage-specific binary
│       ├── src/main.rs          # CLI entry point
│       └── Cargo.toml
```

### Python Daemon
```
Texting/gateway/
├── imessage_daemon.py           # Unix socket server, handles JSON-RPC
├── imessage_daemon_client.py    # Python client for testing
└── output_utils.py              # Shared output formatting
```

### Key Files to Read
1. `Texting/gateway/wolfies-client/crates/wolfies-core/src/lib.rs` - Protocol definition
2. `Texting/gateway/wolfies-client/crates/wolfies-imessage/src/main.rs` - CLI structure
3. `Texting/gateway/imessage_daemon.py` - Daemon architecture
4. `Plans/Rust_Gateway_Framework_2026-01-08.md` - Original implementation plan

---

## Benchmarking Approach

We used a normalized workload benchmark to compare implementations:

### Benchmark Script
`Texting/benchmarks/normalized_workload_benchmarks.py`

### Workloads Tested
1. **recent** - Get recent messages (light read)
2. **unread** - Get unread messages (light read)
3. **find** - Search messages (medium read)
4. **send** - Send message (write operation)
5. **contacts** - List contacts (metadata read)

### Metrics Captured
- Cold start time (first request)
- Warm request time (subsequent requests)
- P50, P95, P99 latencies
- Memory usage
- Throughput (requests/second)

### Before/After Comparison
Create baseline benchmarks BEFORE implementing Rust clients, then compare after.

---

## Proposed Phases

### Phase 1: Gmail Rust Client
1. Create `wolfies-gmail` crate in workspace
2. Convert `gmail/server.py` to daemon mode (Unix socket)
3. Implement Rust CLI with subcommands: `list`, `search`, `read`, `send`, `unread`
4. Benchmark before/after
5. Update Homebrew formula

### Phase 2: Calendar Rust Client
1. Create `wolfies-calendar` crate
2. Convert `google_calendar/server.py` to daemon mode
3. Implement Rust CLI: `list`, `get`, `create`, `free-time`
4. Benchmark before/after
5. Update Homebrew formula

### Phase 3: Reminders Rust Client
1. Create `wolfies-reminders` crate
2. Convert `Reminders/mcp_server/server.py` to daemon mode
3. Implement Rust CLI: `create`, `list`, `complete`, `delete`, `lists`
4. Benchmark before/after
5. Update Homebrew formula

---

## Questions to Consider

1. **Is Rust worth it for these?** iMessage benefited because it's used for quick lookups (`unread`, `recent`). Gmail/Calendar/Reminders are primarily MCP servers for Claude Code - direct CLI use is less common. Benchmark first to see if there's a real bottleneck.

2. **Daemon vs Direct?** iMessage uses a daemon because the database reads are expensive to initialize. Gmail/Calendar use OAuth which has its own warm-up cost. Profile to see where time is spent.

3. **Shared credentials?** Gmail and Calendar could share OAuth tokens. Consider a unified Google daemon.

---

## Quick Start Commands

```bash
# Read the iMessage implementation
cat Plans/Rust_Gateway_Framework_2026-01-08.md

# Check the Rust workspace structure
ls -la Texting/gateway/wolfies-client/crates/

# Read the core library
cat Texting/gateway/wolfies-client/crates/wolfies-core/src/lib.rs

# Run existing benchmarks
python3 -m Texting.benchmarks.normalized_workload_benchmarks --help

# Check current MCP servers
cat src/integrations/gmail/server.py | head -100
cat src/integrations/google_calendar/server.py | head -100
cat Reminders/mcp_server/server.py | head -100
```

---

## Success Criteria

- [ ] Baseline benchmarks for each MCP server
- [ ] Rust CLI achieving <50ms for common operations
- [ ] Homebrew formulas updated with Rust binaries
- [ ] Before/after performance comparison documented
- [ ] All existing functionality preserved

---

## Notes

- The Homebrew tap is at `wolfiesch/homebrew-executive-function`
- Release workflow at `.github/workflows/release.yml` handles multi-module builds
- Current version is v0.2.0

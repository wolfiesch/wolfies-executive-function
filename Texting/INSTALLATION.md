# Wolfie's iMessage Gateway - Installation

19× faster than MCP alternatives (40ms vs 763ms average)

## Prerequisites

- macOS 12+ (Monterey or later)
- Python 3.9+
- Claude Code CLI

## Quick Install (2 minutes)

### 1. Install via pip

```bash
pip install wolfies-imessage-gateway

# Optional: enable semantic search / RAG features
pip install 'wolfies-imessage-gateway[rag]'
```

### 2. Grant Full Disk Access

**Required:** Terminal needs access to iMessage database

1. Open System Settings → Privacy & Security → Full Disk Access
2. Click the + button
3. Add Terminal.app (or your terminal emulator)
4. Restart Terminal

### 3. Test Installation

```bash
wolfies-imessage --version
wolfies-imessage recent --limit 5
```

### 4. Register with Claude Code

```bash
claude skills add wolfies-imessage-gateway
```

## Verification

```bash
# Should show recent messages
wolfies-imessage recent --limit 5

# Check skill registration
claude skills list | grep wolfies-imessage
```

## Troubleshooting

### "Permission denied" errors
→ Grant Full Disk Access (see step 2 above)

### "Database not found"
→ iMessage database location: `~/Library/Messages/chat.db`
→ Verify file exists: `ls ~/Library/Messages/chat.db`

### Skill not loading
```bash
claude skills reload
```

## Uninstallation

```bash
pip uninstall wolfies-imessage-gateway
claude skills remove wolfies-imessage-gateway
```

## Performance

Based on benchmarks vs 10 competitors:
- **Startup:** 83ms (fastest)
- **Recent messages:** 88ms (19x faster than wyattjoh/imessage-mcp)
- **Search:** 109ms (8.8x faster)
- **Groups:** 110ms (8.8x faster)

See `PERFORMANCE_COMPARISON.md` for full benchmarks.

## Commands

Full command reference:

```bash
# Messaging
wolfies-imessage send "John" "Hello!"
wolfies-imessage send-by-phone "+14155551234" "Hi!"

# Reading
wolfies-imessage recent --limit 10
wolfies-imessage messages "John" --limit 20
wolfies-imessage find "Sarah" --query "meeting"
wolfies-imessage unread

# Groups
wolfies-imessage groups
wolfies-imessage group-messages "Family Chat" --limit 10

# Analytics
wolfies-imessage analytics "John" --days 30
wolfies-imessage followup --days 7

# Semantic Search (RAG)
wolfies-imessage index --source=imessage --days 30
wolfies-imessage search "dinner plans with Sarah"
wolfies-imessage ask "What did John say about the project?"
```

Run `wolfies-imessage --help` for complete command list.

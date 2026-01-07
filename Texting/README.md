# iMessage Gateway CLI

![macOS](https://img.shields.io/badge/macOS-only-blue?logo=apple)
![Python](https://img.shields.io/badge/Python-3.9+-green?logo=python)
![PyPI](https://img.shields.io/pypi/v/wolfies-imessage-gateway)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-purple)

**The fastest iMessage integration for Claude Code.** Direct CLI architecture delivers 19x faster performance than MCP-based alternatives.

## Features

- **Send Messages**: Send iMessages using natural language
- **Read Messages**: Retrieve message history with contacts or phone numbers
- **Smart Contact Lookup**: Fuzzy matching for contact names
- **Semantic Search (RAG)**: AI-powered search across iMessages, SuperWhisper, Notes
- **Follow-up Detection**: Find conversations needing response
- **Group Chats**: List and read group conversations
- **Analytics**: Conversation patterns and statistics

## Performance

| Operation | Gateway CLI | MCP-based | Speedup |
|-----------|-------------|-----------|---------|
| List contacts | 40ms | ~763ms | **19x** |
| Find messages | 43ms | ~763ms | **18x** |
| Unread messages | 44ms | ~763ms | **17x** |
| Groups | 61ms | ~763ms | **12x** |
| Semantic search | 150ms | ~900ms | **6x** |

## Requirements

- **macOS** (required - iMessage is macOS only)
- **Python 3.9+**
- **Full Disk Access** permission (for reading message history)

## Installation

**See [INSTALLATION.md](./INSTALLATION.md) for detailed setup instructions.**

### Quick Install (2 minutes)

```bash
# Install the package
pip install wolfies-imessage-gateway

# Optional: enable semantic search / RAG features
pip install 'wolfies-imessage-gateway[rag]'

# Verify installation
wolfies-imessage --version

# Test it
wolfies-imessage recent --limit 5
```

### Grant Full Disk Access

Terminal needs access to read your iMessage database:

1. Open **System Settings → Privacy & Security → Full Disk Access**
2. Click the **+** button
3. Add **Terminal.app** (or your terminal emulator)
4. Restart Terminal

### Basic Usage

```bash
# Check recent messages
wolfies-imessage recent --limit 10

# Send a message
wolfies-imessage send "John" "Hey, are you free for coffee?"

# View all commands
wolfies-imessage --help
```

## Command Reference

### Messaging

```bash
# Send to contact
python3 gateway/imessage_client.py send "John" "Hello!"

# Send to phone number directly
python3 gateway/imessage_client.py send-by-phone "+14155551234" "Hi there!"

# Add a new contact
python3 gateway/imessage_client.py add-contact "Jane Doe" "+14155559876"
```

### Reading

```bash
# Messages with a contact
python3 gateway/imessage_client.py messages "John" --limit 20 --json

# Find messages (keyword search)
python3 gateway/imessage_client.py find "John" --query "meeting" --json

# Fast global text search across all messages (no embeddings)
python3 gateway/imessage_client.py text-search "meeting" --limit 50 --json

# Canonical bundle (single call for common LLM reads)
python3 gateway/imessage_client.py bundle --json --compact --query "http" --search-limit 20

# Recent across all contacts
python3 gateway/imessage_client.py recent --limit 50 --json

# Unread messages
python3 gateway/imessage_client.py unread --json

# Recent phone handles
python3 gateway/imessage_client.py handles --days 30 --json

# Messages from unknown senders
python3 gateway/imessage_client.py unknown --days 7 --json

# Attachments
python3 gateway/imessage_client.py attachments "John" --json

# Voice messages
python3 gateway/imessage_client.py voice --json

# Links shared
python3 gateway/imessage_client.py links --days 30 --json

# Message thread
python3 gateway/imessage_client.py thread "<message-guid>" --json

# Scheduled messages
python3 gateway/imessage_client.py scheduled --json

# Conversation summary
python3 gateway/imessage_client.py summary "John" --days 7 --json
```

### LLM-Friendly Output Controls

For most read commands that support `--json`, you can reduce token cost with:

```bash
# Minified JSON + fewer fields
python3 gateway/imessage_client.py unread --json --compact

# LLM-minimal preset (compact + date/phone/is_from_me/text, truncated)
python3 gateway/imessage_client.py bundle --json --minimal --query "http"

# Truncate large text fields
python3 gateway/imessage_client.py text-search "http" --json --compact --max-text-chars 120

# Choose exact fields
python3 gateway/imessage_client.py recent --json --fields date,phone,text
```

### Groups

```bash
# List group chats
python3 gateway/imessage_client.py groups --json

# Messages from a group
python3 gateway/imessage_client.py group-messages --group-id "chat123456" --json
```

### Analytics

```bash
# Conversation analytics
python3 gateway/imessage_client.py analytics "John" --days 30 --json

# Follow-ups needed
python3 gateway/imessage_client.py followup --days 7 --json

# Reactions
python3 gateway/imessage_client.py reactions "John" --json
```

### Contacts

```bash
# List all contacts
python3 gateway/imessage_client.py contacts --json
```

### Semantic Search / RAG

```bash
# Optional dependencies required:
#   pip install 'wolfies-imessage-gateway[rag]'
#
# Index iMessages for semantic search
python3 gateway/imessage_client.py index --source=imessage --days 30

# Index SuperWhisper transcriptions
python3 gateway/imessage_client.py index --source=superwhisper

# Index Notes
python3 gateway/imessage_client.py index --source=notes

# Index all local sources
python3 gateway/imessage_client.py index --source=local

# Semantic search
python3 gateway/imessage_client.py search "dinner plans with Sarah" --json

# AI-formatted context
python3 gateway/imessage_client.py ask "What restaurant did Sarah recommend?"

# Knowledge base stats
python3 gateway/imessage_client.py stats --json

# List available/indexed sources
python3 gateway/imessage_client.py sources --json

# Clear indexed data
python3 gateway/imessage_client.py clear --source=imessage --force
```

## Architecture

```
Messages.db (SQLite) ←─ ~/Library/Messages/chat.db
        ↓
MessagesInterface ────→ SQLite queries (read)
        │                AppleScript → Messages.app (send)
        ↓
ContactsManager ──────→ config/contacts.json (fuzzy matching)
        ↓
Gateway CLI ──────────→ gateway/imessage_client.py
        ↓
Claude Code ──────────→ Bash tool calls
```

### Why Gateway CLI?

The Gateway CLI architecture bypasses MCP framework overhead entirely:

- **Direct execution**: Python script runs immediately, no JSON-RPC initialization
- **No session startup**: MCP servers have ~700-800ms cold start per session
- **Smaller footprint**: No MCP SDK dependency, simpler codebase
- **Same reliability**: Uses identical `MessagesInterface` code for all operations

## Claude Code Integration

### Using the Skill

The `imessage-gateway` skill provides natural language access:

```
/imessage-gateway unread
/imessage-gateway send John "Running late!"
/imessage-gateway search "meeting next week"
```

### Bash Pre-approval

Ensure your settings include:
```
Bash(python3:*::*)
```

## Configuration

### Contact Format

Contacts are stored in `config/contacts.json`:

```json
{
  "contacts": [
    {
      "name": "John Doe",
      "phone": "14155551234",
      "relationship_type": "friend",
      "notes": "Optional notes"
    }
  ]
}
```

Phone numbers can be in any format - they're normalized automatically.

## Troubleshooting

### "Contact not found"
- Run `python3 scripts/sync_contacts.py` to sync contacts
- Check `config/contacts.json` exists and has contacts
- Try partial names (e.g., "John" instead of "John Doe")

### "Permission denied" reading messages
- Grant Full Disk Access to Terminal/Python
- Restart Terminal after granting permission
- Verify: `ls ~/Library/Messages/chat.db`

### Messages show "[message content not available]"
- Some older messages use a different format
- Attachment-only messages don't have text content
- This is normal for some message types

## Development

```bash
# Run tests
pytest tests/ -v

# Run performance benchmarks
python3 benchmarks/run_benchmarks.py

# Sync contacts
python3 scripts/sync_contacts.py
```

## Privacy & Security

- All data stays local on your Mac
- No cloud services for core functionality
- Contacts file is gitignored by default
- Message history accessed read-only
- Optional OpenAI API for semantic search embeddings

## MCP Server (Archived)

The MCP server has been archived in `mcp_server_archive/`. See `mcp_server_archive/ARCHIVED.md` for restoration instructions if needed.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

*Built for use with [Claude Code](https://claude.ai/code)*

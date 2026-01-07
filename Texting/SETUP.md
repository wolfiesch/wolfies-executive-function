# Setup Guide - iMessage Gateway CLI

This guide sets up the **Gateway CLI** (the default iMessage integration). The legacy MCP server is archived and only needed if you explicitly want MCP-based tools.

## Prerequisites

- macOS (required for iMessage)
- Python 3.9 or higher
- iMessage configured and working
- Full Disk Access permission (for reading message history)

## Step 1: Install Dependencies

```bash
cd Texting
pip install -r requirements.txt
```

## Step 2: Configure Contacts

Recommended: sync from macOS Contacts.

```bash
python3 scripts/sync_contacts.py
```

Or manual setup:

```bash
cp config/contacts.example.json config/contacts.json
```

Edit `config/contacts.json`:

```json
{
  "contacts": [
    {
      "name": "John Doe",
      "phone": "+14155551234",
      "relationship_type": "friend",
      "notes": "Optional notes"
    }
  ]
}
```

## Step 3: Grant macOS Permissions

### Full Disk Access (read message history)

1. System Settings -> Privacy & Security -> Full Disk Access
2. Add Terminal.app (or your Python interpreter)
3. Restart Terminal after granting access

### Automation (send messages)

Automation permission is requested on the first send. Approve when prompted.

## Step 4: Verify the Gateway CLI

```bash
# List contacts
python3 gateway/imessage_client.py contacts --json

# Check unread messages
python3 gateway/imessage_client.py unread --json

# Send a test message
python3 gateway/imessage_client.py send "John" "Testing iMessage Gateway!"
```

## Troubleshooting

### "Contact not found"
- Run `python3 scripts/sync_contacts.py`
- Verify `config/contacts.json` exists
- Try partial names ("John" vs "John Doe")

### "Permission denied" accessing Messages database
- Grant Full Disk Access (Step 3)
- Restart Terminal/Claude Code
- Verify: `ls ~/Library/Messages/chat.db`

### AppleScript errors when sending
- Ensure Messages.app is running
- Approve Automation permissions when prompted
- Try sending a manual message in Messages.app

## Legacy MCP Server (Archived)

If you explicitly need the MCP server, see:
- `Texting/mcp_server_archive/ARCHIVED.md`

## Next Steps

- See command reference in `Texting/README.md`
- Gateway CLI details in `Texting/gateway/README.md`

# Gmail MCP Quick Start Guide

## Installation (5 minutes)

### 1. Run Setup Script
```bash
cd src/integrations/gmail
./setup.sh
```

### 2. Get Google Credentials

Before running setup.sh, get credentials:

1. Visit [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Desktop app)
3. Download as `credentials.json`
4. Save to: `config/google_credentials/credentials.json`

Or share existing Calendar credentials:
- If you already have Calendar integration, reuse the same `credentials.json`
- Gmail will create its own token file

### 3. Register with Claude Code
```bash
claude mcp add -t stdio gmail -- python3 src/integrations/gmail/server.py
```

### 4. Verify
```bash
claude mcp list
# Should show: gmail (Connected)
```

## First Use

1. In Claude Code, say: **"Check my email"**
2. Browser opens for OAuth authorization
3. Sign in and grant permissions
4. Token saved automatically
5. Done! Gmail tools now available

## Quick Commands

| Command | What It Does |
|---------|-------------|
| "Check my email" | List 10 most recent emails |
| "Show unread emails" | List only unread |
| "How many unread emails?" | Get count |
| "Show emails from john@example.com" | Filter by sender |
| "Search emails about project" | Search by keyword |
| "Send email to sarah@example.com" | Compose and send |
| "Show me email ID abc123..." | Get full email content |

## Tools Available

1. **list_emails** - Browse inbox with filters
2. **get_email** - Read full email by ID
3. **search_emails** - Gmail search syntax
4. **send_email** - Send plain text emails
5. **get_unread_count** - Quick unread check

## Troubleshooting

### "Gmail client not initialized"
-> Missing credentials.json. Download from Google Cloud Console.

### "Permission denied"
-> Delete `gmail_token.pickle` and re-authenticate.

### Server not showing
-> Check: `claude mcp list` and re-register if needed.

### Import errors
-> Install dependencies: `pip install -r requirements.txt`

## Files Created

```
src/integrations/gmail/
|-- server.py              # MCP server
|-- gmail_client.py        # Gmail API wrapper
|-- __init__.py
|-- requirements.txt       # Dependencies
|-- README.md             # Full documentation
|-- QUICKSTART.md         # This file
|-- setup.sh              # Automated setup
`-- test_gmail.py         # Test script

config/google_credentials/
|-- credentials.json      # OAuth client (you provide)
`-- gmail_token.pickle    # Auto-generated token
```

## Advanced Usage

### Search Syntax
```
from:john@example.com
subject:meeting
has:attachment
after:2024/12/01
is:unread
label:important
```

### Combine Filters
```
"Search: from:john subject:project after:2024/12/01"
```

### Automation Examples
```
"Summarize my unread emails from today"
"Find all emails about the deadline"
"Show important emails I haven't responded to"
```

## Security Notes

- Credentials stored locally in `config/google_credentials/`
- OAuth 2.0 authentication (industry standard)
- No email content logged to disk
- Token auto-refreshes when expired

## Next Steps

- Test with: `python test_gmail.py`
- Read full docs: `README.md`
- Integrate with Life Planner CRM and tasks

## Support

Check logs: `logs/gmail.log`

---

**Setup Time:** 5 minutes
**Dependencies:** Python 3.9+, Google Cloud account
**Status:** Production ready

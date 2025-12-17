# Gmail MCP Integration

Gmail MCP server for the Life Planner project. Provides email management capabilities through the Model Context Protocol.

## Features

- **List Emails**: Browse recent emails with flexible filtering (unread, sender, date range, labels)
- **Get Email**: Retrieve full email content including body, headers, and metadata
- **Search Emails**: Use Gmail's powerful search syntax to find specific emails
- **Send Email**: Send plain text emails directly from Claude
- **Unread Count**: Quick check of unread email count

## Setup

### 1. Install Dependencies

```bash
cd /Users/wolfgangschoenberger/LIFE-PLANNER/src/integrations/gmail
pip install -r requirements.txt
```

### 2. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as application type
   - Name it "Life Planner Gmail"
   - Download the credentials JSON file

### 3. Install Credentials

```bash
# Create credentials directory
mkdir -p /Users/wolfgangschoenberger/LIFE-PLANNER/config/google_credentials

# Copy downloaded credentials
cp ~/Downloads/client_secret_*.json /Users/wolfgangschoenberger/LIFE-PLANNER/config/google_credentials/credentials.json
```

### 4. Register MCP Server with Claude Code

```bash
claude mcp add -t stdio gmail -- python3 /Users/wolfgangschoenberger/LIFE-PLANNER/src/integrations/gmail/server.py
```

### 5. First Run - OAuth Flow

The first time you use the Gmail tools, you'll be prompted to authorize:

1. Browser window will open automatically
2. Sign in with your Google account
3. Grant permissions for Gmail access
4. Token will be saved to `config/google_credentials/gmail_token.pickle`

### 6. Verify Setup

```bash
# Check MCP server status
claude mcp list

# Should show:
# ✓ gmail (Connected)
```

## Usage Examples

### Check Recent Emails
```
"Check my email"
"Show me my 20 most recent emails"
"List unread emails"
```

### Filter Emails
```
"Show emails from john@example.com"
"List unread emails from this week"
"Show me emails in my INBOX"
```

### Search Emails
```
"Search for emails about the project"
"Find emails with attachments from Sarah"
"Search emails with subject: meeting"
```

### Read Full Email
```
"Show me the full email with ID 18c5f8a..."
"Get details of that email"
```

### Send Email
```
"Send an email to sarah@example.com about tomorrow's meeting"
"Draft and send a thank you email to john@example.com"
```

### Check Unread Count
```
"How many unread emails do I have?"
"Check my unread count"
```

## Gmail Search Syntax

The `search_emails` tool supports full Gmail search syntax:

- `from:john@example.com` - Emails from specific sender
- `to:sarah@example.com` - Emails to specific recipient
- `subject:meeting` - Subject contains "meeting"
- `has:attachment` - Has attachments
- `is:unread` - Unread emails
- `is:starred` - Starred emails
- `after:2024/01/01` - After specific date
- `before:2024/12/31` - Before specific date
- `label:important` - Has specific label

Combine multiple criteria:
```
"Search: from:john@example.com subject:project after:2024/12/01"
```

## File Structure

```
src/integrations/gmail/
├── __init__.py           # Package initialization
├── server.py             # MCP server implementation
├── gmail_client.py       # Gmail API wrapper
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

### Credentials Location
- OAuth credentials: `config/google_credentials/credentials.json`
- Saved token: `config/google_credentials/gmail_token.pickle`

### Logs
- Server logs: `logs/gmail.log`

### Shared with Calendar Integration
If you've already set up the Calendar MCP integration, you can share the same `credentials.json`. The Gmail server will use its own token file (`gmail_token.pickle`) but can authenticate with the same OAuth client.

## API Scopes

The server requests these Gmail API scopes:
- `gmail.readonly` - Read emails and settings
- `gmail.send` - Send emails
- `gmail.modify` - Modify labels (mark as read, etc.)

## Troubleshooting

### "Gmail client not initialized"
**Cause:** Credentials not found or invalid

**Solution:**
1. Verify `config/google_credentials/credentials.json` exists
2. Check file is valid JSON
3. Re-download from Google Cloud Console if needed

### "Permission denied" or "Insufficient scopes"
**Cause:** Token doesn't have required permissions

**Solution:**
1. Delete `config/google_credentials/gmail_token.pickle`
2. Re-run OAuth flow with correct scopes
3. Ensure Gmail API is enabled in Cloud Console

### "Token expired"
**Cause:** OAuth token needs refresh

**Solution:** Token should auto-refresh. If it doesn't:
1. Delete `gmail_token.pickle`
2. Re-authenticate

### Server not appearing in `claude mcp list`
**Cause:** MCP server not registered correctly

**Solution:**
```bash
# Remove and re-add
claude mcp remove gmail
claude mcp add -t stdio gmail -- python3 /Users/wolfgangschoenberger/LIFE-PLANNER/src/integrations/gmail/server.py
```

### Import errors
**Cause:** Dependencies not installed

**Solution:**
```bash
pip install -r requirements.txt
```

## Security & Privacy

- **Local storage:** All credentials and tokens stored locally in `config/google_credentials/`
- **No cloud sync:** Email data not sent to external servers (except Google's Gmail API)
- **Minimal logging:** Only metadata logged, no email content written to logs
- **OAuth 2.0:** Industry-standard authentication
- **Token security:** Token files should have restricted permissions (600)

### Recommended Security Practices

```bash
# Set restrictive permissions on credentials
chmod 600 /Users/wolfgangschoenberger/LIFE-PLANNER/config/google_credentials/credentials.json
chmod 600 /Users/wolfgangschoenberger/LIFE-PLANNER/config/google_credentials/gmail_token.pickle

# Add to .gitignore
echo "config/google_credentials/*.json" >> .gitignore
echo "config/google_credentials/*.pickle" >> .gitignore
```

## Limitations

- **Plain text only:** HTML emails displayed as-is (no rendering)
- **No attachments:** Current version doesn't download/handle attachments
- **Body truncation:** Very long emails (>5000 chars) truncated in responses
- **Rate limits:** Subject to Google's API quotas (default: 1 billion quota units/day)

## Future Enhancements

- [ ] Attachment download and preview
- [ ] HTML email rendering
- [ ] Draft management
- [ ] Label management (create/modify)
- [ ] Batch operations
- [ ] Email templates
- [ ] Integration with Life Planner CRM (auto-log interactions)
- [ ] Smart categorization and prioritization
- [ ] Calendar event extraction from emails

## Integration with Life Planner

This Gmail MCP server is part of the larger Life Planner system:

- **Contacts:** Email addresses can link to contacts in CRM database
- **Tasks:** Important emails can trigger task creation
- **Calendar:** Meeting emails can auto-create calendar events
- **Notes:** Email content can be saved to notes database
- **Context:** Email content available for AI agent decision-making

## Support

For issues or questions:
1. Check logs at `logs/gmail.log`
2. Review this README and troubleshooting section
3. Consult Claude Code documentation
4. Check Google's Gmail API documentation

## License

Part of the Life Planner project.

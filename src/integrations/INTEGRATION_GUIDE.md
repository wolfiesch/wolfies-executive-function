# Integration Priority Guide

**Last Updated:** 01/01/2026 07:54 AM PST (via pst-timestamp)

## ⚠️ Critical: Overlapping Integrations

This project has **MULTIPLE integration paths** for the same services. This guide clarifies which integration to use for each service.

## Integration Decision Matrix

| Service | ✅ USE THIS | ❌ DON'T USE THIS | Why |
|---------|-------------|-------------------|-----|
| **Gmail** | **Rube/Composio** (`GMAIL_*` tools) | Local Gmail MCP (`src/integrations/gmail/`) | Rube is already authenticated; local MCP requires Google Cloud setup |
| **Google Calendar** | **Rube/Composio** (`GOOGLECALENDAR_*` tools) | Local Calendar MCP (`src/integrations/google_calendar/`) | Same as Gmail - Rube already configured |
| **Slack** | **Rube/Composio** (`SLACK_*` tools) | N/A | Rube is the only option |
| **Twitter/X** | **Rube/Composio** (`TWITTER_*` tools) | N/A | Rube is the only option |
| **iMessage** | **Local iMessage MCP** (`mcp__imessage-life-planner__*`) | N/A | Local-only, direct macOS integration |
| **Reminders** | **Local Reminders MCP** (`mcp__reminders-life-planner__*`) | N/A | Local-only, direct macOS integration |

## How to Use Rube/Composio

### 1. Search for Tools (first time or to discover)
```python
RUBE_SEARCH_TOOLS(
    queries=[{
        "use_case": "fetch emails from gmail"
    }],
    session={"generate_id": true}
)
```

### 2. Execute Tools
```python
RUBE_MULTI_EXECUTE_TOOL(
    session_id="<from_search_response>",
    tools=[{
        "tool_slug": "GMAIL_FETCH_EMAILS",
        "arguments": {
            "max_results": 20,
            "user_id": "me"
        }
    }],
    sync_response_to_workbench=false,
    memory={}
)
```

## Common Rube Tools

### Gmail
- `GMAIL_FETCH_EMAILS` - Get recent emails (use `max_results`, `user_id`)
- `GMAIL_SEND_EMAIL` - Send email (use `to`, `subject`, `body`)
- `GMAIL_SEARCH_EMAILS` - Search with Gmail syntax (use `query`)
- `GMAIL_GET_EMAIL` - Get full email by ID (use `message_id`)

### Google Calendar
- `GOOGLECALENDAR_LIST_EVENTS` - Get calendar events
- `GOOGLECALENDAR_CREATE_EVENT` - Create new event
- `GOOGLECALENDAR_UPDATE_EVENT` - Modify existing event
- `GOOGLECALENDAR_DELETE_EVENT` - Remove event

### Slack
- `SLACK_SEND_MESSAGE` - Post message (use `channel`, `text`)
- `SLACK_LIST_CHANNELS` - Get all channels
- `SLACK_SEARCH_MESSAGES` - Search messages
- `SLACK_GET_CHANNEL_HISTORY` - Get recent messages

### Twitter/X
- `TWITTER_GET_PROFILE` - Get user profile
- `TWITTER_RECENT_SEARCH` - Search recent tweets
- `TWITTER_POST_TWEET` - Create new tweet
- `TWITTER_GET_USER_TWEETS` - Get tweets from user

## Why Local MCPs Show "Connected" But Don't Work

**The Issue:**
`claude mcp list` shows `✓ Connected` if the MCP server **process starts successfully**. This DOES NOT mean the server is **authenticated** or **configured**.

**Example - Gmail:**
```bash
$ claude mcp list
✓ gmail (Connected)    # ← Process started, but NO credentials!
```

The local Gmail MCP shows "Connected" because:
1. The Python process starts without errors
2. The MCP protocol handshake completes
3. BUT: `credentials.json` is missing, so all tool calls fail

**How to Detect:**
- Check the server's log file (`logs/gmail.log`)
- Look for "client not initialized" errors
- Try using a tool - it will fail with authentication error

## When to Use Local MCPs

Use local MCPs when:
- Service is NOT available via Rube/Composio
- You need specific features not in Rube
- You want complete control over authentication
- Privacy/security requires local-only access

## Troubleshooting Checklist

When a tool "doesn't work":

1. **Is it a local MCP or Rube?**
   - Check `claude mcp list` for server name
   - Local: `gmail`, `google_calendar`, etc.
   - Rube: `rube`

2. **Is Rube available for this service?**
   - Search: `RUBE_SEARCH_TOOLS` with the service name
   - Check: Integration Decision Matrix above

3. **For local MCPs: Check logs**
   - Location: `logs/<service>.log`
   - Look for: "not initialized", "credentials not found"

4. **For Rube: Check connection**
   - Tool: `RUBE_MANAGE_CONNECTIONS`
   - Verify: Account is connected

## Connected Rube Services

Current connections (as of 01/01/2026):
- ✅ Gmail: `wolfgangs2000@gmail.com`
- ✅ Twitter/X: `@wolfiesch`
- (Other services: run `RUBE_MANAGE_CONNECTIONS` to check)

## Future Integration Strategy

**Before adding a new integration:**
1. Check if Rube/Composio supports it (500+ apps)
2. Only build local MCP if:
   - Not in Rube catalog
   - Requires macOS-specific APIs (like iMessage)
   - Privacy/offline requirements

**Avoid duplicate integrations unless there's a clear reason.**

## See Also

- `CLAUDE.md` → Integration Guidelines → MCP Integration Priority
- `src/integrations/gmail/README.md` → Warning banner
- Global `~/.claude/CLAUDE.md` → Rube Integration Patterns

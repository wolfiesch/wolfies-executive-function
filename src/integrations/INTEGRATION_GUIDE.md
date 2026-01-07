# Integration Priority Guide

This project supports both **local MCP servers** (macOS and OAuth-based) and **optional Rube/Composio integrations**. Use this guide to avoid duplicate setup and pick the default path for each service.

## Integration Decision Matrix

| Service | Default | Alternative | Notes |
|---------|-----------|----------------|-------|
| **Gmail** | **Local Gmail MCP** (`mcp__gmail__*`) | Rube/Composio Gmail | Local uses OAuth credentials in `config/google_credentials/`. |
| **Google Calendar** | **Local Calendar MCP** (`mcp__google-calendar__*`) | Rube/Composio Calendar | Configure via `scripts/setup_google_oauth.py`. |
| **Slack** | **Rube/Composio** (`SLACK_*` tools) | N/A | No local integration. |
| **Twitter/X** | **TwitterAPI.io (reads)** + **Rube (writes)** | N/A | See `SocialMedia/skills/twitter-manager/`. |
| **iMessage** | **Local iMessage Gateway CLI** | Archived MCP | See `Texting/README.md` and `Texting/gateway/README.md`. |
| **Reminders** | **Local Reminders MCP** (`mcp__reminders-life-planner__*`) | N/A | macOS-only (EventKit). |

## Local MCP Usage (Gmail + Google Calendar)

### 1. Register MCP servers (once)

```bash
# Gmail
claude mcp add -t stdio gmail -- python3 src/integrations/gmail/server.py

# Google Calendar
claude mcp add -t stdio google-calendar -- \
  python3 src/integrations/google_calendar/server.py
```

### 2. Authenticate

- **Gmail:** run `src/integrations/gmail/setup.sh` (or follow `src/integrations/gmail/README.md`).
- **Google Calendar:** run `python scripts/setup_google_oauth.py`.

### 3. Use MCP tools

Examples:
- Gmail: `mcp__gmail__list_emails`, `mcp__gmail__get_email`, `mcp__gmail__send_email`
- Calendar: `mcp__google-calendar__list_events`, `mcp__google-calendar__create_event`

## Rube/Composio Usage (Optional)

Use Rube when:
- A service has no local MCP and is available via Composio
- You want cloud integrations beyond macOS
- You already have a Composio connection configured

Typical flow:
1. `RUBE_SEARCH_TOOLS` to discover tools
2. `RUBE_MULTI_EXECUTE_TOOL` to execute requests

## Why Local MCPs Show "Connected" But Don't Work

`claude mcp list` shows `Connected` if the MCP server process starts successfully.
This does **not** guarantee OAuth credentials are configured.

**How to detect auth issues:**
- Check logs (e.g., `logs/gmail.log`, `logs/google_calendar.log`)
- Look for "client not initialized" or credentials errors
- Try a tool call; auth failures are explicit

## Troubleshooting Checklist

1. **Is it local MCP or Rube?**
   - Local: `gmail`, `google-calendar`, `reminders-life-planner`
   - Rube: `rube`

2. **Local MCPs:**
   - Confirm credentials in `config/google_credentials/`
   - Check logs under `logs/`

3. **Rube:**
   - Use `RUBE_MANAGE_CONNECTIONS` to verify account connection

## Future Integration Strategy

Before adding a new integration:
1. Check if a local MCP already exists
2. If not, consider Rube/Composio for cloud services
3. Build local MCPs only for macOS-specific or privacy-sensitive integrations

## See Also

- `README.md` -> CLI usage
- `src/integrations/gmail/README.md` -> Gmail local setup
- `src/integrations/google_calendar/README.md` -> Calendar local setup
- `Reminders/README.md` -> Reminders MCP setup
- `Texting/README.md` -> iMessage Gateway CLI

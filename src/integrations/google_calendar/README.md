# Google Calendar MCP Integration

A Model Context Protocol (MCP) server that provides Google Calendar integration for the Life Planner system.

## Features

- List upcoming calendar events with flexible date ranges
- Get detailed information about specific events
- Create new calendar events with attendees and locations
- Find available time slots for scheduling
- Full OAuth2 authentication with automatic token refresh
- Working hours awareness (customizable)
- Multi-calendar support

## Installation

### 1. Install Dependencies

```bash
cd src/integrations/google_calendar/
pip install -r requirements.txt
```

### 2. Set Up Google Calendar API

Run the setup script (from repo root) which will guide you through:
- Creating a Google Cloud Console project
- Enabling the Google Calendar API
- Setting up OAuth2 credentials
- Authenticating with your Google account

```bash
python scripts/setup_google_oauth.py
```

Follow the detailed instructions provided by the script.

### 3. Register MCP Server with Claude Code

```bash
claude mcp add -t stdio google-calendar -- \
  python3 src/integrations/google_calendar/server.py
```

### 4. Restart Claude Code

Restart Claude Code to load the new MCP server.

## Usage

Once set up, you can interact with your Google Calendar through natural language:

### View Schedule
```
"What's on my calendar today?"
"Show my schedule for next week"
"List upcoming events for the next 3 days"
```

### Create Events
```
"Schedule a team meeting tomorrow at 2pm for 1 hour"
"Create an event on Friday at 10am called 'Coffee with Sarah'"
"Block time for deep work on Wednesday from 9am to 11am"
```

### Find Free Time
```
"When am I free for a 30 minute meeting this week?"
"Find time for a 2 hour deep work session"
"Show me available slots for a 45 minute call"
```

### Get Event Details
```
"Show details for event abc123"
"Get more information about that meeting"
```

## MCP Tools

### list_events
List upcoming calendar events.

**Parameters:**
- `days_ahead` (optional, default: 7): Number of days to look ahead
- `max_results` (optional, default: 10): Maximum events to return
- `calendar_id` (optional, default: 'primary'): Calendar ID

### get_event
Get details of a specific event.

**Parameters:**
- `event_id` (required): Google Calendar event ID
- `calendar_id` (optional, default: 'primary'): Calendar ID

### create_event
Create a new calendar event.

**Parameters:**
- `summary` (required): Event title
- `start_time` (required): Start time (ISO 8601 format)
- `end_time` (required): End time (ISO 8601 format)
- `description` (optional): Event description
- `location` (optional): Event location
- `attendees` (optional): List of attendee emails
- `calendar_id` (optional, default: 'primary'): Calendar ID

### find_free_time
Find available time slots.

**Parameters:**
- `duration_minutes` (required): Required duration
- `days_ahead` (optional, default: 7): Days to search
- `working_hours_start` (optional, default: 9): Start hour (0-23)
- `working_hours_end` (optional, default: 17): End hour (0-23)
- `calendar_id` (optional, default: 'primary'): Calendar ID

## Architecture

```
src/integrations/google_calendar/
├── server.py           # MCP server implementation
├── calendar_client.py  # Google Calendar API wrapper
├── requirements.txt    # Python dependencies
├── __init__.py
└── README.md          # This file

config/google_credentials/
├── credentials.json   # OAuth2 client credentials (from Google Cloud Console)
└── token.json        # Access token (auto-generated)

scripts/
└── setup_google_oauth.py  # Setup wizard

logs/
└── google_calendar.log  # Server logs
```

## Configuration

### OAuth2 Credentials

Credentials are stored in `config/google_credentials/`:

- `credentials.json`: OAuth2 client credentials from Google Cloud Console
- `token.json`: Access token (auto-generated and auto-refreshed)

**Security Note:** These files are in .gitignore and should never be committed.

### Calendar Scopes

The server requests the following OAuth scope:
- `https://www.googleapis.com/auth/calendar`: Full calendar access

### Working Hours

Default working hours for `find_free_time`:
- Start: 9:00 AM
- End: 5:00 PM
- Days: Monday - Friday

These can be customized per request using the tool parameters.

## Logging

Logs are written to `logs/google_calendar.log` and include:
- Authentication events
- API requests and responses
- Error messages with stack traces
- Performance metrics

Log level: INFO (can be changed in `server.py`)

## Error Handling

### Authentication Errors
If authentication fails, the server will:
1. Try to refresh the token
2. If refresh fails, prompt for re-authentication
3. Log detailed error information

### API Errors
- Rate limiting: Automatic backoff and retry (handled by Google client library)
- Permission errors: Clear error messages with resolution steps
- Network errors: Retry with exponential backoff

### Time Parsing Errors
- Invalid time formats return helpful error messages
- Supports multiple time formats (ISO 8601, natural language)
- Timezone handling (converts to UTC for API)

## Troubleshooting

### "Service not initialized"
**Cause:** Authentication not completed
**Solution:** Run `python scripts/setup_google_oauth.py`

### "Credentials file not found"
**Cause:** Missing credentials.json
**Solution:** Complete OAuth2 setup (see Installation step 2)

### "Calendar not found"
**Cause:** Invalid calendar_id
**Solution:** Use 'primary' for default calendar, or verify calendar ID

### "Token expired"
**Cause:** Access token expired
**Solution:** Token should auto-refresh; if not, delete token.json and re-authenticate

### "Permission denied"
**Cause:** OAuth scope not granted
**Solution:** Ensure Calendar API scope is included in OAuth consent screen

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/test_calendar_client.py -v

# Integration tests (requires auth)
pytest tests/integration/test_google_calendar.py -v
```

### Manual Testing

```bash
# Start the MCP server directly
python src/integrations/google_calendar/server.py

# In another terminal, test with MCP inspector
npx @modelcontextprotocol/inspector python3 src/integrations/google_calendar/server.py
```

### Debugging

Enable debug logging:
```python
# In server.py, change:
logging.basicConfig(level=logging.DEBUG, ...)
```

Check logs:
```bash
tail -f logs/google_calendar.log
```

## Integration with Life Planner

This MCP server is part of the Life Planner system and integrates with:

- **Task Management**: Schedule time blocks for tasks
- **Daily Planning**: Show calendar in morning routine
- **Meeting Prep**: Surface relevant notes before meetings
- **CRM**: Track meeting attendees in contacts database

See the main Life Planner documentation for full integration details.

## Security and Privacy

- All authentication tokens stored locally
- No data sent to external services (except Google Calendar API)
- Credentials in .gitignore (never committed)
- OAuth2 standard with automatic token refresh
- Read/write access to your calendar only

## High-Performance CLI Alternative

For performance-critical use cases, a CLI gateway with daemon support is available that provides **9x faster** access compared to the MCP server.

### Performance Comparison

| Operation | MCP Server | CLI + Daemon | Speedup |
|-----------|------------|--------------|---------:|
| Today's events | ~1,130ms | ~126ms | **9.0x** |
| Week's events | ~1,028ms | ~115ms | **8.9x** |
| Find 30-min slots | ~1,003ms | ~111ms | **9.0x** |
| Find 60-min slots | ~1,049ms | ~116ms | **9.0x** |

### CLI Usage

```bash
# Basic operations
python3 src/integrations/google_calendar/calendar_cli.py today --json
python3 src/integrations/google_calendar/calendar_cli.py week --json
python3 src/integrations/google_calendar/calendar_cli.py free 30 --json

# With daemon for maximum speed (requires daemon running)
python3 src/integrations/google_calendar/calendar_cli.py --use-daemon today --json
python3 src/integrations/google_calendar/calendar_cli.py --use-daemon week --json
python3 src/integrations/google_calendar/calendar_cli.py --use-daemon free 60 --json
```

### Starting the Daemon

```bash
# Start shared Google daemon (Gmail + Calendar)
python3 src/integrations/google_daemon/server.py start

# Check status
python3 src/integrations/google_daemon/server.py status
```

### When to Use CLI vs MCP

| Use Case | Recommended |
|----------|-------------|
| Integration with Claude Code tools | MCP Server |
| Quick terminal checks | CLI |
| High-frequency operations | CLI + Daemon |
| Scripting/automation | CLI |
| Complex AI workflows | MCP Server |

See `src/integrations/google_daemon/README.md` for full daemon documentation.

## Future Enhancements

Planned features:
- [ ] Multiple calendar support (view/create across calendars)
- [ ] Recurring event support
- [ ] Calendar sync to local Life Planner database
- [ ] Smart scheduling with task priorities
- [ ] Meeting template support
- [ ] Automatic meeting notes creation
- [ ] Integration with email for meeting invites
- [ ] Time zone detection and conversion

## Contributing

When contributing to this integration:
1. Follow existing code style
2. Add docstrings to all functions
3. Update tests for new features
4. Update this README with new tools/features
5. Log significant operations

## License

Part of the Life Planner system. See main project LICENSE.

## Support

For issues or questions:
1. Check logs in `logs/google_calendar.log`
2. Review Google Calendar API documentation
3. Verify OAuth2 setup is complete
4. Create an issue in the main Life Planner repository

---

*Last Updated: 01/08/2026*

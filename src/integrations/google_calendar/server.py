#!/usr/bin/env python3
"""
Google Calendar MCP Server - Calendar integration for Life Planner.

Provides MCP tools for interacting with Google Calendar:
- list_events: List upcoming calendar events
- get_event: Get details of a specific event
- create_event: Create a new calendar event
- find_free_time: Find available time slots

Usage:
    python src/integrations/google_calendar/server.py
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from src.integrations.google_calendar.calendar_client import GoogleCalendarClient

# Configure logging with absolute path
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)  # Ensure log directory exists

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'google_calendar.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration paths
CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"

# Validation constants
MAX_LIST_RESULTS = 500  # Maximum results for list operations
MAX_DAYS_AHEAD = 365  # Maximum days to look ahead
MIN_DURATION_MINUTES = 1  # Minimum duration for events
MAX_DURATION_MINUTES = 1440  # Maximum duration (24 hours)


def validate_positive_int(value, name: str, min_val: int = 1, max_val: int = MAX_LIST_RESULTS) -> tuple[int | None, str | None]:
    """
    Validate that a value is a positive integer within bounds.

    Args:
        value: Value to validate
        name: Parameter name for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Tuple of (validated_value, error_message). If valid, error_message is None.
    """
    if value is None:
        return None, None

    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return None, f"Invalid {name}: must be an integer, got {type(value).__name__}"

    if int_value < min_val:
        return None, f"Invalid {name}: must be at least {min_val}, got {int_value}"

    if int_value > max_val:
        return None, f"Invalid {name}: must be at most {max_val}, got {int_value}"

    return int_value, None


def validate_non_empty_string(value, name: str) -> tuple[str | None, str | None]:
    """
    Validate that a value is a non-empty string.

    Args:
        value: Value to validate
        name: Parameter name for error messages

    Returns:
        Tuple of (validated_value, error_message). If valid, error_message is None.
    """
    if value is None:
        return None, f"Missing required parameter: {name}"

    if not isinstance(value, str):
        return None, f"Invalid {name}: must be a string, got {type(value).__name__}"

    stripped = value.strip()
    if not stripped:
        return None, f"Invalid {name}: cannot be empty"

    return stripped, None


def validate_datetime_string(value, name: str) -> tuple[str | None, str | None]:
    """
    Validate that a value is a parseable datetime string.

    Args:
        value: Value to validate
        name: Parameter name for error messages

    Returns:
        Tuple of (validated_value, error_message). If valid, error_message is None.
    """
    str_value, error = validate_non_empty_string(value, name)
    if error:
        return None, error

    try:
        date_parser.parse(str_value)
    except Exception as e:
        return None, f"Invalid {name}: cannot parse '{str_value}' as datetime. Use ISO 8601 format (e.g., '2025-12-15T14:00:00')"

    return str_value, None


# Initialize server
app = Server("google-calendar")

# Initialize Google Calendar client
calendar_client = GoogleCalendarClient(str(CREDENTIALS_DIR))


def format_event_details(event: dict) -> str:
    """
    Format event details for display.

    Args:
        event: Event dictionary from Google Calendar API

    Returns:
        Formatted event string
    """
    summary = event.get('summary', 'No Title')
    event_id = event.get('id', 'N/A')

    # Parse start/end times
    start = event.get('start', {})
    end = event.get('end', {})

    start_str = start.get('dateTime', start.get('date', 'N/A'))
    end_str = end.get('dateTime', end.get('date', 'N/A'))

    # Try to parse and format nicely
    try:
        if 'T' in start_str:  # DateTime format
            start_dt = date_parser.parse(start_str)
            end_dt = date_parser.parse(end_str)
            time_str = f"{start_dt.strftime('%Y-%m-%d %I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
        else:  # Date only (all-day event)
            time_str = f"{start_str} (All day)"
    except Exception:
        time_str = f"{start_str} - {end_str}"

    # Build description
    parts = [
        f"Event: {summary}",
        f"ID: {event_id}",
        f"Time: {time_str}"
    ]

    if event.get('location'):
        parts.append(f"Location: {event['location']}")

    if event.get('description'):
        desc = event['description']
        if len(desc) > 200:
            desc = desc[:200] + "..."
        parts.append(f"Description: {desc}")

    if event.get('attendees'):
        attendees = [a.get('email', '') for a in event['attendees']]
        parts.append(f"Attendees: {', '.join(attendees)}")

    if event.get('htmlLink'):
        parts.append(f"Link: {event['htmlLink']}")

    return "\n".join(parts)


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available MCP tools.

    Tools:
    - list_events: List upcoming calendar events
    - get_event: Get details of a specific event
    - create_event: Create a new calendar event
    - find_free_time: Find available time slots
    """
    return [
        types.Tool(
            name="list_events",
            description=(
                "List upcoming calendar events within a date range. "
                "Returns events ordered by start time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "number",
                        "description": "Number of days to look ahead (default: 7)",
                        "default": 7
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of events to return (default: 10)",
                        "default": 10
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_event",
            description="Get detailed information about a specific calendar event by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Google Calendar event ID"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    }
                },
                "required": ["event_id"]
            }
        ),
        types.Tool(
            name="create_event",
            description=(
                "Create a new calendar event. Requires summary, start_time, and end_time. "
                "Times should be in ISO 8601 format (e.g., '2025-12-15T14:00:00')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Event title/summary"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Event start time (ISO 8601 format)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Event end time (ISO 8601 format)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional)"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses (optional)"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    }
                },
                "required": ["summary", "start_time", "end_time"]
            }
        ),
        types.Tool(
            name="find_free_time",
            description=(
                "Find available time slots for scheduling. "
                "Searches within working hours (9am-5pm, Mon-Fri by default) "
                "and returns free slots of the requested duration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "duration_minutes": {
                        "type": "number",
                        "description": "Required duration in minutes"
                    },
                    "days_ahead": {
                        "type": "number",
                        "description": "Number of days to search ahead (default: 7)",
                        "default": 7
                    },
                    "working_hours_start": {
                        "type": "number",
                        "description": "Start of working hours (0-23, default: 9)",
                        "default": 9
                    },
                    "working_hours_end": {
                        "type": "number",
                        "description": "End of working hours (0-23, default: 17)",
                        "default": 17
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    }
                },
                "required": ["duration_minutes"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handle MCP tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent responses
    """
    logger.info(f"Tool called: {name} with args: {arguments}")

    try:
        if name == "list_events":
            return await handle_list_events(arguments)
        elif name == "get_event":
            return await handle_get_event(arguments)
        elif name == "create_event":
            return await handle_create_event(arguments)
        elif name == "find_free_time":
            return await handle_find_free_time(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


async def handle_list_events(arguments: dict) -> list[types.TextContent]:
    """
    Handle list_events tool call.

    Args:
        arguments: {"days_ahead": int, "max_results": int, "calendar_id": str}

    Returns:
        List of upcoming events
    """
    # Validate days_ahead
    days_ahead_raw = arguments.get("days_ahead", 7)
    days_ahead, error = validate_positive_int(days_ahead_raw, "days_ahead", max_val=MAX_DAYS_AHEAD)
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]
    if days_ahead is None:
        days_ahead = 7

    # Validate max_results
    max_results_raw = arguments.get("max_results", 10)
    max_results, error = validate_positive_int(max_results_raw, "max_results", max_val=MAX_LIST_RESULTS)
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]
    if max_results is None:
        max_results = 10

    calendar_id = arguments.get("calendar_id", "primary")

    # Calculate time range
    time_min = datetime.now(timezone.utc)
    time_max = time_min + timedelta(days=days_ahead)

    # Get events
    events = calendar_client.list_events(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results
    )

    if not events:
        return [
            types.TextContent(
                type="text",
                text=f"No upcoming events found in the next {days_ahead} days."
            )
        ]

    # Format response
    response_lines = [
        f"Upcoming Events (Next {days_ahead} Days):",
        f"Found {len(events)} event(s)",
        ""
    ]

    for event in events:
        response_lines.append(format_event_details(event))
        response_lines.append("")  # Blank line between events

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def handle_get_event(arguments: dict) -> list[types.TextContent]:
    """
    Handle get_event tool call.

    Args:
        arguments: {"event_id": str, "calendar_id": str}

    Returns:
        Event details
    """
    # Validate event_id
    event_id, error = validate_non_empty_string(arguments.get("event_id"), "event_id")
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]

    calendar_id = arguments.get("calendar_id", "primary")

    # Get event
    event = calendar_client.get_event(event_id, calendar_id)

    if not event:
        return [
            types.TextContent(
                type="text",
                text=f"Event not found: {event_id}"
            )
        ]

    # Format response
    response = format_event_details(event)

    return [
        types.TextContent(
            type="text",
            text=response
        )
    ]


async def handle_create_event(arguments: dict) -> list[types.TextContent]:
    """
    Handle create_event tool call.

    Args:
        arguments: {
            "summary": str,
            "start_time": str,
            "end_time": str,
            "description": str (optional),
            "location": str (optional),
            "attendees": list (optional),
            "calendar_id": str
        }

    Returns:
        Created event details
    """
    # Validate summary (title)
    summary, error = validate_non_empty_string(arguments.get("summary"), "summary")
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]

    # Validate start_time
    start_time_str, error = validate_datetime_string(arguments.get("start_time"), "start_time")
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]

    # Validate end_time
    end_time_str, error = validate_datetime_string(arguments.get("end_time"), "end_time")
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]

    description = arguments.get("description")
    location = arguments.get("location")
    attendees = arguments.get("attendees")
    calendar_id = arguments.get("calendar_id", "primary")

    # Parse times
    try:
        start_time = date_parser.parse(start_time_str)
        end_time = date_parser.parse(end_time_str)
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error parsing time: {e}\n\nPlease use ISO 8601 format (e.g., '2025-12-15T14:00:00')"
            )
        ]

    # Validate times
    if end_time <= start_time:
        return [
            types.TextContent(
                type="text",
                text="Error: End time must be after start time"
            )
        ]

    # Create event
    event = calendar_client.create_event(
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location,
        attendees=attendees,
        calendar_id=calendar_id
    )

    if not event:
        return [
            types.TextContent(
                type="text",
                text="Failed to create event. Check logs for details."
            )
        ]

    # Format response
    response_lines = [
        "Event created successfully!",
        "",
        format_event_details(event)
    ]

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def handle_find_free_time(arguments: dict) -> list[types.TextContent]:
    """
    Handle find_free_time tool call.

    Args:
        arguments: {
            "duration_minutes": int,
            "days_ahead": int,
            "working_hours_start": int,
            "working_hours_end": int,
            "calendar_id": str
        }

    Returns:
        List of available time slots
    """
    # Validate duration_minutes (required)
    duration_minutes_raw = arguments.get("duration_minutes")
    if duration_minutes_raw is None:
        return [types.TextContent(type="text", text="Validation error: Missing required parameter: duration_minutes")]

    duration_minutes, error = validate_positive_int(
        duration_minutes_raw, "duration_minutes",
        min_val=MIN_DURATION_MINUTES, max_val=MAX_DURATION_MINUTES
    )
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]

    # Validate days_ahead
    days_ahead_raw = arguments.get("days_ahead", 7)
    days_ahead, error = validate_positive_int(days_ahead_raw, "days_ahead", max_val=MAX_DAYS_AHEAD)
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]
    if days_ahead is None:
        days_ahead = 7

    # Validate working_hours_start
    working_hours_start_raw = arguments.get("working_hours_start", 9)
    working_hours_start, error = validate_positive_int(working_hours_start_raw, "working_hours_start", min_val=0, max_val=23)
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]
    if working_hours_start is None:
        working_hours_start = 9

    # Validate working_hours_end
    working_hours_end_raw = arguments.get("working_hours_end", 17)
    working_hours_end, error = validate_positive_int(working_hours_end_raw, "working_hours_end", min_val=0, max_val=23)
    if error:
        return [types.TextContent(type="text", text=f"Validation error: {error}")]
    if working_hours_end is None:
        working_hours_end = 17

    calendar_id = arguments.get("calendar_id", "primary")

    # Validate working hours relationship
    if working_hours_start >= working_hours_end:
        return [
            types.TextContent(
                type="text",
                text="Validation error: working_hours_start must be before working_hours_end"
            )
        ]

    # Calculate time range
    time_min = datetime.now(timezone.utc)
    time_max = time_min + timedelta(days=days_ahead)

    # Find free slots
    free_slots = calendar_client.find_free_time(
        duration_minutes=duration_minutes,
        time_min=time_min,
        time_max=time_max,
        calendar_id=calendar_id,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end
    )

    if not free_slots:
        return [
            types.TextContent(
                type="text",
                text=(
                    f"No free time slots found for {duration_minutes} minutes "
                    f"in the next {days_ahead} days during working hours "
                    f"({working_hours_start}:00-{working_hours_end}:00)."
                )
            )
        ]

    # Format response
    response_lines = [
        f"Available Time Slots ({duration_minutes} minutes):",
        f"Found {len(free_slots)} option(s)",
        ""
    ]

    for i, slot in enumerate(free_slots[:10], 1):  # Limit to 10 for display
        start = slot['start']
        end = slot['end']

        # Format nicely
        start_str = start.strftime("%A, %B %d at %I:%M %p")
        end_str = end.strftime("%I:%M %p")

        response_lines.append(f"{i}. {start_str} - {end_str}")

    if len(free_slots) > 10:
        response_lines.append(f"\n... and {len(free_slots) - 10} more slots")

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def main():
    """Run the MCP server."""
    logger.info("Starting Google Calendar MCP Server...")

    # Authenticate with Google Calendar
    if not calendar_client.authenticate():
        logger.error("Failed to authenticate with Google Calendar")
        logger.error("Please run scripts/setup_google_oauth.py to configure credentials")
        sys.exit(1)

    logger.info("Successfully authenticated with Google Calendar")

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

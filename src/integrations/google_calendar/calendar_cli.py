#!/usr/bin/env python3
"""
Calendar Gateway CLI - Fast, MCP-free calendar access.

Provides direct command-line access to Google Calendar operations,
bypassing MCP overhead for improved performance.
Supports --use-daemon for warm performance via pre-warmed daemon.

Commands:
  today           Get today's events
  week            Get this week's events
  events [N]      List next N events (default: 10)
  get ID          Get event details by ID
  free MINS       Find free time slots of given duration
  create          Create a new event
  delete ID       Delete an event

Usage:
  python3 calendar_cli.py today --json
  python3 calendar_cli.py week --json --compact
  python3 calendar_cli.py events 20 --json
  python3 calendar_cli.py free 60 --json
  python3 calendar_cli.py get EVENT_ID --json
  python3 calendar_cli.py create "Meeting" "2026-01-08T14:00" "2026-01-08T15:00"

  # With daemon (faster if daemon is running):
  python3 calendar_cli.py today --json --use-daemon

CHANGELOG (recent first, max 5 entries):
01/10/2026 - Fixed --use-daemon for events/get/create/delete commands (PR #7 review) (Claude)
01/08/2026 - Made GoogleCalendarClient import lazy for daemon mode (~2s faster) (Claude)
01/08/2026 - Added --use-daemon flag for warm performance (Claude)
01/08/2026 - Initial CLI gateway implementation (Claude)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, timezone

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Lazy import GoogleCalendarClient (2+ seconds to import due to google libraries)
# Only imported when NOT using daemon mode
if TYPE_CHECKING:
    from src.integrations.google_calendar.calendar_client import GoogleCalendarClient

# Default credentials directory
CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"

# Lazy-loaded clients (avoid overhead when using daemon)
_daemon_client = None


def get_daemon_client():
    """Lazy-load daemon client."""
    global _daemon_client
    if _daemon_client is None:
        from src.integrations.google_daemon.client import GoogleDaemonClient, is_daemon_running
        if not is_daemon_running():
            raise RuntimeError("Google daemon is not running. Start it with: python3 src/integrations/google_daemon/server.py start")
        _daemon_client = GoogleDaemonClient()
    return _daemon_client


# =============================================================================
# OUTPUT UTILITIES (token-optimized JSON output)
# =============================================================================

def emit_json(payload: Any, compact: bool = False) -> None:
    """Emit JSON output, optionally compact for LLM consumption."""
    if compact:
        print(json.dumps(payload, separators=(",", ":"), default=str))
    else:
        print(json.dumps(payload, indent=2, default=str))


def filter_fields(data: Dict[str, Any], fields: Optional[List[str]]) -> Dict[str, Any]:
    """Filter dictionary to only include specified fields."""
    if not fields:
        return data
    return {k: v for k, v in data.items() if k in fields}


def format_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Format raw Google Calendar event for clean output."""
    start = event.get('start', {})
    end = event.get('end', {})

    return {
        'id': event.get('id'),
        'summary': event.get('summary', 'No Title'),
        'start': start.get('dateTime', start.get('date')),
        'end': end.get('dateTime', end.get('date')),
        'location': event.get('location'),
        'description': event.get('description'),
        'attendees': [a.get('email') for a in event.get('attendees', [])],
        'html_link': event.get('htmlLink'),
        'status': event.get('status'),
        'creator': event.get('creator', {}).get('email'),
    }


def process_events(
    events: List[Dict[str, Any]],
    fields: Optional[List[str]] = None,
    max_desc_chars: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Apply formatting, field filtering, and text truncation to event list."""
    result = []
    for event in events:
        formatted = format_event(event)
        if fields:
            formatted = filter_fields(formatted, fields)
        if max_desc_chars and formatted.get('description'):
            if len(formatted['description']) > max_desc_chars:
                formatted['description'] = formatted['description'][:max_desc_chars] + "..."
        result.append(formatted)
    return result


# =============================================================================
# CLI COMMANDS
# =============================================================================

def cmd_today(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """Get today's events."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_today()
            events = result.get("events", [])
        else:
            now = datetime.now(timezone.utc)
            end_of_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

            events = client.list_events(
                time_min=now,
                time_max=end_of_day,
                max_results=50
            )

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None

        # Apply minimal preset
        if args.minimal:
            fields = fields or ['id', 'summary', 'start', 'end', 'location']
            args.max_desc_chars = args.max_desc_chars or 100

        processed = process_events(events, fields, args.max_desc_chars)

        if args.json:
            emit_json({"events": processed, "count": len(processed), "date": "today"}, compact=args.compact)
        else:
            print(f"Today's Events ({len(processed)}):")
            for event in processed:
                print(f"  {event.get('start', 'All day')}: {event.get('summary')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_week(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """Get this week's events."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_week()
            events = result.get("events", [])
        else:
            now = datetime.now(timezone.utc)
            end_of_week = now + timedelta(days=7)

            events = client.list_events(
                time_min=now,
                time_max=end_of_week,
                max_results=100
            )

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None

        # Apply minimal preset
        if args.minimal:
            fields = fields or ['id', 'summary', 'start', 'end', 'location']
            args.max_desc_chars = args.max_desc_chars or 100

        processed = process_events(events, fields, args.max_desc_chars)

        if args.json:
            emit_json({"events": processed, "count": len(processed), "period": "week"}, compact=args.compact)
        else:
            print(f"This Week's Events ({len(processed)}):")
            for event in processed:
                print(f"  {event.get('start', 'All day')}: {event.get('summary')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_events(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """List upcoming events."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_events(count=args.count, days=args.days or 7)
            events = result.get("events", [])
        else:
            now = datetime.now(timezone.utc)

            # Build time range
            time_max = None
            if args.days:
                time_max = now + timedelta(days=args.days)

            events = client.list_events(
                time_min=now,
                time_max=time_max,
                max_results=args.count
            )

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None

        # Apply minimal preset
        if args.minimal:
            fields = fields or ['id', 'summary', 'start', 'end', 'location']
            args.max_desc_chars = args.max_desc_chars or 100

        processed = process_events(events, fields, args.max_desc_chars)

        if args.json:
            emit_json({"events": processed, "count": len(processed)}, compact=args.compact)
        else:
            print(f"Upcoming Events ({len(processed)}):")
            for event in processed:
                print(f"  {event.get('start', 'All day')}: {event.get('summary')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_get(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """Get event details by ID."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_get(event_id=args.event_id)
            event = result.get("event")
        else:
            event = client.get_event(args.event_id)

        if not event:
            if args.json:
                emit_json({"error": f"Event not found: {args.event_id}"}, compact=args.compact)
            else:
                print(f"Event not found: {args.event_id}", file=sys.stderr)
            return 1

        formatted = format_event(event)

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None
        if fields:
            formatted = filter_fields(formatted, fields)

        if args.max_desc_chars and formatted.get('description'):
            if len(formatted['description']) > args.max_desc_chars:
                formatted['description'] = formatted['description'][:args.max_desc_chars] + "..."

        if args.json:
            emit_json(formatted, compact=args.compact)
        else:
            print(f"Event: {formatted.get('summary')}")
            print(f"  Start: {formatted.get('start')}")
            print(f"  End: {formatted.get('end')}")
            if formatted.get('location'):
                print(f"  Location: {formatted['location']}")
            if formatted.get('description'):
                print(f"  Description: {formatted['description']}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_free(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """Find free time slots."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_free(
                duration=args.duration,
                days=args.days,
                limit=args.limit or 10,
                work_start=args.work_start,
                work_end=args.work_end
            )
            formatted_slots = result.get("free_slots", [])
        else:
            now = datetime.now(timezone.utc)

            # Build time range
            time_max = now + timedelta(days=args.days)

            slots = client.find_free_time(
                duration_minutes=args.duration,
                time_min=now,
                time_max=time_max,
                working_hours_start=args.work_start,
                working_hours_end=args.work_end
            )

            # Format slots for output
            formatted_slots = [
                {
                    'start': slot['start'].isoformat(),
                    'end': slot['end'].isoformat(),
                    'duration_minutes': args.duration
                }
                for slot in slots
            ]

            # Limit results
            if args.limit and len(formatted_slots) > args.limit:
                formatted_slots = formatted_slots[:args.limit]

        if args.json:
            emit_json({
                "free_slots": formatted_slots,
                "count": len(formatted_slots),
                "duration_minutes": args.duration,
                "search_days": args.days
            }, compact=args.compact)
        else:
            print(f"Free {args.duration}-minute slots ({len(formatted_slots)} found):")
            for slot in formatted_slots:
                print(f"  {slot['start']} - {slot['end']}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_create(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """Create a new event."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_create(
                title=args.summary,
                start=args.start,
                end=args.end,
                description=args.description,
                location=args.location,
                attendees=args.attendees.split(',') if args.attendees else None
            )
            # Daemon returns {"event_id": "..."} on success
            if result.get("event_id"):
                formatted = {"id": result["event_id"], "summary": args.summary, "start": args.start, "end": args.end}
                if args.json:
                    emit_json({"success": True, "event": formatted}, compact=args.compact)
                else:
                    print(f"Created event: {args.summary}")
                    print(f"  ID: {result['event_id']}")
                    print(f"  Start: {args.start}")
                    print(f"  End: {args.end}")
                return 0
            else:
                if args.json:
                    emit_json({"success": False, "error": result.get("error", "Failed to create event")}, compact=args.compact)
                else:
                    print(f"Failed to create event: {result.get('error', 'unknown error')}", file=sys.stderr)
                return 1

        # Parse dates
        from dateutil import parser as date_parser
        start_time = date_parser.parse(args.start)
        end_time = date_parser.parse(args.end)

        # Parse attendees if provided
        attendees = None
        if args.attendees:
            attendees = [a.strip() for a in args.attendees.split(',')]

        event = client.create_event(
            summary=args.summary,
            start_time=start_time,
            end_time=end_time,
            description=args.description,
            location=args.location,
            attendees=attendees
        )

        if not event:
            if args.json:
                emit_json({"success": False, "error": "Failed to create event"}, compact=args.compact)
            else:
                print("Failed to create event", file=sys.stderr)
            return 1

        formatted = format_event(event)

        if args.json:
            emit_json({"success": True, "event": formatted}, compact=args.compact)
        else:
            print(f"Created event: {formatted.get('summary')}")
            print(f"  ID: {formatted.get('id')}")
            print(f"  Start: {formatted.get('start')}")
            print(f"  End: {formatted.get('end')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"success": False, "error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_delete(args: argparse.Namespace, client: GoogleCalendarClient) -> int:
    """Delete an event."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.calendar_delete(event_id=args.event_id)
            success = result.get("success", False)
        else:
            success = client.delete_event(args.event_id)

        if args.json:
            emit_json({"success": success, "event_id": args.event_id}, compact=args.compact)
        else:
            if success:
                print(f"Deleted event: {args.event_id}")
            else:
                print(f"Failed to delete event: {args.event_id}", file=sys.stderr)
                return 1
        return 0 if success else 1
    except Exception as e:
        if args.json:
            emit_json({"success": False, "error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


# =============================================================================
# OUTPUT ARGUMENTS (shared across commands)
# =============================================================================

def add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add LLM-friendly output controls for JSON output."""
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (required for skill integration)."
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Minify JSON output (reduces token cost)."
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="LLM-minimal preset: compact + essential fields + text truncation."
    )
    parser.add_argument(
        "--fields",
        help="Comma-separated list of JSON fields to include."
    )
    parser.add_argument(
        "--max-desc-chars",
        dest="max_desc_chars",
        type=int,
        default=None,
        help="Truncate description fields to N characters."
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calendar Gateway CLI - Fast, MCP-free calendar access.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s today --json                        # Today's events
  %(prog)s week --json --compact               # This week's events, compact
  %(prog)s events 20 --minimal                 # Next 20 events, LLM-optimized
  %(prog)s free 60 --json                      # Find 60-min free slots
  %(prog)s get EVENT_ID --json                 # Get event details
  %(prog)s create "Meeting" "2026-01-08T14:00" "2026-01-08T15:00"  # Create event
"""
    )

    parser.add_argument(
        "--credentials-dir",
        type=str,
        default=str(CREDENTIALS_DIR),
        help=f"Path to credentials directory (default: {CREDENTIALS_DIR})"
    )
    parser.add_argument(
        "--use-daemon",
        action="store_true",
        help="Use pre-warmed Google daemon for faster responses"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # today command
    p_today = subparsers.add_parser("today", help="Get today's events")
    add_output_args(p_today)

    # week command
    p_week = subparsers.add_parser("week", help="Get this week's events")
    add_output_args(p_week)

    # events command
    p_events = subparsers.add_parser("events", help="List upcoming events")
    p_events.add_argument("count", type=int, nargs="?", default=10, help="Number of events (default: 10)")
    p_events.add_argument("--days", type=int, help="Limit to next N days")
    add_output_args(p_events)

    # get command
    p_get = subparsers.add_parser("get", help="Get event details by ID")
    p_get.add_argument("event_id", help="Google Calendar event ID")
    add_output_args(p_get)

    # free command
    p_free = subparsers.add_parser("free", help="Find free time slots")
    p_free.add_argument("duration", type=int, help="Duration in minutes")
    p_free.add_argument("--days", type=int, default=7, help="Days to search (default: 7)")
    p_free.add_argument("--limit", type=int, default=10, help="Max slots to return (default: 10)")
    p_free.add_argument("--work-start", type=int, default=9, help="Working hours start (default: 9)")
    p_free.add_argument("--work-end", type=int, default=17, help="Working hours end (default: 17)")
    add_output_args(p_free)

    # create command
    p_create = subparsers.add_parser("create", help="Create a new event")
    p_create.add_argument("summary", help="Event title")
    p_create.add_argument("start", help="Start time (ISO 8601 or natural date)")
    p_create.add_argument("end", help="End time (ISO 8601 or natural date)")
    p_create.add_argument("--description", help="Event description")
    p_create.add_argument("--location", help="Event location")
    p_create.add_argument("--attendees", help="Comma-separated attendee emails")
    add_output_args(p_create)

    # delete command
    p_delete = subparsers.add_parser("delete", help="Delete an event")
    p_delete.add_argument("event_id", help="Google Calendar event ID")
    add_output_args(p_delete)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize client (skip if using daemon)
    client = None
    if not args.use_daemon:
        try:
            # Lazy import to avoid 2s+ overhead when using daemon mode
            from src.integrations.google_calendar.calendar_client import GoogleCalendarClient
            client = GoogleCalendarClient(args.credentials_dir)
            if not client.authenticate():
                print("Error: Failed to authenticate with Google Calendar", file=sys.stderr)
                print("\nSetup instructions:", file=sys.stderr)
                print("1. Go to https://console.cloud.google.com/apis/credentials", file=sys.stderr)
                print("2. Create OAuth 2.0 Client ID (Desktop app)", file=sys.stderr)
                print(f"3. Save as {CREDENTIALS_DIR}/credentials.json", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"Error initializing Calendar client: {e}", file=sys.stderr)
            return 1

    # Dispatch to command handler
    commands = {
        "today": cmd_today,
        "week": cmd_week,
        "events": cmd_events,
        "get": cmd_get,
        "free": cmd_free,
        "create": cmd_create,
        "delete": cmd_delete,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args, client)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

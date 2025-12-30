"""
Calendar Agent for AI Life Planner
Handles all calendar-related operations: events, time blocks, scheduling, and free time finding.

This agent integrates with the existing Database and CalendarEvent model to provide
natural language calendar management capabilities.
"""

from datetime import datetime, timedelta, timezone, time as dt_time
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from .base_agent import BaseAgent, AgentResponse
from ..core.models import CalendarEvent


class CalendarAgent(BaseAgent):
    """
    Specialized agent for calendar management.

    Handles intents:
    - add_event: Create a new calendar event
    - list_events: List upcoming events with filters
    - get_event: Get event details by ID
    - update_event: Modify an existing event
    - delete_event: Cancel/delete an event
    - find_free_time: Find available time slots
    - block_time: Create time blocks (deep work, focus time, etc.)

    Integrates with the Database layer for persistence and the CalendarEvent model
    for data representation.
    """

    # Supported intents for this agent
    INTENTS = [
        "add_event",
        "list_events",
        "get_event",
        "update_event",
        "delete_event",
        "find_free_time",
        "block_time"
    ]

    # Default duration in minutes when not specified
    DEFAULT_DURATION_MINUTES = 60

    # Time keywords for parsing (24-hour reference)
    TIME_KEYWORDS = {
        "morning": (9, 0),      # 9:00 AM
        "noon": (12, 0),        # 12:00 PM
        "afternoon": (14, 0),   # 2:00 PM
        "evening": (18, 0),     # 6:00 PM
        "night": (20, 0),       # 8:00 PM
        "midnight": (0, 0),     # 12:00 AM
    }

    # Day name to weekday number mapping (Monday = 0)
    WEEKDAY_MAP = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1, "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "thurs": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }

    def __init__(self, db, config):
        """Initialize the Calendar Agent."""
        super().__init__(db, config, "calendar")

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents."""
        return self.INTENTS

    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given intent."""
        return intent in self.INTENTS

    def process(self, intent: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process a calendar-related intent.

        Routes to the appropriate handler based on intent type.

        Args:
            intent: One of the supported calendar intents
            context: Request context with parameters

        Returns:
            AgentResponse with operation result
        """
        self.log_action(f"processing_{intent}", {"context_keys": list(context.keys())})

        handlers = {
            "add_event": self._handle_add_event,
            "list_events": self._handle_list_events,
            "get_event": self._handle_get_event,
            "update_event": self._handle_update_event,
            "delete_event": self._handle_delete_event,
            "find_free_time": self._handle_find_free_time,
            "block_time": self._handle_block_time,
        }

        handler = handlers.get(intent)
        if not handler:
            return AgentResponse.error(f"Unknown intent: {intent}")

        try:
            return handler(context)
        except Exception as e:
            self.logger.error(f"Error processing {intent}: {e}", exc_info=True)
            return AgentResponse.error(f"Failed to process {intent}: {str(e)}")

    # =========================================================================
    # Intent Handlers
    # =========================================================================

    def _handle_add_event(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Handle event creation.

        Supports two modes:
        1. Structured: title, start_time, end_time/duration provided directly
        2. Natural language: text field parsed for event details

        Context params:
            text (str): Natural language event description
            OR
            title (str): Event title
            start_time (str): Start time ISO string or natural language
            end_time (str, optional): End time ISO string
            duration (int, optional): Duration in minutes
            location (str, optional): Event location
            description (str, optional): Event description
            all_day (bool, optional): Whether this is an all-day event
        """
        # Check if we have natural language input
        if "text" in context and context["text"]:
            parsed = self._parse_event_from_text(context["text"])
            # Merge parsed values with any explicit overrides from context
            for key, value in parsed.items():
                if key not in context or context[key] is None:
                    context[key] = value

        # Validate required fields
        if not context.get("title"):
            return AgentResponse.error("Event title is required")

        if not context.get("start_time") and not context.get("all_day"):
            return AgentResponse.error("Event start time is required")

        # Parse and normalize times
        start_time = self._parse_datetime(context.get("start_time"))
        if not start_time and not context.get("all_day"):
            return AgentResponse.error(
                f"Could not parse start time: {context.get('start_time')}"
            )

        # Calculate end time from duration or use provided end_time
        if context.get("end_time"):
            end_time = self._parse_datetime(context["end_time"])
        elif context.get("duration"):
            duration_minutes = self._parse_duration(context["duration"])
            end_time = start_time + timedelta(minutes=duration_minutes) if start_time else None
        else:
            # Default duration
            end_time = start_time + timedelta(minutes=self.DEFAULT_DURATION_MINUTES) if start_time else None

        if not end_time and not context.get("all_day"):
            return AgentResponse.error("Could not determine event end time")

        # Handle all-day events
        all_day = context.get("all_day", False)
        if all_day:
            # For all-day events, set times to midnight
            if start_time:
                start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
            else:
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                start_time = today
                end_time = today + timedelta(days=1)

        # Build event data
        event_data = {
            "title": context["title"],
            "description": context.get("description"),
            "location": context.get("location"),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "all_day": all_day,
            "calendar_source": context.get("calendar_source", "internal"),
            "external_id": context.get("external_id"),
            "status": context.get("status", "confirmed"),
            "metadata": json.dumps(context.get("metadata", {})) if context.get("metadata") else None,
        }

        # Insert into database
        try:
            event_id = self._insert_event(event_data)
            created_event = self._get_event_by_id(event_id)

            return AgentResponse.ok(
                message=f"Event created: '{event_data['title']}' on {self._format_datetime(start_time)}",
                data={
                    "event_id": event_id,
                    "event": created_event
                },
                suggestions=[
                    "List today's events",
                    f"Update event {event_id}",
                    "Find free time slots"
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to create event: {e}")
            return AgentResponse.error(f"Failed to create event: {str(e)}")

    def _handle_list_events(self, context: Dict[str, Any]) -> AgentResponse:
        """
        List upcoming events with optional filters.

        Context params:
            days_ahead (int): Number of days ahead to look (default 7)
            start_date (str): Start of date range
            end_date (str): End of date range
            status (str): Filter by status
            limit (int): Max events to return (default 50)
            include_cancelled (bool): Include cancelled events (default False)
        """
        # Determine date range
        now = datetime.now(timezone.utc)
        days_ahead = context.get("days_ahead", 7)

        if "start_date" in context:
            start_date = self._parse_datetime(context["start_date"])
        else:
            start_date = now

        if "end_date" in context:
            end_date = self._parse_datetime(context["end_date"])
        else:
            end_date = now + timedelta(days=days_ahead)

        limit = context.get("limit", 50)
        include_cancelled = context.get("include_cancelled", False)
        status = context.get("status")

        events = self._fetch_events(
            start_date=start_date,
            end_date=end_date,
            status=status,
            include_cancelled=include_cancelled,
            limit=limit
        )

        if not events:
            return AgentResponse.ok(
                message="No events found in the specified time range",
                data={"events": [], "count": 0}
            )

        return AgentResponse.ok(
            message=f"Found {len(events)} event(s)",
            data={
                "events": events,
                "count": len(events),
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
        )

    def _handle_get_event(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Get a single event by ID.

        Context params:
            event_id (int): Event ID to retrieve
        """
        validation = self.validate_required_params(context, ["event_id"])
        if validation:
            return validation

        event = self._get_event_by_id(context["event_id"])
        if event:
            return AgentResponse.ok(
                message=f"Event: {event['title']}",
                data={"event": event}
            )
        else:
            return AgentResponse.error(f"Event {context['event_id']} not found")

    def _handle_update_event(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Update event properties.

        Context params:
            event_id (int): Event to update
            title (str, optional): New title
            description (str, optional): New description
            location (str, optional): New location
            start_time (str, optional): New start time
            end_time (str, optional): New end time
            status (str, optional): New status
        """
        validation = self.validate_required_params(context, ["event_id"])
        if validation:
            return validation

        event_id = context["event_id"]

        # Build update data
        update_fields = {}
        if "title" in context:
            update_fields["title"] = context["title"]
        if "description" in context:
            update_fields["description"] = context["description"]
        if "location" in context:
            update_fields["location"] = context["location"]
        if "start_time" in context:
            parsed_start = self._parse_datetime(context["start_time"])
            if parsed_start:
                update_fields["start_time"] = parsed_start.isoformat()
        if "end_time" in context:
            parsed_end = self._parse_datetime(context["end_time"])
            if parsed_end:
                update_fields["end_time"] = parsed_end.isoformat()
        if "status" in context:
            update_fields["status"] = context["status"]
        if "all_day" in context:
            update_fields["all_day"] = context["all_day"]
        if "metadata" in context:
            update_fields["metadata"] = json.dumps(context["metadata"])

        if not update_fields:
            return AgentResponse.error("No fields to update provided")

        try:
            success = self._update_event(event_id, update_fields)
            if success:
                updated_event = self._get_event_by_id(event_id)
                return AgentResponse.ok(
                    message=f"Event {event_id} updated",
                    data={"event": updated_event}
                )
            else:
                return AgentResponse.error(f"Event {event_id} not found")
        except Exception as e:
            return AgentResponse.error(f"Failed to update event: {str(e)}")

    def _handle_delete_event(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Delete (cancel) an event.

        Context params:
            event_id (int): Event to delete
            hard_delete (bool): If True, permanently delete; otherwise mark as cancelled
        """
        validation = self.validate_required_params(context, ["event_id"])
        if validation:
            return validation

        event_id = context["event_id"]
        hard_delete = context.get("hard_delete", False)

        try:
            if hard_delete:
                success = self._hard_delete_event(event_id)
                action = "deleted"
            else:
                success = self._update_event(event_id, {"status": "cancelled"})
                action = "cancelled"

            if success:
                return AgentResponse.ok(
                    message=f"Event {event_id} {action}",
                    data={"event_id": event_id, "action": action}
                )
            else:
                return AgentResponse.error(f"Event {event_id} not found")
        except Exception as e:
            return AgentResponse.error(f"Failed to delete event: {str(e)}")

    def _handle_find_free_time(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Find available time slots.

        Context params:
            duration_minutes (int): Required duration for the slot (default 60)
            days_ahead (int): Number of days to look ahead (default 7)
            work_hours_only (bool): Only consider work hours (default True)
            start_date (str): Start looking from this date
        """
        duration_minutes = context.get("duration_minutes", 60)
        days_ahead = context.get("days_ahead", 7)
        work_hours_only = context.get("work_hours_only", True)

        # Get work hours from config
        work_start = self.get_config_value("work_hours_start", section="preferences", default="09:00")
        work_end = self.get_config_value("work_hours_end", section="preferences", default="17:00")

        # Parse work hours
        work_start_hour, work_start_min = map(int, work_start.split(":"))
        work_end_hour, work_end_min = map(int, work_end.split(":"))

        now = datetime.now(timezone.utc)
        if "start_date" in context:
            start_date = self._parse_datetime(context["start_date"])
        else:
            start_date = now

        end_date = start_date + timedelta(days=days_ahead)

        # Fetch events in the range
        events = self._fetch_events(
            start_date=start_date,
            end_date=end_date,
            include_cancelled=False,
            limit=500
        )

        # Find free slots
        free_slots = []
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            # Define the day's boundaries
            if work_hours_only:
                day_start = datetime(
                    current_date.year, current_date.month, current_date.day,
                    work_start_hour, work_start_min, tzinfo=timezone.utc
                )
                day_end = datetime(
                    current_date.year, current_date.month, current_date.day,
                    work_end_hour, work_end_min, tzinfo=timezone.utc
                )
            else:
                day_start = datetime(
                    current_date.year, current_date.month, current_date.day,
                    0, 0, tzinfo=timezone.utc
                )
                day_end = datetime(
                    current_date.year, current_date.month, current_date.day,
                    23, 59, tzinfo=timezone.utc
                )

            # Skip past time if this is today
            if current_date == now.date() and day_start < now:
                day_start = now

            # Get events for this day
            day_events = [
                e for e in events
                if e.get("start_time") and e.get("end_time") and
                self._parse_datetime(e["start_time"]).date() == current_date
            ]

            # Sort by start time
            day_events.sort(key=lambda e: e["start_time"])

            # Find gaps
            current_slot_start = day_start
            for event in day_events:
                event_start = self._parse_datetime(event["start_time"])
                event_end = self._parse_datetime(event["end_time"])

                # Cap event times to work hours if needed
                if work_hours_only:
                    event_start = max(event_start, day_start)
                    event_end = min(event_end, day_end)

                if event_start > current_slot_start:
                    gap_duration = (event_start - current_slot_start).total_seconds() / 60
                    if gap_duration >= duration_minutes:
                        free_slots.append({
                            "start": current_slot_start.isoformat(),
                            "end": event_start.isoformat(),
                            "duration_minutes": int(gap_duration),
                            "date": current_date.isoformat()
                        })

                current_slot_start = max(current_slot_start, event_end)

            # Check for remaining time after last event
            if current_slot_start < day_end:
                gap_duration = (day_end - current_slot_start).total_seconds() / 60
                if gap_duration >= duration_minutes:
                    free_slots.append({
                        "start": current_slot_start.isoformat(),
                        "end": day_end.isoformat(),
                        "duration_minutes": int(gap_duration),
                        "date": current_date.isoformat()
                    })

            current_date += timedelta(days=1)

        return AgentResponse.ok(
            message=f"Found {len(free_slots)} free time slot(s) of {duration_minutes}+ minutes",
            data={
                "free_slots": free_slots,
                "count": len(free_slots),
                "parameters": {
                    "duration_minutes": duration_minutes,
                    "days_ahead": days_ahead,
                    "work_hours_only": work_hours_only
                }
            },
            suggestions=[
                "Block a time slot for deep work",
                "Schedule a meeting in the first available slot"
            ]
        )

    def _handle_block_time(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Create a time block (deep work, focus time, etc.).

        Similar to add_event but with specific metadata for time blocking.

        Context params:
            title (str): Block title (e.g., "Deep Work", "Focus Time")
            start_time (str): When to start the block
            duration (int, optional): Duration in minutes (default from config)
            block_type (str, optional): Type of block (deep_work, focus, break, etc.)
        """
        # Use configured deep work duration as default
        default_duration = self.get_config_value(
            "deep_work_block_duration",
            section="preferences",
            default=120
        )

        # Set defaults for time blocks
        if "title" not in context or not context["title"]:
            context["title"] = context.get("block_type", "Time Block").replace("_", " ").title()

        if "duration" not in context:
            context["duration"] = default_duration

        # Add metadata for time block tracking
        context["metadata"] = {
            "is_time_block": True,
            "block_type": context.get("block_type", "focus"),
            **(context.get("metadata") or {})
        }

        # Delegate to add_event handler
        return self._handle_add_event(context)

    # =========================================================================
    # Natural Language Parsing
    # =========================================================================

    def _parse_event_from_text(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text to extract event properties.

        Extracts:
        - Title (main event description)
        - Start time (from various time/date formats)
        - Duration (from duration mentions)
        - Location (from "at <location>" patterns)

        Examples:
        - "Schedule meeting tomorrow at 2pm for 1 hour"
        - "Team standup Monday 10am"
        - "Lunch with John at noon at Cafe Roma"

        Args:
            text: Natural language event description

        Returns:
            Dictionary with parsed event properties
        """
        result = {
            "title": text,
            "start_time": None,
            "duration": None,
            "location": None,
            "description": None,
        }

        working_text = text

        # Extract location (pattern: "at <location>" - must be capitalized or multi-word)
        # Be careful not to match "at noon", "at 2pm", etc.
        location_patterns = [
            # "at Cafe Roma" or "at The Office" (capitalized location)
            r'\s+at\s+([A-Z][A-Za-z\s]+(?:\s+[A-Z][A-Za-z\s]+)*)(?=\s*$)',
            # "at <Location>" before time indicators (not matching time words)
            r'\s+at\s+([A-Z][A-Za-z\s\']+?)(?=\s+(?:at|on|from|tomorrow|today|next|\d))',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, working_text)
            if match:
                potential_location = match.group(1).strip()
                # Check it's not a time-related word and has actual content
                if not self._is_time_word(potential_location) and len(potential_location) > 1:
                    result["location"] = potential_location
                    working_text = working_text[:match.start()] + working_text[match.end():]
                    break

        # Extract duration
        duration, working_text = self._extract_duration(working_text)
        if duration:
            result["duration"] = duration

        # Extract start time
        start_time, working_text = self._extract_datetime(working_text)
        if start_time:
            result["start_time"] = start_time.isoformat()

        # Clean up title
        result["title"] = self._clean_title(working_text)

        return result

    def _is_time_word(self, word: str) -> bool:
        """Check if word is a time-related term that shouldn't be treated as location."""
        word_lower = word.lower().strip()
        time_words = [
            "noon", "midnight", "morning", "afternoon", "evening", "night",
            "am", "pm", "today", "tomorrow", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday"
        ]
        # Check if word is a time word or starts with a digit (like "2pm")
        if word_lower in time_words:
            return True
        # Check for time patterns like "2pm", "10am", "3:30pm"
        if re.match(r'^\d{1,2}(?::\d{2})?\s*(?:am|pm)?$', word_lower):
            return True
        return False

    def _extract_duration(self, text: str) -> Tuple[Optional[int], str]:
        """
        Extract duration from text.

        Patterns:
        - "for 1 hour", "for 30 minutes"
        - "1h", "30min", "90 min", "2 hours"

        Returns:
            Tuple of (duration in minutes, cleaned text)
        """
        duration_patterns = [
            (r'\bfor\s+(\d+(?:\.\d+)?)\s*hours?\b', lambda m: int(float(m.group(1)) * 60)),
            (r'\bfor\s+(\d+)\s*(?:minutes?|mins?)\b', lambda m: int(m.group(1))),
            (r'\bfor\s+(\d+)\s*h\b', lambda m: int(m.group(1)) * 60),
            (r'\bfor\s+(\d+)\s*m\b', lambda m: int(m.group(1))),
            (r'\b(\d+(?:\.\d+)?)\s*hours?\b', lambda m: int(float(m.group(1)) * 60)),
            (r'\b(\d+)\s*(?:minutes?|mins?)\b', lambda m: int(m.group(1))),
            (r'\b(\d+)\s*h\b(?!\w)', lambda m: int(m.group(1)) * 60),
        ]

        for pattern, converter in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = converter(match)
                cleaned = text[:match.start()] + text[match.end():]
                return duration, cleaned.strip()

        return None, text

    def _extract_datetime(self, text: str) -> Tuple[Optional[datetime], str]:
        """
        Extract datetime from text.

        Handles:
        - Relative: "today", "tomorrow", "next Monday"
        - Time of day: "at 2pm", "at 14:00", "at noon"
        - Combined: "tomorrow at 3pm", "next Friday at 10am"

        Returns:
            Tuple of (datetime, cleaned text)
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        result_date = None
        result_time = None
        cleaned_text = text

        # Extract date first
        date_patterns = [
            (r'\btoday\b', lambda: today),
            (r'\btonight\b', lambda: today),
            (r'\btomorrow\b', lambda: today + timedelta(days=1)),
            (r'\bday after tomorrow\b', lambda: today + timedelta(days=2)),
            (r'\bnext week\b', lambda: today + timedelta(days=7)),
        ]

        for pattern, date_func in date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result_date = date_func()
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
                break

        # Check for weekday patterns
        if not result_date:
            for day_name, weekday in self.WEEKDAY_MAP.items():
                patterns = [
                    rf'\b(?:next\s+)?{day_name}\b',
                    rf'\bon\s+{day_name}\b',
                ]
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        # Calculate next occurrence of this weekday
                        days_ahead = weekday - today.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        result_date = today + timedelta(days=days_ahead)
                        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
                        break
                if result_date:
                    break

        # Check for explicit dates
        if not result_date:
            explicit_patterns = [
                (r'\b(\d{4}-\d{2}-\d{2})\b', '%Y-%m-%d'),
                (r'\b(\d{1,2}/\d{1,2}/\d{4})\b', '%m/%d/%Y'),
                (r'\b(\d{1,2}/\d{1,2})\b', '%m/%d'),
            ]
            for pattern, date_format in explicit_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        date_str = match.group(1)
                        if date_format == '%m/%d':
                            date_str = f"{date_str}/{today.year}"
                            date_format = '%m/%d/%Y'
                        parsed = datetime.strptime(date_str, date_format).date()
                        result_date = parsed
                        cleaned_text = cleaned_text[:match.start()] + cleaned_text[match.end():]
                        break
                    except ValueError:
                        continue

        # Default to today if no date found
        if not result_date:
            result_date = today

        # Extract time
        time_patterns = [
            # "at 2pm", "at 2:30pm"
            (r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
             lambda m: self._parse_12h_time(m.group(1), m.group(2), m.group(3))),
            # "at 14:00", "at 9:30"
            (r'\bat\s+(\d{1,2}):(\d{2})\b',
             lambda m: (int(m.group(1)), int(m.group(2)))),
            # "2pm", "2:30pm" (without "at")
            (r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
             lambda m: self._parse_12h_time(m.group(1), m.group(2), m.group(3))),
            # "14:00", "9:30" (24-hour without "at")
            (r'\b(\d{2}):(\d{2})\b',
             lambda m: (int(m.group(1)), int(m.group(2)))),
        ]

        for pattern, time_parser in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result_time = time_parser(match)
                cleaned_text = cleaned_text[:match.start()] + cleaned_text[match.end():]
                break

        # Check for time keywords
        if not result_time:
            for keyword, (hour, minute) in self.TIME_KEYWORDS.items():
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    result_time = (hour, minute)
                    cleaned_text = re.sub(rf'\b{keyword}\b', '', cleaned_text, flags=re.IGNORECASE)
                    break

        # Combine date and time
        if result_time:
            hour, minute = result_time
            result = datetime(
                result_date.year, result_date.month, result_date.day,
                hour, minute, tzinfo=timezone.utc
            )
            return result, cleaned_text.strip()
        elif result_date != today:
            # If we have a date but no time, use 9am as default
            result = datetime(
                result_date.year, result_date.month, result_date.day,
                9, 0, tzinfo=timezone.utc
            )
            return result, cleaned_text.strip()

        return None, text

    def _parse_12h_time(self, hour_str: str, minute_str: Optional[str],
                        meridiem: str) -> Tuple[int, int]:
        """Convert 12-hour time to 24-hour tuple."""
        hour = int(hour_str)
        minute = int(minute_str) if minute_str else 0
        meridiem = meridiem.lower()

        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        return (hour, minute)

    def _parse_datetime(self, dt_input: Any) -> Optional[datetime]:
        """
        Parse and normalize datetime input.

        Args:
            dt_input: String datetime, datetime object, or None

        Returns:
            datetime object in UTC or None
        """
        if dt_input is None:
            return None
        if isinstance(dt_input, datetime):
            if dt_input.tzinfo is None:
                return dt_input.replace(tzinfo=timezone.utc)
            return dt_input
        if isinstance(dt_input, str):
            # Try ISO format first
            try:
                parsed = datetime.fromisoformat(dt_input.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                pass

            # Try natural language parsing
            result, _ = self._extract_datetime(dt_input)
            return result

        return None

    def _parse_duration(self, duration_input: Any) -> int:
        """
        Parse duration to minutes.

        Args:
            duration_input: Integer, string with units, or None

        Returns:
            Duration in minutes
        """
        if duration_input is None:
            return self.DEFAULT_DURATION_MINUTES
        if isinstance(duration_input, int):
            return duration_input
        if isinstance(duration_input, str):
            extracted, _ = self._extract_duration(f"for {duration_input}")
            return extracted or self.DEFAULT_DURATION_MINUTES
        return self.DEFAULT_DURATION_MINUTES

    def _clean_title(self, text: str) -> str:
        """Clean up extracted title."""
        # Remove common action words
        action_words = [
            r'^schedule\s+(?:a\s+)?',
            r'^create\s+(?:a\s+)?(?:event|meeting|appointment)\s+(?:for\s+)?',
            r'^add\s+(?:a\s+)?(?:event|meeting|appointment)\s+(?:for\s+)?',
            r'^set\s+up\s+(?:a\s+)?',
            r'^book\s+(?:a\s+)?(?:time\s+slot\s+for\s+)?',
        ]
        for pattern in action_words:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove orphaned time references that weren't fully cleaned
        time_cleanup_patterns = [
            r'\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*$',
            r'\s+at\s+(?:noon|midnight|morning|afternoon|evening)\s*$',
            r'\s+for\s+\d+\s*(?:h|hours?|minutes?|mins?|m)?\s*$',
            r'\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*$',  # Trailing "10am" without "at"
            r'\s+(?:at\s+)?(?:noon|midnight)\s*$',
        ]
        for pattern in time_cleanup_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove trailing prepositions
        text = re.sub(r'\s+(?:at|on|for|to)\s*$', '', text, flags=re.IGNORECASE)

        # Remove extra spaces and clean up
        text = re.sub(r'\s+', ' ', text).strip(' ,.-:')
        return text

    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if not dt:
            return "unknown time"
        return dt.strftime("%B %d, %Y at %I:%M %p")

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _insert_event(self, event_data: Dict[str, Any]) -> int:
        """Insert a new event and return its ID."""
        query = """
            INSERT INTO calendar_events (
                title, description, location, start_time, end_time,
                all_day, calendar_source, external_id, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            event_data["title"],
            event_data.get("description"),
            event_data.get("location"),
            event_data.get("start_time"),
            event_data.get("end_time"),
            event_data.get("all_day", False),
            event_data.get("calendar_source", "internal"),
            event_data.get("external_id"),
            event_data.get("status", "confirmed"),
            event_data.get("metadata"),
        )
        return self.db.execute_write(query, params)

    def _get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single event by ID."""
        query = "SELECT * FROM calendar_events WHERE id = ?"
        row = self.db.execute_one(query, (event_id,))
        return self.db.row_to_dict(row)

    def _update_event(self, event_id: int, fields: Dict[str, Any]) -> bool:
        """Update specified event fields."""
        if not fields:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        query = f"UPDATE calendar_events SET {set_clause} WHERE id = ?"
        params = tuple(fields.values()) + (event_id,)

        result = self.db.execute_write(query, params)
        return result > 0

    def _hard_delete_event(self, event_id: int) -> bool:
        """Permanently delete an event."""
        query = "DELETE FROM calendar_events WHERE id = ?"
        result = self.db.execute_write(query, (event_id,))
        return result > 0

    def _fetch_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        include_cancelled: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch events with filters."""
        conditions = []
        params = []

        if start_date:
            conditions.append("end_time >= ?")
            params.append(start_date.isoformat())

        if end_date:
            conditions.append("start_time <= ?")
            params.append(end_date.isoformat())

        if status:
            conditions.append("status = ?")
            params.append(status)
        elif not include_cancelled:
            conditions.append("status != 'cancelled'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM calendar_events
            WHERE {where_clause}
            ORDER BY start_time ASC
            LIMIT ?
        """
        params.append(limit)

        rows = self.db.execute(query, tuple(params))
        return self.db.rows_to_dicts(rows)

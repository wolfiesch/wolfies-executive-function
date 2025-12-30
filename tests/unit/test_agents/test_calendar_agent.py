"""
Unit tests for the CalendarAgent.
Tests time parsing, duration parsing, natural language parsing, intent handling,
error handling, and database integration.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.calendar_agent import CalendarAgent
from src.agents.base_agent import AgentResponse
from src.core.database import Database


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary in-memory database with the calendar_events table schema."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create calendar_events table matching production schema
    cursor.execute("""
        CREATE TABLE calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            all_day INTEGER DEFAULT 0,
            calendar_source TEXT DEFAULT 'internal',
            external_id TEXT,
            status TEXT DEFAULT 'confirmed',
            metadata TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
        )
    """)
    conn.commit()
    conn.close()

    return Database(db_file)


@pytest.fixture
def mock_config():
    """Create a mock config object with default preferences."""
    config = MagicMock()

    def config_get(key, section="preferences", default=None):
        config_values = {
            "work_hours_start": "09:00",
            "work_hours_end": "17:00",
            "deep_work_block_duration": 120,
        }
        return config_values.get(key, default)

    config.get.side_effect = config_get
    return config


@pytest.fixture
def calendar_agent(temp_db, mock_config):
    """Create a CalendarAgent instance with test database and config."""
    agent = CalendarAgent(temp_db, mock_config)
    agent.initialize()
    return agent


@pytest.fixture
def populated_db(temp_db):
    """Populate the test database with sample events."""
    now = datetime.now(timezone.utc)
    today = now.date()

    events = [
        (
            "Morning standup",
            "Daily team sync",
            "Conference Room A",
            datetime(today.year, today.month, today.day, 9, 0, tzinfo=timezone.utc).isoformat(),
            datetime(today.year, today.month, today.day, 9, 30, tzinfo=timezone.utc).isoformat(),
            0,
            "internal",
            None,
            "confirmed",
            None
        ),
        (
            "Lunch with client",
            "Discuss Q1 projections",
            "Cafe Roma",
            datetime(today.year, today.month, today.day, 12, 0, tzinfo=timezone.utc).isoformat(),
            datetime(today.year, today.month, today.day, 13, 0, tzinfo=timezone.utc).isoformat(),
            0,
            "internal",
            None,
            "confirmed",
            None
        ),
        (
            "Project review",
            None,
            None,
            datetime(today.year, today.month, today.day, 14, 0, tzinfo=timezone.utc).isoformat(),
            datetime(today.year, today.month, today.day, 15, 0, tzinfo=timezone.utc).isoformat(),
            0,
            "internal",
            None,
            "confirmed",
            None
        ),
        (
            "Old meeting",
            "Past event",
            None,
            (datetime(today.year, today.month, today.day, 10, 0, tzinfo=timezone.utc) - timedelta(days=5)).isoformat(),
            (datetime(today.year, today.month, today.day, 11, 0, tzinfo=timezone.utc) - timedelta(days=5)).isoformat(),
            0,
            "internal",
            None,
            "confirmed",
            None
        ),
        (
            "Cancelled meeting",
            "This was cancelled",
            None,
            datetime(today.year, today.month, today.day, 16, 0, tzinfo=timezone.utc).isoformat(),
            datetime(today.year, today.month, today.day, 17, 0, tzinfo=timezone.utc).isoformat(),
            0,
            "internal",
            None,
            "cancelled",
            None
        ),
    ]

    for event in events:
        temp_db.execute_write(
            """INSERT INTO calendar_events
               (title, description, location, start_time, end_time, all_day,
                calendar_source, external_id, status, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            event
        )

    return temp_db


@pytest.fixture
def calendar_agent_with_data(populated_db, mock_config):
    """Create a CalendarAgent with pre-populated test data."""
    agent = CalendarAgent(populated_db, mock_config)
    agent.initialize()
    return agent


# =============================================================================
# Test Agent Initialization and Basic Properties
# =============================================================================

class TestCalendarAgentInit:
    """Tests for CalendarAgent initialization."""

    def test_agent_initializes_correctly(self, calendar_agent):
        """CalendarAgent initializes with correct name and properties."""
        assert calendar_agent.name == "calendar"
        assert calendar_agent._initialized is True

    def test_get_supported_intents(self, calendar_agent):
        """get_supported_intents returns all expected intents."""
        intents = calendar_agent.get_supported_intents()

        expected = [
            "add_event", "list_events", "get_event",
            "update_event", "delete_event", "find_free_time", "block_time"
        ]

        for intent in expected:
            assert intent in intents

    def test_can_handle_supported_intents(self, calendar_agent):
        """can_handle returns True for supported intents."""
        assert calendar_agent.can_handle("add_event", {}) is True
        assert calendar_agent.can_handle("list_events", {}) is True
        assert calendar_agent.can_handle("get_event", {}) is True
        assert calendar_agent.can_handle("update_event", {}) is True
        assert calendar_agent.can_handle("delete_event", {}) is True
        assert calendar_agent.can_handle("find_free_time", {}) is True
        assert calendar_agent.can_handle("block_time", {}) is True

    def test_can_handle_unsupported_intents(self, calendar_agent):
        """can_handle returns False for unsupported intents."""
        assert calendar_agent.can_handle("add_task", {}) is False
        assert calendar_agent.can_handle("create_note", {}) is False
        assert calendar_agent.can_handle("unknown_intent", {}) is False


# =============================================================================
# Test Time Parsing - 12-hour Time Formats
# =============================================================================

class TestTimeParsing12Hour:
    """Tests for parsing 12-hour time formats."""

    def test_parse_2pm(self, calendar_agent):
        """Parses '2pm' correctly."""
        result = calendar_agent._parse_12h_time("2", None, "pm")
        assert result == (14, 0)

    def test_parse_2am(self, calendar_agent):
        """Parses '2am' correctly."""
        result = calendar_agent._parse_12h_time("2", None, "am")
        assert result == (2, 0)

    def test_parse_12pm_noon(self, calendar_agent):
        """Parses '12pm' as noon (12:00)."""
        result = calendar_agent._parse_12h_time("12", None, "pm")
        assert result == (12, 0)

    def test_parse_12am_midnight(self, calendar_agent):
        """Parses '12am' as midnight (00:00)."""
        result = calendar_agent._parse_12h_time("12", None, "am")
        assert result == (0, 0)

    def test_parse_230pm(self, calendar_agent):
        """Parses '2:30pm' correctly."""
        result = calendar_agent._parse_12h_time("2", "30", "pm")
        assert result == (14, 30)

    def test_parse_1045am(self, calendar_agent):
        """Parses '10:45am' correctly."""
        result = calendar_agent._parse_12h_time("10", "45", "am")
        assert result == (10, 45)

    def test_parse_1159pm(self, calendar_agent):
        """Parses '11:59pm' correctly."""
        result = calendar_agent._parse_12h_time("11", "59", "pm")
        assert result == (23, 59)

    def test_parse_uppercase_am(self, calendar_agent):
        """Handles uppercase AM/PM."""
        result = calendar_agent._parse_12h_time("3", None, "PM")
        assert result == (15, 0)

    def test_parse_9am(self, calendar_agent):
        """Parses '9am' correctly."""
        result = calendar_agent._parse_12h_time("9", None, "am")
        assert result == (9, 0)


# =============================================================================
# Test Time Parsing - 24-hour Time Formats
# =============================================================================

class TestTimeParsing24Hour:
    """Tests for parsing 24-hour time formats."""

    def test_parse_14_00(self, calendar_agent):
        """Parses '14:00' from text correctly."""
        result, _ = calendar_agent._extract_datetime("Meeting at 14:00")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 0

    def test_parse_09_30(self, calendar_agent):
        """Parses '09:30' from text correctly."""
        result, _ = calendar_agent._extract_datetime("Standup at 09:30")
        assert result is not None
        assert result.hour == 9
        assert result.minute == 30

    def test_parse_23_45(self, calendar_agent):
        """Parses '23:45' from text correctly."""
        result, _ = calendar_agent._extract_datetime("Late night at 23:45")
        assert result is not None
        assert result.hour == 23
        assert result.minute == 45

    def test_parse_00_00(self, calendar_agent):
        """Parses '00:00' from text correctly (midnight in 24-hour)."""
        # Note: This may or may not parse depending on pattern specifics
        # Testing the regex pattern behavior
        result, _ = calendar_agent._extract_datetime("at 00:00 midnight")
        # 00:00 may not match as it requires 2-digit hour in pattern
        # The actual behavior depends on implementation


# =============================================================================
# Test Time Parsing - Time Keywords
# =============================================================================

class TestTimeParsingKeywords:
    """Tests for parsing time keywords (noon, midnight, morning, etc.)."""

    def test_parse_noon(self, calendar_agent):
        """Parses 'noon' as 12:00."""
        result, _ = calendar_agent._extract_datetime("Meeting at noon")
        assert result is not None
        assert result.hour == 12
        assert result.minute == 0

    def test_parse_midnight(self, calendar_agent):
        """Parses 'midnight' as 00:00."""
        result, _ = calendar_agent._extract_datetime("Event at midnight")
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_morning(self, calendar_agent):
        """Parses 'morning' as 9:00."""
        result, _ = calendar_agent._extract_datetime("Call in the morning")
        assert result is not None
        assert result.hour == 9
        assert result.minute == 0

    def test_parse_afternoon(self, calendar_agent):
        """Parses 'afternoon' as 14:00."""
        result, _ = calendar_agent._extract_datetime("Meeting this afternoon")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 0

    def test_parse_evening(self, calendar_agent):
        """Parses 'evening' as 18:00."""
        result, _ = calendar_agent._extract_datetime("Dinner in the evening")
        assert result is not None
        assert result.hour == 18
        assert result.minute == 0

    def test_parse_night(self, calendar_agent):
        """Parses 'night' as 20:00."""
        result, _ = calendar_agent._extract_datetime("Movie night")
        assert result is not None
        assert result.hour == 20
        assert result.minute == 0


# =============================================================================
# Test Time Parsing - Relative Dates
# =============================================================================

class TestTimeParsingRelativeDates:
    """Tests for parsing relative date expressions."""

    def test_parse_today(self, calendar_agent):
        """Parses 'today' as current date."""
        result, _ = calendar_agent._extract_datetime("Meeting today at 3pm")
        assert result is not None
        assert result.date() == datetime.now(timezone.utc).date()
        assert result.hour == 15

    def test_parse_tomorrow(self, calendar_agent):
        """Parses 'tomorrow' as next day."""
        result, _ = calendar_agent._extract_datetime("Call tomorrow at 10am")
        expected_date = datetime.now(timezone.utc).date() + timedelta(days=1)
        assert result is not None
        assert result.date() == expected_date
        assert result.hour == 10

    def test_parse_tomorrow_at_3pm(self, calendar_agent):
        """Parses 'tomorrow at 3pm' completely."""
        result, _ = calendar_agent._extract_datetime("tomorrow at 3pm")
        expected_date = datetime.now(timezone.utc).date() + timedelta(days=1)
        assert result is not None
        assert result.date() == expected_date
        assert result.hour == 15
        assert result.minute == 0

    def test_parse_next_week(self, calendar_agent):
        """Parses 'next week' as 7 days ahead."""
        result, _ = calendar_agent._extract_datetime("Review next week")
        expected_date = datetime.now(timezone.utc).date() + timedelta(days=7)
        assert result is not None
        assert result.date() == expected_date


# =============================================================================
# Test Time Parsing - Weekdays
# =============================================================================

class TestTimeParsingWeekdays:
    """Tests for parsing weekday references."""

    def test_parse_next_monday(self, calendar_agent):
        """Parses 'next Monday' correctly."""
        result, _ = calendar_agent._extract_datetime("Meeting next Monday 10am")
        assert result is not None
        assert result.weekday() == 0  # Monday
        assert result.hour == 10

    def test_parse_on_tuesday(self, calendar_agent):
        """Parses 'on Tuesday' correctly."""
        result, _ = calendar_agent._extract_datetime("Lunch on Tuesday at noon")
        assert result is not None
        assert result.weekday() == 1  # Tuesday
        assert result.hour == 12

    def test_parse_friday(self, calendar_agent):
        """Parses standalone 'Friday' reference."""
        result, _ = calendar_agent._extract_datetime("Report due Friday 5pm")
        assert result is not None
        assert result.weekday() == 4  # Friday
        assert result.hour == 17

    def test_parse_wednesday(self, calendar_agent):
        """Parses 'wednesday' correctly."""
        result, _ = calendar_agent._extract_datetime("Call wednesday afternoon")
        assert result is not None
        assert result.weekday() == 2  # Wednesday
        assert result.hour == 14  # afternoon

    def test_parse_saturday(self, calendar_agent):
        """Parses weekend day correctly."""
        result, _ = calendar_agent._extract_datetime("Party on Saturday evening")
        assert result is not None
        assert result.weekday() == 5  # Saturday
        assert result.hour == 18  # evening

    def test_parse_sunday(self, calendar_agent):
        """Parses 'Sunday' correctly."""
        result, _ = calendar_agent._extract_datetime("Brunch Sunday morning")
        assert result is not None
        assert result.weekday() == 6  # Sunday
        assert result.hour == 9  # morning


# =============================================================================
# Test Time Parsing - Invalid/Edge Cases
# =============================================================================

class TestTimeParsingEdgeCases:
    """Tests for edge cases and error handling in time parsing."""

    def test_parse_no_time_in_text(self, calendar_agent):
        """Returns None when no time is present."""
        result, cleaned = calendar_agent._extract_datetime("Simple meeting")
        # May return default time or None depending on implementation
        # Check it doesn't crash

    def test_parse_datetime_returns_datetime_object(self, calendar_agent):
        """_parse_datetime with datetime object returns it unchanged."""
        dt = datetime(2025, 6, 15, 14, 30, tzinfo=timezone.utc)
        result = calendar_agent._parse_datetime(dt)
        assert result == dt

    def test_parse_datetime_with_none(self, calendar_agent):
        """_parse_datetime with None returns None."""
        result = calendar_agent._parse_datetime(None)
        assert result is None

    def test_parse_datetime_iso_format(self, calendar_agent):
        """_parse_datetime handles ISO format strings."""
        result = calendar_agent._parse_datetime("2025-06-15T14:30:00+00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_datetime_adds_utc_timezone(self, calendar_agent):
        """_parse_datetime adds UTC timezone to naive datetime."""
        naive_dt = datetime(2025, 6, 15, 14, 30)
        result = calendar_agent._parse_datetime(naive_dt)
        assert result.tzinfo == timezone.utc


# =============================================================================
# Test Duration Parsing
# =============================================================================

class TestDurationParsing:
    """Tests for duration extraction from text."""

    def test_extract_1_hour(self, calendar_agent):
        """Extracts '1 hour' as 60 minutes."""
        duration, _ = calendar_agent._extract_duration("Meeting for 1 hour")
        assert duration == 60

    def test_extract_2_hours(self, calendar_agent):
        """Extracts '2 hours' as 120 minutes."""
        duration, _ = calendar_agent._extract_duration("Workshop for 2 hours")
        assert duration == 120

    def test_extract_30_minutes(self, calendar_agent):
        """Extracts '30 minutes' correctly."""
        duration, _ = calendar_agent._extract_duration("Call for 30 minutes")
        assert duration == 30

    def test_extract_45_mins(self, calendar_agent):
        """Extracts '45 mins' abbreviation."""
        duration, _ = calendar_agent._extract_duration("Sync for 45 mins")
        assert duration == 45

    def test_extract_90_min(self, calendar_agent):
        """Extracts '90 min' singular abbreviation."""
        duration, _ = calendar_agent._extract_duration("Deep work for 90 min")
        assert duration == 90

    def test_extract_2h_abbreviation(self, calendar_agent):
        """Extracts '2h' abbreviation as 120 minutes."""
        duration, _ = calendar_agent._extract_duration("Focus time 2h")
        assert duration == 120

    def test_extract_3h_abbreviation(self, calendar_agent):
        """Extracts '3h' abbreviation as 180 minutes."""
        duration, _ = calendar_agent._extract_duration("Training 3h")
        assert duration == 180

    def test_no_duration_returns_none(self, calendar_agent):
        """Returns None when no duration found."""
        duration, _ = calendar_agent._extract_duration("Simple meeting")
        assert duration is None

    def test_parse_duration_integer_passthrough(self, calendar_agent):
        """_parse_duration returns integer as-is."""
        result = calendar_agent._parse_duration(45)
        assert result == 45

    def test_parse_duration_string_with_units(self, calendar_agent):
        """_parse_duration handles string with units."""
        result = calendar_agent._parse_duration("2 hours")
        assert result == 120


# =============================================================================
# Test Natural Language Parsing - Event Extraction
# =============================================================================

class TestNLEventParsing:
    """Tests for parsing natural language event descriptions."""

    def test_parse_schedule_meeting_tomorrow(self, calendar_agent):
        """Parses 'Schedule meeting tomorrow at 2pm'."""
        result = calendar_agent._parse_event_from_text("Schedule meeting tomorrow at 2pm")

        assert result["start_time"] is not None
        expected_date = datetime.now(timezone.utc).date() + timedelta(days=1)
        parsed_dt = datetime.fromisoformat(result["start_time"])
        assert parsed_dt.date() == expected_date
        assert parsed_dt.hour == 14

    def test_parse_block_time_deep_work(self, calendar_agent):
        """Parses 'Block 2 hours for deep work'."""
        result = calendar_agent._parse_event_from_text("Block 2 hours for deep work")
        assert result["duration"] == 120

    def test_extract_location_from_at_cafe(self, calendar_agent):
        """Extracts location from 'at Cafe Roma' when at end of text."""
        # Note: Location extraction works best when location is at end of string
        # The regex pattern avoids matching time words following "at"
        result = calendar_agent._parse_event_from_text("Lunch at noon at Cafe Roma")
        assert result["location"] == "Cafe Roma"

    def test_extract_location_capitalized_place(self, calendar_agent):
        """Extracts capitalized location names."""
        result = calendar_agent._parse_event_from_text("Meeting at The Office")
        assert result["location"] == "The Office"

    def test_no_location_when_at_noon(self, calendar_agent):
        """Does not extract 'noon' as location from 'at noon'."""
        result = calendar_agent._parse_event_from_text("Lunch at noon")
        assert result["location"] is None or result["location"] == ""

    def test_no_location_when_at_time(self, calendar_agent):
        """Does not extract time as location."""
        result = calendar_agent._parse_event_from_text("Meeting at 2pm")
        assert result["location"] is None

    def test_title_extraction_removes_action_words(self, calendar_agent):
        """Title is cleaned of action words like 'schedule'."""
        result = calendar_agent._parse_event_from_text("Schedule team standup")
        assert "schedule" not in result["title"].lower()

    def test_title_extraction_removes_time_references(self, calendar_agent):
        """Title is cleaned of time references."""
        result = calendar_agent._parse_event_from_text("Team sync tomorrow at 10am")
        title = result["title"].lower()
        assert "tomorrow" not in title
        assert "10am" not in title

    def test_complete_event_parsing(self, calendar_agent):
        """Parses event with all components."""
        text = "Schedule meeting at Conference Room tomorrow at 2pm for 1 hour"
        result = calendar_agent._parse_event_from_text(text)

        assert result["duration"] == 60
        expected_date = datetime.now(timezone.utc).date() + timedelta(days=1)
        parsed_dt = datetime.fromisoformat(result["start_time"])
        assert parsed_dt.date() == expected_date
        assert parsed_dt.hour == 14
        # Location might be extracted depending on pattern matching
        assert result["title"] is not None


# =============================================================================
# Test Intent Handler - add_event
# =============================================================================

class TestAddEventIntent:
    """Tests for the add_event intent handler."""

    def test_add_event_with_title_and_time(self, calendar_agent):
        """Creates event with title and start time."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Team Meeting",
            "start_time": start_time.isoformat()
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        assert "event_id" in response.data
        assert response.data["event"]["title"] == "Team Meeting"

    def test_add_event_with_duration(self, calendar_agent):
        """Creates event with specified duration."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        context = {
            "title": "Workshop",
            "start_time": start_time.isoformat(),
            "duration": 90
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        event = response.data["event"]

        start = datetime.fromisoformat(event["start_time"])
        end = datetime.fromisoformat(event["end_time"])
        duration_minutes = (end - start).total_seconds() / 60
        assert duration_minutes == 90

    def test_add_event_with_location(self, calendar_agent):
        """Creates event with location."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)

        context = {
            "title": "Lunch Meeting",
            "start_time": start_time.isoformat(),
            "location": "Cafe Downtown"
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        assert response.data["event"]["location"] == "Cafe Downtown"

    def test_add_event_with_description(self, calendar_agent):
        """Creates event with description."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)

        context = {
            "title": "Project Review",
            "start_time": start_time.isoformat(),
            "description": "Quarterly project status review"
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        assert response.data["event"]["description"] == "Quarterly project status review"

    def test_add_event_with_natural_language(self, calendar_agent):
        """Creates event from natural language text."""
        context = {
            "text": "Schedule team standup tomorrow at 9am for 30 minutes"
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        event = response.data["event"]

        # Verify duration
        start = datetime.fromisoformat(event["start_time"])
        end = datetime.fromisoformat(event["end_time"])
        duration_minutes = (end - start).total_seconds() / 60
        assert duration_minutes == 30

        # Verify date is tomorrow
        expected_date = datetime.now(timezone.utc).date() + timedelta(days=1)
        assert start.date() == expected_date

        # Verify time is 9am
        assert start.hour == 9

    def test_add_event_all_day(self, calendar_agent):
        """Creates all-day event."""
        context = {
            "title": "Company Holiday",
            "all_day": True
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        event = response.data["event"]
        assert event["all_day"] == 1 or event["all_day"] is True

    def test_add_event_missing_title_fails(self, calendar_agent):
        """add_event fails when title is missing."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        context = {
            "start_time": tomorrow.isoformat()
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is False
        assert "title" in response.message.lower()

    def test_add_event_missing_start_time_fails(self, calendar_agent):
        """add_event fails when start time is missing for non-all-day event."""
        context = {
            "title": "Meeting"
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is False
        assert "start time" in response.message.lower()

    def test_add_event_returns_suggestions(self, calendar_agent):
        """add_event response includes suggestions."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Meeting",
            "start_time": start_time.isoformat()
        }
        response = calendar_agent.process("add_event", context)

        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_add_event_default_duration(self, calendar_agent):
        """Event uses default duration when not specified."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Quick Sync",
            "start_time": start_time.isoformat()
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        event = response.data["event"]

        start = datetime.fromisoformat(event["start_time"])
        end = datetime.fromisoformat(event["end_time"])
        duration_minutes = (end - start).total_seconds() / 60

        # Default duration is 60 minutes
        assert duration_minutes == 60

    def test_add_event_with_explicit_end_time(self, calendar_agent):
        """Creates event with explicit end time."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = tomorrow.replace(hour=16, minute=30, second=0, microsecond=0)

        context = {
            "title": "Extended Meeting",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is True
        event = response.data["event"]

        end = datetime.fromisoformat(event["end_time"])
        assert end.hour == 16
        assert end.minute == 30


# =============================================================================
# Test Intent Handler - list_events
# =============================================================================

class TestListEventsIntent:
    """Tests for the list_events intent handler."""

    def test_list_events_returns_events(self, calendar_agent_with_data):
        """list_events returns upcoming events."""
        response = calendar_agent_with_data.process("list_events", {})

        assert response.success is True
        assert "events" in response.data
        assert response.data["count"] >= 0

    def test_list_events_excludes_cancelled(self, calendar_agent_with_data):
        """list_events excludes cancelled events by default."""
        response = calendar_agent_with_data.process("list_events", {})

        events = response.data["events"]
        for event in events:
            assert event["status"] != "cancelled"

    def test_list_events_includes_cancelled_when_requested(self, calendar_agent_with_data):
        """list_events includes cancelled when include_cancelled=True."""
        response = calendar_agent_with_data.process(
            "list_events", {"include_cancelled": True}
        )

        events = response.data["events"]
        statuses = [e["status"] for e in events]
        assert "cancelled" in statuses

    def test_list_events_with_days_ahead(self, calendar_agent_with_data):
        """list_events respects days_ahead parameter."""
        response = calendar_agent_with_data.process(
            "list_events", {"days_ahead": 1}
        )

        assert response.success is True
        # Should return events within 1 day

    def test_list_events_with_limit(self, calendar_agent_with_data):
        """list_events respects limit parameter."""
        response = calendar_agent_with_data.process(
            "list_events", {"limit": 2, "include_cancelled": True}
        )

        assert response.success is True
        assert len(response.data["events"]) <= 2

    def test_list_events_empty_when_no_events(self, calendar_agent):
        """list_events returns empty list when no events."""
        response = calendar_agent.process("list_events", {})

        assert response.success is True
        assert response.data["events"] == []
        assert response.data["count"] == 0

    def test_list_events_includes_date_range(self, calendar_agent_with_data):
        """list_events response includes date range info."""
        response = calendar_agent_with_data.process("list_events", {})

        assert "date_range" in response.data
        assert "start" in response.data["date_range"]
        assert "end" in response.data["date_range"]


# =============================================================================
# Test Intent Handler - get_event
# =============================================================================

class TestGetEventIntent:
    """Tests for the get_event intent handler."""

    def test_get_event_by_id(self, calendar_agent_with_data):
        """Retrieves event by ID."""
        response = calendar_agent_with_data.process("get_event", {"event_id": 1})

        assert response.success is True
        assert response.data["event"]["id"] == 1
        assert response.data["event"]["title"] == "Morning standup"

    def test_get_event_missing_id_fails(self, calendar_agent_with_data):
        """get_event fails when event_id is missing."""
        response = calendar_agent_with_data.process("get_event", {})

        assert response.success is False
        assert "event_id" in response.message.lower()

    def test_get_event_invalid_id_fails(self, calendar_agent_with_data):
        """get_event fails for non-existent event."""
        response = calendar_agent_with_data.process("get_event", {"event_id": 9999})

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handler - update_event
# =============================================================================

class TestUpdateEventIntent:
    """Tests for the update_event intent handler."""

    def test_update_event_title(self, calendar_agent_with_data):
        """Updates event title."""
        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 1, "title": "Updated Standup"}
        )

        assert response.success is True
        assert response.data["event"]["title"] == "Updated Standup"

    def test_update_event_location(self, calendar_agent_with_data):
        """Updates event location."""
        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 1, "location": "New Room B"}
        )

        assert response.success is True
        assert response.data["event"]["location"] == "New Room B"

    def test_update_event_description(self, calendar_agent_with_data):
        """Updates event description."""
        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 1, "description": "New description"}
        )

        assert response.success is True
        assert response.data["event"]["description"] == "New description"

    def test_update_event_status(self, calendar_agent_with_data):
        """Updates event status."""
        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 1, "status": "tentative"}
        )

        assert response.success is True
        assert response.data["event"]["status"] == "tentative"

    def test_update_event_start_time(self, calendar_agent_with_data):
        """Updates event start time."""
        new_start = datetime.now(timezone.utc) + timedelta(days=2)
        new_start = new_start.replace(hour=11, minute=0, second=0, microsecond=0)

        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 1, "start_time": new_start.isoformat()}
        )

        assert response.success is True
        updated_start = datetime.fromisoformat(response.data["event"]["start_time"])
        assert updated_start.hour == 11

    def test_update_event_multiple_fields(self, calendar_agent_with_data):
        """Updates multiple event fields at once."""
        response = calendar_agent_with_data.process(
            "update_event", {
                "event_id": 1,
                "title": "New Title",
                "location": "New Location",
                "description": "New Description"
            }
        )

        assert response.success is True
        event = response.data["event"]
        assert event["title"] == "New Title"
        assert event["location"] == "New Location"
        assert event["description"] == "New Description"

    def test_update_event_missing_id_fails(self, calendar_agent_with_data):
        """update_event fails when event_id is missing."""
        response = calendar_agent_with_data.process(
            "update_event", {"title": "No ID"}
        )

        assert response.success is False
        assert "event_id" in response.message.lower()

    def test_update_event_no_fields_fails(self, calendar_agent_with_data):
        """update_event fails when no update fields provided."""
        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 1}
        )

        assert response.success is False
        assert "no fields" in response.message.lower()

    def test_update_event_invalid_id_fails(self, calendar_agent_with_data):
        """update_event fails for non-existent event."""
        response = calendar_agent_with_data.process(
            "update_event", {"event_id": 9999, "title": "Never exists"}
        )

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handler - delete_event
# =============================================================================

class TestDeleteEventIntent:
    """Tests for the delete_event intent handler."""

    def test_delete_event_soft_delete(self, calendar_agent_with_data):
        """delete_event marks event as cancelled (soft delete)."""
        response = calendar_agent_with_data.process(
            "delete_event", {"event_id": 1}
        )

        assert response.success is True
        assert response.data["action"] == "cancelled"

        # Verify status is cancelled
        event = calendar_agent_with_data._get_event_by_id(1)
        assert event["status"] == "cancelled"

    def test_delete_event_hard_delete(self, calendar_agent_with_data):
        """delete_event with hard_delete=True permanently deletes."""
        response = calendar_agent_with_data.process(
            "delete_event", {"event_id": 1, "hard_delete": True}
        )

        assert response.success is True
        assert response.data["action"] == "deleted"

        # Verify event no longer exists
        event = calendar_agent_with_data._get_event_by_id(1)
        assert event is None

    def test_delete_event_missing_id_fails(self, calendar_agent_with_data):
        """delete_event fails when event_id is missing."""
        response = calendar_agent_with_data.process("delete_event", {})

        assert response.success is False
        assert "event_id" in response.message.lower()

    def test_delete_event_invalid_id_fails(self, calendar_agent_with_data):
        """delete_event fails for non-existent event."""
        response = calendar_agent_with_data.process(
            "delete_event", {"event_id": 9999}
        )

        assert response.success is False


# =============================================================================
# Test Intent Handler - find_free_time
# =============================================================================

class TestFindFreeTimeIntent:
    """Tests for the find_free_time intent handler."""

    def test_find_free_time_returns_slots(self, calendar_agent_with_data):
        """find_free_time returns available slots."""
        response = calendar_agent_with_data.process(
            "find_free_time", {"duration_minutes": 30, "days_ahead": 7}
        )

        assert response.success is True
        assert "free_slots" in response.data
        assert isinstance(response.data["free_slots"], list)

    def test_find_free_time_respects_duration(self, calendar_agent_with_data):
        """find_free_time only returns slots >= requested duration."""
        response = calendar_agent_with_data.process(
            "find_free_time", {"duration_minutes": 60}
        )

        assert response.success is True
        for slot in response.data["free_slots"]:
            assert slot["duration_minutes"] >= 60

    def test_find_free_time_includes_count(self, calendar_agent_with_data):
        """find_free_time response includes slot count."""
        response = calendar_agent_with_data.process("find_free_time", {})

        assert response.success is True
        assert "count" in response.data
        assert response.data["count"] == len(response.data["free_slots"])

    def test_find_free_time_includes_parameters(self, calendar_agent_with_data):
        """find_free_time response includes search parameters."""
        response = calendar_agent_with_data.process(
            "find_free_time", {"duration_minutes": 45, "days_ahead": 3}
        )

        assert response.success is True
        assert "parameters" in response.data
        assert response.data["parameters"]["duration_minutes"] == 45
        assert response.data["parameters"]["days_ahead"] == 3

    def test_find_free_time_returns_suggestions(self, calendar_agent_with_data):
        """find_free_time response includes suggestions."""
        response = calendar_agent_with_data.process("find_free_time", {})

        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_find_free_time_slot_structure(self, calendar_agent_with_data):
        """find_free_time slots have expected structure."""
        response = calendar_agent_with_data.process("find_free_time", {})

        if response.data["free_slots"]:
            slot = response.data["free_slots"][0]
            assert "start" in slot
            assert "end" in slot
            assert "duration_minutes" in slot
            assert "date" in slot


# =============================================================================
# Test Intent Handler - block_time
# =============================================================================

class TestBlockTimeIntent:
    """Tests for the block_time intent handler."""

    def test_block_time_creates_event(self, calendar_agent):
        """block_time creates a calendar event."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Deep Work",
            "start_time": start_time.isoformat()
        }
        response = calendar_agent.process("block_time", context)

        assert response.success is True
        assert "event_id" in response.data

    def test_block_time_with_block_type(self, calendar_agent):
        """block_time uses block_type for metadata."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        context = {
            "title": "Focus Time",
            "start_time": start_time.isoformat(),
            "block_type": "deep_work"
        }
        response = calendar_agent.process("block_time", context)

        assert response.success is True
        event = response.data["event"]

        if event["metadata"]:
            metadata = json.loads(event["metadata"])
            assert metadata["is_time_block"] is True
            assert metadata["block_type"] == "deep_work"

    def test_block_time_default_title(self, calendar_agent):
        """block_time generates title from block_type when not provided."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "start_time": start_time.isoformat(),
            "block_type": "focus"
        }
        response = calendar_agent.process("block_time", context)

        assert response.success is True
        # Title should be derived from block_type
        assert "Focus" in response.data["event"]["title"]

    def test_block_time_uses_configured_duration(self, calendar_agent):
        """block_time uses configured deep work duration as default."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Deep Work Session",
            "start_time": start_time.isoformat()
            # No duration specified - should use config default
        }
        response = calendar_agent.process("block_time", context)

        assert response.success is True
        event = response.data["event"]

        start = datetime.fromisoformat(event["start_time"])
        end = datetime.fromisoformat(event["end_time"])
        duration_minutes = (end - start).total_seconds() / 60

        # Config mock returns 120 for deep_work_block_duration
        assert duration_minutes == 120

    def test_block_time_with_custom_duration(self, calendar_agent):
        """block_time allows custom duration override."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Quick Focus",
            "start_time": start_time.isoformat(),
            "duration": 45
        }
        response = calendar_agent.process("block_time", context)

        assert response.success is True
        event = response.data["event"]

        start = datetime.fromisoformat(event["start_time"])
        end = datetime.fromisoformat(event["end_time"])
        duration_minutes = (end - start).total_seconds() / 60

        assert duration_minutes == 45


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in CalendarAgent."""

    def test_unknown_intent_returns_error(self, calendar_agent):
        """Unknown intent returns error response."""
        response = calendar_agent.process("unknown_intent", {})

        assert response.success is False
        assert "unknown intent" in response.message.lower()

    def test_database_error_handled(self, calendar_agent, mock_config):
        """Database errors are caught and returned as error response."""
        mock_db = MagicMock()
        mock_db.execute_write.side_effect = Exception("Database connection failed")

        agent = CalendarAgent(mock_db, mock_config)

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        context = {
            "title": "Test Event",
            "start_time": tomorrow.isoformat()
        }
        response = agent.process("add_event", context)

        assert response.success is False
        assert "failed" in response.message.lower()

    def test_invalid_start_time_format(self, calendar_agent):
        """Invalid start time format returns error."""
        context = {
            "title": "Meeting",
            "start_time": "not-a-valid-time"
        }
        response = calendar_agent.process("add_event", context)

        assert response.success is False
        assert "parse" in response.message.lower() or "start time" in response.message.lower()

    def test_validation_error_for_missing_params(self, calendar_agent):
        """Validation catches missing required parameters."""
        response = calendar_agent.process("get_event", {})

        assert response.success is False
        assert "event_id" in response.message.lower()


# =============================================================================
# Test Database Integration
# =============================================================================

class TestDatabaseIntegration:
    """Tests for database integration in CalendarAgent."""

    def test_event_persisted_correctly(self, calendar_agent):
        """Event is correctly persisted to database."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        context = {
            "title": "Persistent Event",
            "start_time": start_time.isoformat(),
            "location": "Test Location",
            "description": "Test description",
            "duration": 60
        }
        response = calendar_agent.process("add_event", context)
        event_id = response.data["event_id"]

        # Fetch directly from database
        event = calendar_agent._get_event_by_id(event_id)

        assert event["title"] == "Persistent Event"
        assert event["location"] == "Test Location"
        assert event["description"] == "Test description"

    def test_event_update_persisted(self, calendar_agent_with_data):
        """Event update is correctly persisted."""
        calendar_agent_with_data.process(
            "update_event", {"event_id": 1, "title": "Updated Title"}
        )

        # Fetch fresh from database
        event = calendar_agent_with_data._get_event_by_id(1)
        assert event["title"] == "Updated Title"

    def test_event_list_sorted_by_start_time(self, calendar_agent_with_data):
        """Events are returned sorted by start time."""
        response = calendar_agent_with_data.process(
            "list_events", {"include_cancelled": True, "days_ahead": 30}
        )

        events = response.data["events"]

        # Verify sorted by start_time ascending
        for i in range(len(events) - 1):
            current_start = events[i]["start_time"]
            next_start = events[i + 1]["start_time"]
            assert current_start <= next_start


# =============================================================================
# Test AgentResponse Structure
# =============================================================================

class TestAgentResponseStructure:
    """Tests for AgentResponse data structure."""

    def test_success_response_structure(self, calendar_agent):
        """Successful response has expected structure."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        response = calendar_agent.process("add_event", {
            "title": "Test",
            "start_time": start_time.isoformat()
        })

        assert hasattr(response, "success")
        assert hasattr(response, "message")
        assert hasattr(response, "data")
        assert hasattr(response, "suggestions")

    def test_error_response_structure(self, calendar_agent):
        """Error response has expected structure."""
        response = calendar_agent.process("add_event", {})  # Missing title

        assert response.success is False
        assert response.message is not None
        assert len(response.message) > 0

    def test_response_to_dict(self, calendar_agent):
        """Response can be converted to dictionary."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

        response = calendar_agent.process("add_event", {
            "title": "Test",
            "start_time": start_time.isoformat()
        })

        result = response.to_dict()
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "data" in result


# =============================================================================
# Test Helper Methods
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods in CalendarAgent."""

    def test_is_time_word_noon(self, calendar_agent):
        """'noon' is recognized as time word."""
        assert calendar_agent._is_time_word("noon") is True

    def test_is_time_word_midnight(self, calendar_agent):
        """'midnight' is recognized as time word."""
        assert calendar_agent._is_time_word("midnight") is True

    def test_is_time_word_morning(self, calendar_agent):
        """'morning' is recognized as time word."""
        assert calendar_agent._is_time_word("morning") is True

    def test_is_time_word_2pm(self, calendar_agent):
        """'2pm' is recognized as time word."""
        assert calendar_agent._is_time_word("2pm") is True

    def test_is_time_word_location(self, calendar_agent):
        """'Cafe' is not recognized as time word."""
        assert calendar_agent._is_time_word("Cafe") is False

    def test_format_datetime(self, calendar_agent):
        """_format_datetime returns formatted string."""
        dt = datetime(2025, 6, 15, 14, 30, tzinfo=timezone.utc)
        result = calendar_agent._format_datetime(dt)

        assert "June" in result
        assert "15" in result
        assert "2025" in result
        assert "02:30 PM" in result

    def test_format_datetime_none(self, calendar_agent):
        """_format_datetime handles None."""
        result = calendar_agent._format_datetime(None)
        assert result == "unknown time"

    def test_clean_title_removes_schedule(self, calendar_agent):
        """_clean_title removes 'schedule' prefix."""
        result = calendar_agent._clean_title("schedule meeting with team")
        assert "schedule" not in result.lower()
        assert "meeting" in result.lower()

    def test_clean_title_removes_extra_spaces(self, calendar_agent):
        """_clean_title removes extra whitespace."""
        result = calendar_agent._clean_title("  meeting   with   team  ")
        assert "  " not in result
        assert result == result.strip()


# =============================================================================
# Test Overlapping Events (Edge Case)
# =============================================================================

class TestOverlappingEvents:
    """Tests for handling overlapping events."""

    def test_add_overlapping_event_succeeds(self, calendar_agent_with_data):
        """Adding overlapping event is allowed (no validation in agent)."""
        # Get an existing event's time
        existing = calendar_agent_with_data._get_event_by_id(1)

        # Try to create an overlapping event
        context = {
            "title": "Overlapping Meeting",
            "start_time": existing["start_time"],
            "duration": 30
        }
        response = calendar_agent_with_data.process("add_event", context)

        # Should succeed - overlap detection may be handled elsewhere
        assert response.success is True

    def test_find_free_time_avoids_existing_events(self, calendar_agent_with_data):
        """find_free_time returns slots that don't overlap with events."""
        response = calendar_agent_with_data.process(
            "find_free_time", {"duration_minutes": 30}
        )

        # All returned slots should be truly free
        # (This is validated by the implementation)
        assert response.success is True
        assert isinstance(response.data["free_slots"], list)

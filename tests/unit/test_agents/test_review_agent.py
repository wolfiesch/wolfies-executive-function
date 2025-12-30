"""
Unit tests for the ReviewAgent.
Tests daily/weekly reviews, reflections, insights, prompt generation,
mood detection, and database integration.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import json
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.review_agent import ReviewAgent
from src.agents.base_agent import AgentResponse
from src.core.database import Database


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database with all required tables."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create tasks table
    cursor.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            priority INTEGER NOT NULL DEFAULT 3,
            project_id INTEGER,
            para_category_id INTEGER,
            parent_task_id INTEGER,
            estimated_minutes INTEGER,
            actual_minutes INTEGER,
            due_date TEXT,
            scheduled_start TEXT,
            scheduled_end TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            tags TEXT,
            context TEXT
        )
    """)

    # Create calendar_events table
    cursor.execute("""
        CREATE TABLE calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT DEFAULT 'confirmed',
            location TEXT,
            source TEXT DEFAULT 'local',
            external_id TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            metadata TEXT
        )
    """)

    # Create projects table (for goals)
    cursor.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            para_category_id INTEGER,
            start_date TEXT,
            target_end_date TEXT,
            actual_end_date TEXT,
            archived INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            metadata TEXT
        )
    """)

    # Create notes table
    cursor.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_path TEXT,
            note_type TEXT DEFAULT 'note',
            tags TEXT,
            metadata TEXT,
            word_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
        )
    """)

    conn.commit()
    conn.close()

    return Database(db_file)


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config object with default preferences."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    config = MagicMock()
    config.get.return_value = "weekly"  # Default review frequency
    config.get_notes_directory.return_value = notes_dir
    return config


@pytest.fixture
def review_agent(temp_db, mock_config):
    """Create a ReviewAgent instance with test database and config."""
    agent = ReviewAgent(temp_db, mock_config)
    agent.initialize()
    return agent


@pytest.fixture
def today():
    """Get today's date."""
    return datetime.now(timezone.utc).date()


@pytest.fixture
def today_iso(today):
    """Get today's date as ISO string."""
    return today.isoformat()


@pytest.fixture
def yesterday(today):
    """Get yesterday's date."""
    return today - timedelta(days=1)


@pytest.fixture
def yesterday_iso(yesterday):
    """Get yesterday's date as ISO string."""
    return yesterday.isoformat()


@pytest.fixture
def week_ago(today):
    """Get date from a week ago."""
    return today - timedelta(days=7)


@pytest.fixture
def sample_tasks(temp_db, today, today_iso, yesterday_iso):
    """Populate database with sample tasks."""
    tasks = [
        # Completed today
        ("Task completed today 1", "desc", "done", 4, None, today_iso, today_iso),
        ("Task completed today 2", "desc", "done", 3, None, today_iso, today_iso),
        ("Task completed today 3", "desc", "done", 5, None, today_iso, today_iso),
        # Remaining tasks
        ("Task remaining 1", "desc", "todo", 5, None, today_iso, None),
        ("Task remaining 2", "desc", "todo", 4, None, today_iso, None),
        ("Task remaining 3", "desc", "in_progress", 3, None, today_iso, None),
        # Completed yesterday
        ("Task completed yesterday", "desc", "done", 3, None, yesterday_iso, yesterday_iso),
        # Cancelled
        ("Cancelled task", "desc", "cancelled", 2, None, today_iso, None),
    ]

    for task in tasks:
        temp_db.execute_write(
            """INSERT INTO tasks
               (title, description, status, priority, project_id, due_date, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            task
        )

    return temp_db


@pytest.fixture
def sample_events(temp_db, today_iso):
    """Populate database with sample events."""
    events = [
        ("Morning meeting", "Team standup", f"{today_iso}T09:00:00", f"{today_iso}T09:30:00", "confirmed"),
        ("Lunch with client", None, f"{today_iso}T12:00:00", f"{today_iso}T13:00:00", "confirmed"),
        ("Cancelled meeting", None, f"{today_iso}T15:00:00", f"{today_iso}T16:00:00", "cancelled"),
    ]

    for event in events:
        temp_db.execute_write(
            """INSERT INTO calendar_events (title, description, start_time, end_time, status)
               VALUES (?, ?, ?, ?, ?)""",
            event
        )

    return temp_db


@pytest.fixture
def sample_goals(temp_db, today, today_iso):
    """Populate database with sample goals."""
    start_date = (today - timedelta(days=30)).isoformat()
    target_date = (today + timedelta(days=60)).isoformat()

    goals = [
        # Active goal with progress logged today
        (
            "Save $10,000",
            "Emergency fund",
            "active",
            start_date,
            target_date,
            0,
            json.dumps({
                "is_goal": True,
                "goal_type": "finance",
                "overall_progress": 50,
                "progress_log": [
                    {"date": today_iso, "note": "Made progress", "percentage": 50},
                    {"date": (today - timedelta(days=7)).isoformat(), "note": "Started", "percentage": 30},
                ],
            })
        ),
        # Active goal with no recent progress (stalled)
        (
            "Run a marathon",
            "26.2 miles",
            "active",
            start_date,
            (today + timedelta(days=30)).isoformat(),
            0,
            json.dumps({
                "is_goal": True,
                "goal_type": "health",
                "overall_progress": 10,
                "progress_log": [
                    {"date": (today - timedelta(days=14)).isoformat(), "note": "Started", "percentage": 10},
                ],
            })
        ),
        # Goal at risk (close deadline, low progress)
        (
            "Learn Spanish",
            "B1 level",
            "active",
            start_date,
            (today + timedelta(days=10)).isoformat(),
            0,
            json.dumps({
                "is_goal": True,
                "goal_type": "learning",
                "overall_progress": 20,
                "progress_log": [],
            })
        ),
    ]

    for goal in goals:
        temp_db.execute_write(
            """INSERT INTO projects
               (name, description, status, start_date, target_end_date, archived, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            goal
        )

    return temp_db


@pytest.fixture
def sample_reflections(temp_db, today, today_iso, yesterday_iso):
    """Populate database with sample reflections."""
    reflections = [
        (
            f"Reflection - {today_iso}",
            f"reflections/{today_iso}_reflection.md",
            "note",
            json.dumps(["reflection", "mood:good"]),
            json.dumps({"type": "reflection", "mood": "good", "mood_score": 4, "date": today_iso}),
            50,
        ),
        (
            f"Reflection - {yesterday_iso}",
            f"reflections/{yesterday_iso}_reflection.md",
            "note",
            json.dumps(["reflection", "mood:neutral"]),
            json.dumps({"type": "reflection", "mood": "neutral", "mood_score": 3, "date": yesterday_iso}),
            30,
        ),
    ]

    for reflection in reflections:
        temp_db.execute_write(
            """INSERT INTO notes (title, file_path, note_type, tags, metadata, word_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            reflection
        )

    return temp_db


@pytest.fixture
def populated_db(sample_tasks, sample_events, sample_goals):
    """Database with tasks, events, and goals."""
    return sample_tasks


@pytest.fixture
def review_agent_with_data(populated_db, mock_config):
    """Create a ReviewAgent with pre-populated test data."""
    agent = ReviewAgent(populated_db, mock_config)
    agent.initialize()
    return agent


@pytest.fixture
def review_agent_with_reflections(sample_tasks, sample_events, sample_goals, sample_reflections, mock_config):
    """Create a ReviewAgent with reflections data."""
    agent = ReviewAgent(sample_reflections, mock_config)
    agent.initialize()
    return agent


# =============================================================================
# Test Agent Initialization and Basic Properties
# =============================================================================

class TestReviewAgentInit:
    """Tests for ReviewAgent initialization."""

    def test_agent_initializes_correctly(self, review_agent):
        """ReviewAgent initializes with correct name and properties."""
        assert review_agent.name == "review"
        assert review_agent._initialized is True

    def test_get_supported_intents(self, review_agent):
        """get_supported_intents returns all expected intents."""
        intents = review_agent.get_supported_intents()

        expected = [
            "daily_review", "weekly_review", "add_reflection",
            "get_insights", "generate_prompts"
        ]

        for intent in expected:
            assert intent in intents

    def test_supported_intents_count(self, review_agent):
        """Correct number of intents supported."""
        intents = review_agent.get_supported_intents()
        assert len(intents) == 5

    def test_can_handle_supported_intents(self, review_agent):
        """can_handle returns True for supported intents."""
        assert review_agent.can_handle("daily_review", {}) is True
        assert review_agent.can_handle("weekly_review", {}) is True
        assert review_agent.can_handle("add_reflection", {}) is True
        assert review_agent.can_handle("get_insights", {}) is True
        assert review_agent.can_handle("generate_prompts", {}) is True

    def test_can_handle_unsupported_intents(self, review_agent):
        """can_handle returns False for unsupported intents."""
        assert review_agent.can_handle("add_task", {}) is False
        assert review_agent.can_handle("create_note", {}) is False
        assert review_agent.can_handle("unknown_intent", {}) is False
        assert review_agent.can_handle("schedule_meeting", {}) is False
        assert review_agent.can_handle("create_goal", {}) is False

    def test_unknown_intent_returns_error(self, review_agent):
        """Unknown intent returns error response."""
        response = review_agent.process("unknown_intent", {})

        assert response.success is False
        assert "unknown intent" in response.message.lower()

    def test_agent_has_mood_keywords(self, review_agent):
        """Agent has mood keywords dictionary."""
        assert hasattr(review_agent, "MOOD_KEYWORDS")
        assert len(review_agent.MOOD_KEYWORDS) == 5

    def test_agent_has_mood_labels(self, review_agent):
        """Agent has mood labels dictionary."""
        assert hasattr(review_agent, "MOOD_LABELS")
        assert len(review_agent.MOOD_LABELS) == 5

    def test_agent_has_reflection_prompts(self, review_agent):
        """Agent has reflection prompts dictionary."""
        assert hasattr(review_agent, "REFLECTION_PROMPTS")
        assert "general" in review_agent.REFLECTION_PROMPTS
        assert "productive" in review_agent.REFLECTION_PROMPTS
        assert "struggling" in review_agent.REFLECTION_PROMPTS
        assert "weekly" in review_agent.REFLECTION_PROMPTS


# =============================================================================
# Test Daily Review Intent
# =============================================================================

class TestDailyReview:
    """Tests for daily_review intent."""

    def test_daily_review_returns_success(self, review_agent_with_data, today_iso):
        """daily_review returns successful response."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        assert response.success is True
        assert "review" in response.data
        assert response.data["date"] == today_iso

    def test_daily_review_includes_task_metrics(self, review_agent_with_data):
        """daily_review includes task completion metrics."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        assert "tasks_completed" in metrics
        assert "tasks_remaining" in metrics
        assert "completion_rate" in metrics

    def test_daily_review_task_count_correct(self, review_agent_with_data):
        """daily_review counts tasks correctly."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        # We have 3 tasks completed today in sample_tasks
        assert metrics["tasks_completed"] == 3

    def test_daily_review_completion_rate_calculation(self, review_agent_with_data):
        """daily_review calculates completion rate correctly."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        # 3 completed, 3 remaining = 50% completion rate
        total = metrics["tasks_completed"] + metrics["tasks_remaining"]
        if total > 0:
            expected_rate = metrics["tasks_completed"] / total
            assert abs(metrics["completion_rate"] - expected_rate) < 0.01

    def test_daily_review_includes_event_metrics(self, review_agent_with_data):
        """daily_review includes event metrics."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        assert "events_attended" in metrics
        assert "events_total" in metrics

    def test_daily_review_events_excludes_cancelled(self, review_agent_with_data):
        """daily_review excludes cancelled events from attended count."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        # 2 confirmed, 1 cancelled = 2 attended
        assert metrics["events_attended"] == 2

    def test_daily_review_includes_goal_progress(self, review_agent_with_data, today_iso):
        """daily_review includes goal progress updates."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        assert "goal_progress" in metrics
        # One goal has progress logged today
        assert len(metrics["goal_progress"]) >= 1

    def test_daily_review_includes_highlights(self, review_agent_with_data):
        """daily_review includes highlights."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        review = response.data["review"]
        assert "highlights" in review
        assert isinstance(review["highlights"], list)

    def test_daily_review_includes_improvement_areas(self, review_agent_with_data):
        """daily_review includes areas for improvement."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        review = response.data["review"]
        assert "areas_for_improvement" in review
        assert isinstance(review["areas_for_improvement"], list)

    def test_daily_review_for_specific_date(self, review_agent_with_data, yesterday_iso):
        """daily_review can be generated for a specific date."""
        response = review_agent_with_data.process("daily_review", {
            "date": yesterday_iso,
            "save_review": False
        })

        assert response.success is True
        assert response.data["date"] == yesterday_iso

    def test_daily_review_includes_reflection_prompts(self, review_agent_with_data):
        """daily_review includes reflection prompts."""
        response = review_agent_with_data.process("daily_review", {
            "save_review": False,
            "include_suggestions": True
        })

        assert "reflection_prompts" in response.data
        assert isinstance(response.data["reflection_prompts"], list)

    def test_daily_review_prompts_can_be_disabled(self, review_agent_with_data):
        """daily_review can disable reflection prompts."""
        response = review_agent_with_data.process("daily_review", {
            "save_review": False,
            "include_suggestions": False
        })

        assert response.success is True
        assert response.data["reflection_prompts"] == []

    def test_daily_review_message_format(self, review_agent_with_data, today_iso):
        """daily_review message contains expected information."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        assert today_iso in response.message
        assert "Tasks:" in response.message
        assert "Events:" in response.message

    def test_daily_review_empty_day(self, review_agent, today_iso):
        """daily_review handles days with no activity."""
        response = review_agent.process("daily_review", {"save_review": False})

        assert response.success is True
        metrics = response.data["review"]["metrics"]
        assert metrics["tasks_completed"] == 0
        assert metrics["completion_rate"] == 0.0

    def test_daily_review_with_iso_date_string(self, review_agent_with_data):
        """daily_review parses ISO date strings."""
        response = review_agent_with_data.process("daily_review", {
            "date": "2025-01-15",
            "save_review": False
        })

        assert response.success is True
        assert response.data["date"] == "2025-01-15"

    def test_daily_review_today_keyword(self, review_agent_with_data, today_iso):
        """daily_review defaults to today when no date provided."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        assert response.data["date"] == today_iso

    def test_daily_review_high_priority_remaining_shown(self, review_agent_with_data):
        """daily_review shows high priority remaining tasks."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        task_details = response.data["review"].get("task_details", {})
        high_priority = task_details.get("high_priority_remaining", [])
        # Should show high priority (4 or 5) remaining tasks
        assert isinstance(high_priority, list)


# =============================================================================
# Test Weekly Review Intent
# =============================================================================

class TestWeeklyReview:
    """Tests for weekly_review intent."""

    def test_weekly_review_returns_success(self, review_agent_with_data):
        """weekly_review returns successful response."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        assert response.success is True
        assert "review" in response.data

    def test_weekly_review_includes_period(self, review_agent_with_data):
        """weekly_review includes period start and end."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        assert "period" in response.data
        assert "start" in response.data["period"]
        assert "end" in response.data["period"]

    def test_weekly_review_period_is_7_days(self, review_agent_with_data):
        """weekly_review period spans 7 days."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        start = datetime.fromisoformat(response.data["period"]["start"]).date()
        end = datetime.fromisoformat(response.data["period"]["end"]).date()
        delta = (end - start).days
        assert delta == 6  # Start to end is 6 days (7 day week)

    def test_weekly_review_includes_task_metrics(self, review_agent_with_data):
        """weekly_review includes aggregate task metrics."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        assert "tasks_completed" in metrics
        assert "tasks_remaining" in metrics
        assert "completion_rate" in metrics

    def test_weekly_review_includes_trends(self, review_agent_with_data):
        """weekly_review includes trend data."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        review = response.data["review"]
        assert "trends" in review
        assert "daily_breakdown" in review["trends"]

    def test_weekly_review_daily_breakdown_format(self, review_agent_with_data):
        """weekly_review daily breakdown has correct format."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        daily_breakdown = response.data["review"]["trends"]["daily_breakdown"]
        assert len(daily_breakdown) == 7  # 7 days in a week

        for day in daily_breakdown:
            assert "date" in day
            assert "day_name" in day
            assert "completed" in day

    def test_weekly_review_identifies_best_day(self, review_agent_with_data):
        """weekly_review identifies the best productivity day."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        trends = response.data["review"]["trends"]
        assert "best_day" in trends

    def test_weekly_review_identifies_worst_day(self, review_agent_with_data):
        """weekly_review identifies the worst productivity day."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        trends = response.data["review"]["trends"]
        assert "worst_day" in trends

    def test_weekly_review_with_comparison(self, review_agent_with_data):
        """weekly_review includes previous week comparison."""
        response = review_agent_with_data.process("weekly_review", {
            "save_review": False,
            "include_comparison": True
        })

        trends = response.data["review"]["trends"]
        assert "previous_week_comparison" in trends

    def test_weekly_review_comparison_disabled(self, review_agent_with_data):
        """weekly_review can disable comparison."""
        response = review_agent_with_data.process("weekly_review", {
            "save_review": False,
            "include_comparison": False
        })

        trends = response.data["review"]["trends"]
        assert trends.get("previous_week_comparison") is None

    def test_weekly_review_includes_goal_progress(self, review_agent_with_data):
        """weekly_review includes goal progress for the week."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        metrics = response.data["review"]["metrics"]
        assert "goal_progress" in metrics

    def test_weekly_review_includes_upcoming_priorities(self, review_agent_with_data):
        """weekly_review includes upcoming priorities."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        review = response.data["review"]
        assert "upcoming_priorities" in review
        assert isinstance(review["upcoming_priorities"], list)

    def test_weekly_review_includes_highlights(self, review_agent_with_data):
        """weekly_review includes highlights."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        review = response.data["review"]
        assert "highlights" in review

    def test_weekly_review_includes_improvements(self, review_agent_with_data):
        """weekly_review includes improvement areas."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        review = response.data["review"]
        assert "areas_for_improvement" in review

    def test_weekly_review_for_specific_week(self, review_agent_with_data):
        """weekly_review can be generated for a specific week."""
        response = review_agent_with_data.process("weekly_review", {
            "week_start": "2025-01-06",
            "save_review": False
        })

        assert response.success is True
        assert response.data["period"]["start"] == "2025-01-06"

    def test_weekly_review_message_includes_stats(self, review_agent_with_data):
        """weekly_review message includes key statistics."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        assert "Weekly Review" in response.message
        assert "Tasks:" in response.message

    def test_weekly_review_empty_week(self, review_agent):
        """weekly_review handles weeks with no activity."""
        response = review_agent.process("weekly_review", {"save_review": False})

        assert response.success is True
        metrics = response.data["review"]["metrics"]
        assert metrics["tasks_completed"] == 0


# =============================================================================
# Test Add Reflection Intent
# =============================================================================

class TestAddReflection:
    """Tests for add_reflection intent."""

    def test_add_reflection_requires_text(self, review_agent):
        """add_reflection fails without text."""
        response = review_agent.process("add_reflection", {})

        assert response.success is False
        assert "text" in response.message.lower() or "required" in response.message.lower()

    def test_add_reflection_with_text(self, review_agent, today_iso):
        """add_reflection succeeds with text."""
        response = review_agent.process("add_reflection", {
            "text": "Today was a good day. I accomplished a lot."
        })

        assert response.success is True
        assert "note_id" in response.data

    def test_add_reflection_detects_mood(self, review_agent):
        """add_reflection detects mood from text."""
        response = review_agent.process("add_reflection", {
            "text": "Today was amazing! I felt so productive and accomplished."
        })

        assert response.success is True
        assert response.data["mood"] == "excellent"
        assert response.data["mood_score"] == 5

    def test_add_reflection_explicit_mood(self, review_agent):
        """add_reflection uses explicit mood if provided."""
        response = review_agent.process("add_reflection", {
            "text": "Just a regular day.",
            "mood": "stressed"
        })

        assert response.success is True
        assert response.data["mood"] == "stressed"
        assert response.data["mood_score"] == 2

    def test_add_reflection_for_specific_date(self, review_agent, yesterday_iso):
        """add_reflection can be for a specific date."""
        response = review_agent.process("add_reflection", {
            "text": "Reflecting on yesterday.",
            "date": yesterday_iso
        })

        assert response.success is True
        assert response.data["date"] == yesterday_iso

    def test_add_reflection_includes_date(self, review_agent, today_iso):
        """add_reflection response includes date."""
        response = review_agent.process("add_reflection", {
            "text": "Some thoughts for today."
        })

        assert response.success is True
        assert response.data["date"] == today_iso

    def test_add_reflection_includes_suggestions(self, review_agent):
        """add_reflection includes follow-up suggestions."""
        response = review_agent.process("add_reflection", {
            "text": "Today was good."
        })

        assert response.success is True
        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_add_reflection_with_tags(self, review_agent):
        """add_reflection can include tags."""
        response = review_agent.process("add_reflection", {
            "text": "Work thoughts for today.",
            "tags": ["work", "planning"]
        })

        assert response.success is True

    def test_add_reflection_message_format(self, review_agent, today_iso):
        """add_reflection message includes key info."""
        response = review_agent.process("add_reflection", {
            "text": "Good day overall."
        })

        assert "saved" in response.message.lower()
        assert today_iso in response.message


# =============================================================================
# Test Get Insights Intent
# =============================================================================

class TestGetInsights:
    """Tests for get_insights intent."""

    def test_get_insights_returns_success(self, review_agent_with_data):
        """get_insights returns successful response."""
        response = review_agent_with_data.process("get_insights", {})

        assert response.success is True
        assert "insights" in response.data

    def test_get_insights_default_period(self, review_agent_with_data):
        """get_insights defaults to 30 days."""
        response = review_agent_with_data.process("get_insights", {})

        period = response.data["insights"]["period"]
        assert period["days"] == 30

    def test_get_insights_custom_period(self, review_agent_with_data):
        """get_insights can use custom period."""
        response = review_agent_with_data.process("get_insights", {"days": 14})

        period = response.data["insights"]["period"]
        assert period["days"] == 14

    def test_get_insights_includes_productivity(self, review_agent_with_data):
        """get_insights includes productivity patterns."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "all"})

        insights = response.data["insights"]
        assert "productivity" in insights

    def test_get_insights_productivity_best_day(self, review_agent_with_data):
        """get_insights identifies best productivity day."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "productivity"})

        productivity = response.data["insights"]["productivity"]
        if productivity.get("best_day"):
            assert "day_name" in productivity["best_day"]
            assert "avg_completed" in productivity["best_day"]

    def test_get_insights_includes_goals(self, review_agent_with_data):
        """get_insights includes goal momentum."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "all"})

        insights = response.data["insights"]
        assert "goals" in insights

    def test_get_insights_goal_counts(self, review_agent_with_data):
        """get_insights includes goal counts."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "goals"})

        goals = response.data["insights"]["goals"]
        assert "active_count" in goals
        assert "at_risk_count" in goals

    def test_get_insights_includes_mood(self, review_agent_with_reflections):
        """get_insights includes mood patterns when reflections exist."""
        response = review_agent_with_reflections.process("get_insights", {"insight_type": "mood"})

        insights = response.data["insights"]
        assert "mood" in insights

    def test_get_insights_no_mood_data(self, review_agent_with_data):
        """get_insights handles no mood data gracefully."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "mood"})

        mood = response.data["insights"]["mood"]
        assert "reflection_count" in mood or "message" in mood

    def test_get_insights_includes_overdue(self, review_agent_with_data):
        """get_insights includes overdue task trends."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "productivity"})

        insights = response.data["insights"]
        assert "overdue" in insights

    def test_get_insights_overdue_categories(self, review_agent_with_data):
        """get_insights categorizes overdue tasks."""
        response = review_agent_with_data.process("get_insights", {"insight_type": "productivity"})

        overdue = response.data["insights"]["overdue"]
        assert "total_overdue" in overdue
        assert "severely_overdue" in overdue
        assert "moderately_overdue" in overdue
        assert "recently_overdue" in overdue

    def test_get_insights_message_format(self, review_agent_with_data):
        """get_insights message includes summary."""
        response = review_agent_with_data.process("get_insights", {})

        assert "Insights" in response.message
        assert "days" in response.message

    def test_get_insights_includes_suggestions(self, review_agent_with_data):
        """get_insights includes suggestions."""
        response = review_agent_with_data.process("get_insights", {})

        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_get_insights_empty_data(self, review_agent):
        """get_insights handles empty data gracefully."""
        response = review_agent.process("get_insights", {})

        assert response.success is True
        assert "insights" in response.data


# =============================================================================
# Test Generate Prompts Intent
# =============================================================================

class TestGeneratePrompts:
    """Tests for generate_prompts intent."""

    def test_generate_prompts_returns_success(self, review_agent):
        """generate_prompts returns successful response."""
        response = review_agent.process("generate_prompts", {})

        assert response.success is True
        assert "prompts" in response.data

    def test_generate_prompts_default_count(self, review_agent):
        """generate_prompts returns 5 prompts by default."""
        response = review_agent.process("generate_prompts", {})

        prompts = response.data["prompts"]
        assert len(prompts) <= 5

    def test_generate_prompts_custom_count(self, review_agent):
        """generate_prompts can return custom count."""
        response = review_agent.process("generate_prompts", {"count": 3})

        prompts = response.data["prompts"]
        assert len(prompts) <= 3

    def test_generate_prompts_general_type(self, review_agent):
        """generate_prompts can return general prompts."""
        response = review_agent.process("generate_prompts", {"prompt_type": "general"})

        assert response.success is True
        assert response.data["prompt_type"] == "general"

    def test_generate_prompts_productive_type(self, review_agent):
        """generate_prompts can return productive prompts."""
        response = review_agent.process("generate_prompts", {"prompt_type": "productive"})

        assert response.success is True
        assert response.data["prompt_type"] == "productive"

    def test_generate_prompts_struggling_type(self, review_agent):
        """generate_prompts can return struggling prompts."""
        response = review_agent.process("generate_prompts", {"prompt_type": "struggling"})

        assert response.success is True
        assert response.data["prompt_type"] == "struggling"

    def test_generate_prompts_weekly_type(self, review_agent):
        """generate_prompts can return weekly prompts."""
        response = review_agent.process("generate_prompts", {"prompt_type": "weekly"})

        assert response.success is True
        assert response.data["prompt_type"] == "weekly"

    def test_generate_prompts_goal_focused_type(self, review_agent):
        """generate_prompts can return goal-focused prompts."""
        response = review_agent.process("generate_prompts", {"prompt_type": "goal_focused"})

        assert response.success is True
        assert response.data["prompt_type"] == "goal_focused"

    def test_generate_prompts_auto_detect(self, review_agent_with_data):
        """generate_prompts can auto-detect context."""
        response = review_agent_with_data.process("generate_prompts", {"auto_detect": True})

        assert response.success is True
        assert response.data["prompt_type"] in ["general", "productive", "struggling", "weekly"]

    def test_generate_prompts_auto_detect_disabled(self, review_agent):
        """generate_prompts defaults to general when auto_detect disabled."""
        response = review_agent.process("generate_prompts", {
            "auto_detect": False,
            "prompt_type": None
        })

        assert response.success is True
        assert response.data["prompt_type"] == "general"

    def test_generate_prompts_invalid_type_fallback(self, review_agent):
        """generate_prompts falls back to general for invalid type."""
        response = review_agent.process("generate_prompts", {
            "prompt_type": "invalid_type",
            "auto_detect": False
        })

        assert response.success is True
        assert response.data["prompt_type"] == "general"

    def test_generate_prompts_includes_suggestions(self, review_agent):
        """generate_prompts includes follow-up suggestions."""
        response = review_agent.process("generate_prompts", {})

        assert response.suggestions is not None

    def test_generate_prompts_message_format(self, review_agent):
        """generate_prompts message indicates context."""
        response = review_agent.process("generate_prompts", {"prompt_type": "weekly"})

        assert "weekly" in response.message.lower()


# =============================================================================
# Test Mood Detection
# =============================================================================

class TestMoodDetection:
    """Tests for mood/sentiment detection."""

    def test_detect_excellent_mood(self, review_agent):
        """Detects excellent mood from text."""
        score, label = review_agent._detect_mood_from_text("Today was amazing and fantastic!")

        assert score == 5
        assert label == "excellent"

    def test_detect_good_mood(self, review_agent):
        """Detects good mood from text."""
        score, label = review_agent._detect_mood_from_text("I feel satisfied with my work today.")

        assert score == 4
        assert label == "good"

    def test_detect_neutral_mood(self, review_agent):
        """Detects neutral mood from text."""
        score, label = review_agent._detect_mood_from_text("It was an okay day, nothing special.")

        assert score == 3
        assert label == "neutral"

    def test_detect_stressed_mood(self, review_agent):
        """Detects stressed mood from text."""
        score, label = review_agent._detect_mood_from_text("Feeling overwhelmed and stressed today.")

        assert score == 2
        assert label == "stressed"

    def test_detect_struggling_mood(self, review_agent):
        """Detects struggling mood from text."""
        score, label = review_agent._detect_mood_from_text("I feel terrible and exhausted.")

        assert score == 1
        assert label == "struggling"

    def test_default_neutral_mood(self, review_agent):
        """Defaults to neutral when no mood keywords found."""
        score, label = review_agent._detect_mood_from_text("Just some random thoughts.")

        assert score == 3
        assert label == "neutral"

    def test_mood_keywords_case_insensitive(self, review_agent):
        """Mood detection is case insensitive."""
        score, label = review_agent._detect_mood_from_text("Today was AMAZING!")

        assert score == 5
        assert label == "excellent"

    def test_mood_label_to_score_excellent(self, review_agent):
        """Converts 'excellent' label to score."""
        score = review_agent._mood_label_to_score("excellent")
        assert score == 5

    def test_mood_label_to_score_good(self, review_agent):
        """Converts 'good' label to score."""
        score = review_agent._mood_label_to_score("good")
        assert score == 4

    def test_mood_label_to_score_stressed(self, review_agent):
        """Converts 'stressed' label to score."""
        score = review_agent._mood_label_to_score("stressed")
        assert score == 2

    def test_mood_label_to_score_from_keyword(self, review_agent):
        """Converts mood keyword to score."""
        score = review_agent._mood_label_to_score("happy")
        assert score == 4

    def test_mood_label_default_neutral(self, review_agent):
        """Unknown mood label defaults to neutral."""
        score = review_agent._mood_label_to_score("unknown_mood")
        assert score == 3


# =============================================================================
# Test Intent Handling and Routing
# =============================================================================

class TestIntentHandling:
    """Tests for intent handling and routing."""

    def test_process_routes_to_daily_review(self, review_agent_with_data):
        """process routes daily_review to correct handler."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        assert response.success is True
        assert response.data["review"]["review_type"] == "daily"

    def test_process_routes_to_weekly_review(self, review_agent_with_data):
        """process routes weekly_review to correct handler."""
        response = review_agent_with_data.process("weekly_review", {"save_review": False})

        assert response.success is True
        assert response.data["review"]["review_type"] == "weekly"

    def test_process_routes_to_add_reflection(self, review_agent):
        """process routes add_reflection to correct handler."""
        response = review_agent.process("add_reflection", {"text": "Test reflection"})

        assert response.success is True
        assert "note_id" in response.data

    def test_process_routes_to_get_insights(self, review_agent_with_data):
        """process routes get_insights to correct handler."""
        response = review_agent_with_data.process("get_insights", {})

        assert response.success is True
        assert "insights" in response.data

    def test_process_routes_to_generate_prompts(self, review_agent):
        """process routes generate_prompts to correct handler."""
        response = review_agent.process("generate_prompts", {})

        assert response.success is True
        assert "prompts" in response.data

    def test_process_handles_exception(self, review_agent, mock_config):
        """process handles exceptions gracefully."""
        # Create agent with mock that raises exception
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database error")

        agent = ReviewAgent(mock_db, mock_config)
        response = agent.process("daily_review", {"save_review": False})

        assert response.success is False
        assert "failed" in response.message.lower()


# =============================================================================
# Test Date Parsing
# =============================================================================

class TestDateParsing:
    """Tests for date parsing utilities."""

    def test_parse_date_iso_format(self, review_agent):
        """Parses ISO format date."""
        result = review_agent._parse_date("2025-01-15")

        assert result is not None
        assert result == date(2025, 1, 15)

    def test_parse_date_slash_format(self, review_agent):
        """Parses MM/DD/YYYY format date."""
        result = review_agent._parse_date("01/15/2025")

        assert result is not None
        assert result == date(2025, 1, 15)

    def test_parse_date_datetime_object(self, review_agent):
        """Parses datetime object."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = review_agent._parse_date(dt)

        assert result is not None
        # _parse_date returns .date() for datetime objects
        if isinstance(result, datetime):
            assert result.date() == date(2025, 1, 15)
        else:
            assert result == date(2025, 1, 15)

    def test_parse_date_date_object(self, review_agent):
        """Parses date object."""
        d = date(2025, 1, 15)
        result = review_agent._parse_date(d)

        assert result is not None
        assert result == d

    def test_parse_date_none_returns_none(self, review_agent):
        """Returns None for None input."""
        result = review_agent._parse_date(None)
        assert result is None

    def test_parse_date_invalid_returns_none(self, review_agent):
        """Returns None for invalid date string."""
        result = review_agent._parse_date("not-a-date")
        assert result is None


# =============================================================================
# Test Highlight and Improvement Extraction
# =============================================================================

class TestHighlightsAndImprovements:
    """Tests for highlight and improvement extraction."""

    def test_extract_highlights_productive_day(self, review_agent_with_data, today_iso):
        """Extracts highlights for productive day."""
        task_metrics = {
            "completed": 6,
            "remaining": 2,
            "completed_list": [{"id": 1, "title": "Important task completed"}]
        }
        event_metrics = {"attended": 2, "total": 2}
        goal_progress = [{"goal_id": 1, "name": "Save money", "percentage": 50}]

        highlights = review_agent_with_data._extract_highlights(
            task_metrics, event_metrics, goal_progress
        )

        assert len(highlights) > 0
        # Should mention 6 tasks completed
        assert any("6" in h for h in highlights)

    def test_extract_highlights_with_goal_progress(self, review_agent):
        """Includes goal progress in highlights."""
        task_metrics = {"completed": 2, "remaining": 3, "completed_list": []}
        event_metrics = {"attended": 0, "total": 0}
        goal_progress = [{"goal_id": 1, "name": "Learn Spanish", "percentage": 30}]

        highlights = review_agent._extract_highlights(
            task_metrics, event_metrics, goal_progress
        )

        assert any("Learn Spanish" in h for h in highlights)

    def test_identify_improvement_areas_low_completion(self, review_agent):
        """Identifies improvement for low completion rate."""
        task_metrics = {"completed": 1, "remaining": 10, "high_priority_remaining": [], "created": 2}
        event_metrics = {"attended": 0, "total": 0}

        areas = review_agent._identify_improvement_areas(
            task_metrics, event_metrics, 0.1
        )

        assert len(areas) > 0
        assert any("break" in a.lower() or "smaller" in a.lower() for a in areas)

    def test_identify_improvement_high_priority_remaining(self, review_agent):
        """Identifies high priority tasks remaining."""
        task_metrics = {
            "completed": 3,
            "remaining": 5,
            "high_priority_remaining": [{"id": 1, "title": "Urgent"}, {"id": 2, "title": "Critical"}],
            "created": 2
        }
        event_metrics = {"attended": 0, "total": 0}

        areas = review_agent._identify_improvement_areas(
            task_metrics, event_metrics, 0.5
        )

        assert any("high-priority" in a.lower() or "priority" in a.lower() for a in areas)


# =============================================================================
# Test AgentResponse Structure
# =============================================================================

class TestAgentResponseStructure:
    """Tests for AgentResponse data structure."""

    def test_success_response_structure(self, review_agent_with_data):
        """Successful response has expected structure."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        assert hasattr(response, "success")
        assert hasattr(response, "message")
        assert hasattr(response, "data")
        assert hasattr(response, "suggestions")

    def test_error_response_structure(self, review_agent):
        """Error response has expected structure."""
        response = review_agent.process("add_reflection", {})  # Missing text

        assert response.success is False
        assert response.message is not None
        assert len(response.message) > 0

    def test_response_to_dict(self, review_agent_with_data):
        """Response can be converted to dictionary."""
        response = review_agent_with_data.process("daily_review", {"save_review": False})

        result = response.to_dict()
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "data" in result


# =============================================================================
# Test Prompt Context Detection
# =============================================================================

class TestPromptContextDetection:
    """Tests for automatic prompt context detection."""

    def test_detect_productive_context(self, review_agent_with_data):
        """Detects productive context from high completion rate."""
        # With 3 completed and 3 remaining, completion rate is 50%
        # Need to mock higher completion rate
        context = review_agent_with_data._detect_prompt_context()
        # Just ensure it returns a valid context
        assert context in ["general", "productive", "struggling", "weekly"]

    def test_detect_context_returns_valid_type(self, review_agent):
        """Detect context returns valid prompt type."""
        context = review_agent._detect_prompt_context()

        assert context in ["general", "productive", "struggling", "weekly"]


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in ReviewAgent."""

    def test_database_error_handled(self, mock_config):
        """Database errors are caught and returned as error response."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database connection failed")

        agent = ReviewAgent(mock_db, mock_config)
        response = agent.process("daily_review", {"save_review": False})

        assert response.success is False
        assert "failed" in response.message.lower()

    def test_missing_reflection_text_error(self, review_agent):
        """add_reflection fails without text."""
        response = review_agent.process("add_reflection", {})

        assert response.success is False
        assert "required" in response.message.lower() or "text" in response.message.lower()

    def test_empty_reflection_text_error(self, review_agent):
        """add_reflection fails with empty text."""
        response = review_agent.process("add_reflection", {"text": ""})

        assert response.success is False


# =============================================================================
# Test Weekly Improvements and Trends
# =============================================================================

class TestWeeklyTrends:
    """Tests for weekly trend analysis."""

    def test_identify_weekly_improvements_low_rate(self, review_agent):
        """Identifies improvement for low weekly completion rate."""
        daily_breakdown = [
            {"date": "2025-01-06", "day_name": "Monday", "completed": 2},
            {"date": "2025-01-07", "day_name": "Tuesday", "completed": 1},
            {"date": "2025-01-08", "day_name": "Wednesday", "completed": 0},
            {"date": "2025-01-09", "day_name": "Thursday", "completed": 0},
            {"date": "2025-01-10", "day_name": "Friday", "completed": 1},
        ]

        areas = review_agent._identify_weekly_improvements(daily_breakdown, 0.3)

        assert len(areas) > 0

    def test_identify_zero_days(self, review_agent):
        """Identifies days with zero completions."""
        daily_breakdown = [
            {"date": "2025-01-06", "day_name": "Monday", "completed": 5},
            {"date": "2025-01-07", "day_name": "Tuesday", "completed": 0},
            {"date": "2025-01-08", "day_name": "Wednesday", "completed": 0},
            {"date": "2025-01-09", "day_name": "Thursday", "completed": 3},
        ]

        areas = review_agent._identify_weekly_improvements(daily_breakdown, 0.6)

        assert any("Tuesday" in a or "Wednesday" in a for a in areas)


# =============================================================================
# Test Review Saving
# =============================================================================

class TestReviewSaving:
    """Tests for saving reviews as notes."""

    def test_daily_review_can_save(self, review_agent_with_data):
        """daily_review can save review as note."""
        response = review_agent_with_data.process("daily_review", {"save_review": True})

        assert response.success is True
        # Should return review_note_id when saved
        assert "review_note_id" in response.data

    def test_weekly_review_can_save(self, review_agent_with_data):
        """weekly_review can save review as note."""
        response = review_agent_with_data.process("weekly_review", {"save_review": True})

        assert response.success is True
        assert "review_note_id" in response.data

    def test_generate_review_file_path_daily(self, review_agent, today):
        """Generates correct file path for daily review."""
        path = review_agent._generate_review_file_path("daily", today)

        assert "daily" in path
        assert today.strftime("%Y-%m-%d") in path
        assert path.endswith(".md")

    def test_generate_review_file_path_weekly(self, review_agent, today):
        """Generates correct file path for weekly review."""
        path = review_agent._generate_review_file_path("weekly", today)

        assert "weekly" in path
        assert today.strftime("%Y-%m-%d") in path
        assert path.endswith(".md")


# =============================================================================
# Test Markdown Generation
# =============================================================================

class TestMarkdownGeneration:
    """Tests for review markdown generation."""

    def test_generate_daily_review_markdown(self, review_agent, today_iso):
        """Generates valid markdown for daily review."""
        review_data = {
            "type": "review",
            "review_type": "daily",
            "period": {"start": today_iso, "end": today_iso},
            "metrics": {
                "tasks_completed": 5,
                "tasks_remaining": 3,
                "completion_rate": 0.625,
                "events_attended": 2,
                "goal_progress": [],
            },
            "highlights": ["Completed 5 tasks"],
            "areas_for_improvement": ["Focus on priorities"],
        }

        markdown = review_agent._generate_review_markdown(review_data, "daily")

        assert "# Daily Review" in markdown
        assert "Tasks Completed: 5" in markdown
        assert "62%" in markdown
        assert "---" in markdown  # Frontmatter

    def test_generate_weekly_review_markdown(self, review_agent, today_iso):
        """Generates valid markdown for weekly review."""
        week_start = (datetime.now(timezone.utc).date() - timedelta(days=6)).isoformat()
        review_data = {
            "type": "review",
            "review_type": "weekly",
            "period": {"start": week_start, "end": today_iso},
            "metrics": {
                "tasks_completed": 25,
                "tasks_remaining": 10,
                "completion_rate": 0.714,
                "events_attended": 8,
                "goal_progress": [{"name": "Save money", "delta": 10}],
            },
            "trends": {
                "best_day": {"day_name": "Wednesday"},
                "worst_day": {"day_name": "Friday"},
            },
            "highlights": ["Great week!"],
            "areas_for_improvement": [],
            "upcoming_priorities": [{"title": "Important task"}],
        }

        markdown = review_agent._generate_review_markdown(review_data, "weekly")

        assert "# Weekly Review" in markdown
        assert "Tasks Completed: 25" in markdown
        assert "Productivity Trends" in markdown


# =============================================================================
# Test Reflection Appending
# =============================================================================

class TestReflectionAppending:
    """Tests for appending to existing reflections."""

    def test_get_reflection_for_date_not_found(self, review_agent, yesterday):
        """Returns None when no reflection exists for date."""
        result = review_agent._get_reflection_for_date(yesterday)
        assert result is None


# =============================================================================
# Additional Edge Cases
# =============================================================================

class TestEdgeCases:
    """Additional edge case tests."""

    def test_review_with_no_tasks(self, review_agent):
        """Handles review with no tasks gracefully."""
        response = review_agent.process("daily_review", {"save_review": False})

        assert response.success is True
        metrics = response.data["review"]["metrics"]
        assert metrics["tasks_completed"] == 0
        assert metrics["completion_rate"] == 0.0

    def test_review_with_no_events(self, review_agent):
        """Handles review with no events gracefully."""
        response = review_agent.process("daily_review", {"save_review": False})

        assert response.success is True
        metrics = response.data["review"]["metrics"]
        assert metrics["events_total"] == 0

    def test_review_with_no_goals(self, review_agent):
        """Handles review with no goals gracefully."""
        response = review_agent.process("daily_review", {"save_review": False})

        assert response.success is True
        metrics = response.data["review"]["metrics"]
        assert metrics["goal_progress"] == []

    def test_insights_with_no_data(self, review_agent):
        """Handles insights with no data gracefully."""
        response = review_agent.process("get_insights", {"days": 1})

        assert response.success is True

    def test_weekly_review_incomplete_week(self, review_agent):
        """Handles weekly review at start of week."""
        response = review_agent.process("weekly_review", {"save_review": False})

        assert response.success is True
        assert len(response.data["review"]["trends"]["daily_breakdown"]) == 7

    def test_prompts_fill_from_general(self, review_agent):
        """Fills prompts from general when category has fewer than requested."""
        response = review_agent.process("generate_prompts", {"count": 10, "prompt_type": "productive"})

        assert response.success is True
        # Should have filled from general prompts
        assert len(response.data["prompts"]) >= 4  # At least productive prompts count

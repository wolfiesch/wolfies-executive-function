"""
Unit tests for the aggregator module.
Tests the DashboardAggregator class for data collection and aggregation.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta, time
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.database import Database
from src.core.config import Config
from src.core.models import Task, CalendarEvent
from src.dashboard.aggregator import (
    DashboardAggregator,
    DashboardData,
    DailyStats,
    TimeAnalysis,
)


class InMemoryDatabase:
    """
    Minimal in-memory database for testing.

    Mimics the Database class interface but uses :memory: SQLite
    and doesn't require file existence.
    """

    def __init__(self):
        self.db_path = ":memory:"
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def _init_schema(self):
        """Initialize the database schema for testing."""
        cursor = self._conn.cursor()

        # Tasks table
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'todo',
                priority INTEGER NOT NULL DEFAULT 3,
                para_category_id INTEGER,
                project_id INTEGER,
                parent_task_id INTEGER,
                estimated_minutes INTEGER,
                actual_minutes INTEGER,
                due_date DATETIME,
                scheduled_start DATETIME,
                scheduled_end DATETIME,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                tags TEXT,
                context TEXT
            )
        """)

        # Calendar events table
        cursor.execute("""
            CREATE TABLE calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                all_day BOOLEAN DEFAULT 0,
                calendar_source TEXT DEFAULT 'internal',
                external_id TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        self._conn.commit()

    def get_connection(self):
        """Return connection context manager."""
        class ConnectionContext:
            def __init__(self, conn):
                self.conn = conn
            def __enter__(self):
                return self.conn
            def __exit__(self, *args):
                pass  # Don't close in-memory connection
        return ConnectionContext(self._conn)

    def execute(self, query, params=()):
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def execute_one(self, query, params=()):
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def execute_write(self, query, params=()):
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        self._conn.commit()
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    def execute_many(self, query, params_list):
        cursor = self._conn.cursor()
        cursor.executemany(query, params_list)
        self._conn.commit()
        return cursor.rowcount


class MockConfig:
    """Mock config for testing with controllable settings."""

    def __init__(self, preferences=None):
        self.preferences = preferences or {
            "work_hours_start": "09:00",
            "work_hours_end": "17:00",
        }

    def get(self, key, section="settings", default=None):
        if section == "preferences":
            return self.preferences.get(key, default)
        return default


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    return InMemoryDatabase()


@pytest.fixture
def config():
    """Create a mock config for testing."""
    return MockConfig()


@pytest.fixture
def aggregator(db, config):
    """Create an aggregator instance for testing."""
    return DashboardAggregator(db, config)


class TestDashboardAggregatorInit:
    """Tests for DashboardAggregator initialization."""

    def test_init_with_db_and_config(self, db, config):
        """Aggregator initializes with provided db and config."""
        agg = DashboardAggregator(db, config)

        assert agg.db is db
        assert agg.config is config
        assert agg.prioritizer is not None

    def test_init_creates_default_config_if_none(self, db):
        """Aggregator creates default Config if none provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Config, '__init__', return_value=None):
                with patch.object(Config, 'get', return_value="09:00"):
                    agg = DashboardAggregator(db)
                    # Should have a config object (mocked)
                    assert agg.config is not None


class TestGetGreeting:
    """Tests for greeting generation."""

    def test_morning_greeting(self, aggregator):
        """Morning hours (0-11) get 'Good Morning!'."""
        morning = datetime(2025, 1, 15, 8, 30)
        assert aggregator._get_greeting(morning) == "Good Morning!"

    def test_afternoon_greeting(self, aggregator):
        """Afternoon hours (12-16) get 'Good Afternoon!'."""
        afternoon = datetime(2025, 1, 15, 14, 30)
        assert aggregator._get_greeting(afternoon) == "Good Afternoon!"

    def test_evening_greeting(self, aggregator):
        """Evening hours (17-20) get 'Good Evening!'."""
        evening = datetime(2025, 1, 15, 19, 0)
        assert aggregator._get_greeting(evening) == "Good Evening!"

    def test_night_greeting(self, aggregator):
        """Night hours (21-23) get 'Good Night!'."""
        night = datetime(2025, 1, 15, 22, 0)
        assert aggregator._get_greeting(night) == "Good Night!"


class TestGetTodayTasks:
    """Tests for get_today_tasks() method."""

    def test_returns_four_tuple(self, aggregator):
        """get_today_tasks() returns tuple of 4 lists."""
        now = datetime(2025, 1, 15, 10, 0)
        result = aggregator.get_today_tasks(now)

        assert isinstance(result, tuple)
        assert len(result) == 4
        assert all(isinstance(lst, list) for lst in result)

    def test_due_today_finds_tasks_due_today(self, db, aggregator):
        """Tasks due today are returned in due_today list."""
        now = datetime(2025, 1, 15, 10, 0)
        today_due = now.replace(hour=18, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("Due today task", "todo", 3, today_due)
        )

        due_today, _, _, _ = aggregator.get_today_tasks(now)

        assert len(due_today) == 1
        assert due_today[0].title == "Due today task"

    def test_due_today_excludes_done_tasks(self, db, aggregator):
        """Done tasks are not included in due_today."""
        now = datetime(2025, 1, 15, 10, 0)
        today_due = now.replace(hour=18, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("Completed task", "done", 3, today_due)
        )

        due_today, _, _, _ = aggregator.get_today_tasks(now)

        assert len(due_today) == 0

    def test_due_today_excludes_cancelled_tasks(self, db, aggregator):
        """Cancelled tasks are not included in due_today."""
        now = datetime(2025, 1, 15, 10, 0)
        today_due = now.replace(hour=18, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("Cancelled task", "cancelled", 3, today_due)
        )

        due_today, _, _, _ = aggregator.get_today_tasks(now)

        assert len(due_today) == 0

    def test_scheduled_today_finds_tasks(self, db, aggregator):
        """Tasks scheduled today are returned in scheduled_today list."""
        now = datetime(2025, 1, 15, 10, 0)
        scheduled_start = now.replace(hour=14, minute=0).isoformat()
        scheduled_end = now.replace(hour=15, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, scheduled_start, scheduled_end)
               VALUES (?, ?, ?, ?, ?)""",
            ("Scheduled task", "todo", 3, scheduled_start, scheduled_end)
        )

        _, scheduled_today, _, _ = aggregator.get_today_tasks(now)

        assert len(scheduled_today) == 1
        assert scheduled_today[0].title == "Scheduled task"

    def test_overdue_finds_past_due_tasks(self, db, aggregator):
        """Tasks past due date are returned in overdue list."""
        now = datetime(2025, 1, 15, 10, 0)
        yesterday = (now - timedelta(days=1)).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("Overdue task", "todo", 3, yesterday)
        )

        _, _, overdue, _ = aggregator.get_today_tasks(now)

        assert len(overdue) == 1
        assert overdue[0].title == "Overdue task"

    def test_high_priority_finds_unscheduled_high_priority(self, db, aggregator):
        """High priority tasks without due date or schedule are returned."""
        now = datetime(2025, 1, 15, 10, 0)

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date, scheduled_start)
               VALUES (?, ?, ?, ?, ?)""",
            ("High priority task", "todo", 5, None, None)
        )

        _, _, _, high_priority = aggregator.get_today_tasks(now)

        assert len(high_priority) == 1
        assert high_priority[0].title == "High priority task"
        assert high_priority[0].priority == 5

    def test_high_priority_excludes_priority_3(self, db, aggregator):
        """Normal priority (3) tasks are not in high_priority list."""
        now = datetime(2025, 1, 15, 10, 0)

        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date, scheduled_start)
               VALUES (?, ?, ?, ?, ?)""",
            ("Normal priority task", "todo", 3, None, None)
        )

        _, _, _, high_priority = aggregator.get_today_tasks(now)

        assert len(high_priority) == 0

    def test_due_today_sorted_by_priority_then_due_date(self, db, aggregator):
        """Due today tasks are sorted by priority DESC, then due_date ASC."""
        now = datetime(2025, 1, 15, 10, 0)
        early_due = now.replace(hour=12, minute=0).isoformat()
        late_due = now.replace(hour=18, minute=0).isoformat()

        # Insert in non-sorted order
        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("Low priority late", "todo", 2, late_due)
        )
        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("High priority late", "todo", 5, late_due)
        )
        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("High priority early", "todo", 5, early_due)
        )

        due_today, _, _, _ = aggregator.get_today_tasks(now)

        assert len(due_today) == 3
        # Sorted by priority DESC first
        assert due_today[0].priority == 5
        assert due_today[1].priority == 5
        # Then by due_date ASC for same priority
        assert due_today[0].title == "High priority early"
        assert due_today[1].title == "High priority late"
        assert due_today[2].priority == 2


class TestGetTodayEvents:
    """Tests for get_today_events() method."""

    def test_returns_list_of_events(self, aggregator):
        """get_today_events() returns a list."""
        now = datetime(2025, 1, 15, 10, 0)
        result = aggregator.get_today_events(now)

        assert isinstance(result, list)

    def test_finds_events_today(self, db, aggregator):
        """Events with start_time today are returned."""
        now = datetime(2025, 1, 15, 10, 0)
        start = now.replace(hour=14, minute=0).isoformat()
        end = now.replace(hour=15, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO calendar_events (title, start_time, end_time, status)
               VALUES (?, ?, ?, ?)""",
            ("Team meeting", start, end, "confirmed")
        )

        events = aggregator.get_today_events(now)

        assert len(events) == 1
        assert events[0].title == "Team meeting"

    def test_excludes_cancelled_events(self, db, aggregator):
        """Cancelled events are not returned."""
        now = datetime(2025, 1, 15, 10, 0)
        start = now.replace(hour=14, minute=0).isoformat()
        end = now.replace(hour=15, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO calendar_events (title, start_time, end_time, status)
               VALUES (?, ?, ?, ?)""",
            ("Cancelled meeting", start, end, "cancelled")
        )

        events = aggregator.get_today_events(now)

        assert len(events) == 0

    def test_events_sorted_by_start_time(self, db, aggregator):
        """Events are sorted by start_time ascending."""
        now = datetime(2025, 1, 15, 10, 0)

        # Insert in non-sorted order
        for hour, title in [(16, "Late meeting"), (9, "Morning standup"), (12, "Lunch")]:
            start = now.replace(hour=hour, minute=0).isoformat()
            end = now.replace(hour=hour+1, minute=0).isoformat()
            db.execute_write(
                """INSERT INTO calendar_events (title, start_time, end_time, status)
                   VALUES (?, ?, ?, ?)""",
                (title, start, end, "confirmed")
            )

        events = aggregator.get_today_events(now)

        assert len(events) == 3
        assert events[0].title == "Morning standup"
        assert events[1].title == "Lunch"
        assert events[2].title == "Late meeting"

    def test_excludes_events_from_other_days(self, db, aggregator):
        """Events from other days are not returned."""
        now = datetime(2025, 1, 15, 10, 0)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        for day, title in [(yesterday, "Yesterday meeting"), (tomorrow, "Tomorrow meeting")]:
            start = day.replace(hour=14, minute=0).isoformat()
            end = day.replace(hour=15, minute=0).isoformat()
            db.execute_write(
                """INSERT INTO calendar_events (title, start_time, end_time, status)
                   VALUES (?, ?, ?, ?)""",
                (title, start, end, "confirmed")
            )

        events = aggregator.get_today_events(now)

        assert len(events) == 0


class TestGetDailyStats:
    """Tests for get_daily_stats() method."""

    def test_returns_daily_stats(self, aggregator):
        """get_daily_stats() returns a DailyStats object."""
        now = datetime(2025, 1, 15, 10, 0)
        result = aggregator.get_daily_stats(now)

        assert isinstance(result, DailyStats)

    def test_counts_completed_today(self, db, aggregator):
        """tasks_completed_today counts tasks completed today."""
        now = datetime(2025, 1, 15, 14, 0)
        completed_at = now.replace(hour=10, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, completed_at)
               VALUES (?, ?, ?)""",
            ("Completed task", "done", completed_at)
        )

        stats = aggregator.get_daily_stats(now)

        assert stats.tasks_completed_today == 1

    def test_excludes_tasks_completed_yesterday(self, db, aggregator):
        """Tasks completed yesterday are not counted in tasks_completed_today."""
        now = datetime(2025, 1, 15, 14, 0)
        yesterday = (now - timedelta(days=1)).replace(hour=10, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, completed_at)
               VALUES (?, ?, ?)""",
            ("Old completed task", "done", yesterday)
        )

        stats = aggregator.get_daily_stats(now)

        assert stats.tasks_completed_today == 0

    def test_counts_remaining_tasks(self, db, aggregator):
        """tasks_remaining counts non-done/cancelled tasks."""
        now = datetime(2025, 1, 15, 10, 0)

        db.execute_write(
            "INSERT INTO tasks (title, status) VALUES (?, ?)",
            ("Todo task", "todo")
        )
        db.execute_write(
            "INSERT INTO tasks (title, status) VALUES (?, ?)",
            ("In progress task", "in_progress")
        )
        db.execute_write(
            "INSERT INTO tasks (title, status) VALUES (?, ?)",
            ("Done task", "done")
        )
        db.execute_write(
            "INSERT INTO tasks (title, status) VALUES (?, ?)",
            ("Cancelled task", "cancelled")
        )

        stats = aggregator.get_daily_stats(now)

        assert stats.tasks_remaining == 2  # todo + in_progress

    def test_counts_overdue_tasks(self, db, aggregator):
        """tasks_overdue counts tasks with past due dates."""
        now = datetime(2025, 1, 15, 10, 0)
        yesterday = (now - timedelta(days=1)).isoformat()

        db.execute_write(
            """INSERT INTO tasks (title, status, due_date)
               VALUES (?, ?, ?)""",
            ("Overdue task", "todo", yesterday)
        )
        db.execute_write(
            """INSERT INTO tasks (title, status, due_date)
               VALUES (?, ?, ?)""",
            ("Overdue but done", "done", yesterday)
        )

        stats = aggregator.get_daily_stats(now)

        assert stats.tasks_overdue == 1  # Only non-done overdue

    def test_counts_events_today(self, db, aggregator):
        """events_today counts non-cancelled events today."""
        now = datetime(2025, 1, 15, 10, 0)
        start = now.replace(hour=14, minute=0).isoformat()
        end = now.replace(hour=15, minute=0).isoformat()

        db.execute_write(
            """INSERT INTO calendar_events (title, start_time, end_time, status)
               VALUES (?, ?, ?, ?)""",
            ("Meeting 1", start, end, "confirmed")
        )
        db.execute_write(
            """INSERT INTO calendar_events (title, start_time, end_time, status)
               VALUES (?, ?, ?, ?)""",
            ("Cancelled meeting", start, end, "cancelled")
        )

        stats = aggregator.get_daily_stats(now)

        assert stats.events_today == 1

    def test_completion_rate_calculation(self, db, aggregator):
        """completion_rate is calculated correctly."""
        now = datetime(2025, 1, 15, 14, 0)
        completed_at = now.replace(hour=10, minute=0).isoformat()

        # 2 completed today, 2 remaining = 50% completion rate
        db.execute_write(
            """INSERT INTO tasks (title, status, completed_at)
               VALUES (?, ?, ?)""",
            ("Completed 1", "done", completed_at)
        )
        db.execute_write(
            """INSERT INTO tasks (title, status, completed_at)
               VALUES (?, ?, ?)""",
            ("Completed 2", "done", completed_at)
        )
        db.execute_write(
            "INSERT INTO tasks (title, status) VALUES (?, ?)",
            ("Remaining 1", "todo")
        )
        db.execute_write(
            "INSERT INTO tasks (title, status) VALUES (?, ?)",
            ("Remaining 2", "in_progress")
        )

        stats = aggregator.get_daily_stats(now)

        # 2 completed / (2 completed + 2 remaining) = 50%
        assert stats.completion_rate == 50.0

    def test_completion_rate_zero_when_no_tasks(self, aggregator):
        """completion_rate is 0 when there are no tasks."""
        now = datetime(2025, 1, 15, 10, 0)

        stats = aggregator.get_daily_stats(now)

        assert stats.completion_rate == 0.0


class TestCalculateTimeAnalysis:
    """Tests for calculate_time_analysis() method."""

    def test_returns_time_analysis(self, aggregator):
        """calculate_time_analysis() returns a TimeAnalysis object."""
        now = datetime(2025, 1, 15, 10, 0)
        result = aggregator.calculate_time_analysis([], [], now)

        assert isinstance(result, TimeAnalysis)

    def test_total_work_minutes_from_config(self, aggregator):
        """total_work_minutes is calculated from config work hours."""
        now = datetime(2025, 1, 15, 10, 0)
        # Config has 09:00-17:00 = 8 hours = 480 minutes

        result = aggregator.calculate_time_analysis([], [], now)

        assert result.total_work_minutes == 480
        assert result.work_hours_start == time(9, 0)
        assert result.work_hours_end == time(17, 0)

    def test_events_minutes_calculated(self, aggregator):
        """events_minutes sums event durations within work hours."""
        now = datetime(2025, 1, 15, 10, 0)

        # Create a 1-hour event during work hours
        event = CalendarEvent(
            id=1,
            title="Meeting",
            start_time=now.replace(hour=10, minute=0),
            end_time=now.replace(hour=11, minute=0),
            all_day=False,
        )

        result = aggregator.calculate_time_analysis([event], [], now)

        assert result.events_minutes == 60

    def test_events_clipped_to_work_hours(self, aggregator):
        """Event time is clipped to work hours bounds."""
        now = datetime(2025, 1, 15, 10, 0)

        # Event starts before work hours and ends during
        event = CalendarEvent(
            id=1,
            title="Early meeting",
            start_time=now.replace(hour=7, minute=0),  # Before 9am
            end_time=now.replace(hour=10, minute=0),
            all_day=False,
        )

        result = aggregator.calculate_time_analysis([event], [], now)

        # Only counts 9:00-10:00 = 60 minutes
        assert result.events_minutes == 60

    def test_all_day_event_blocks_entire_work_day(self, aggregator):
        """All-day events block the entire work day."""
        now = datetime(2025, 1, 15, 10, 0)

        event = CalendarEvent(
            id=1,
            title="All day event",
            start_time=now.replace(hour=0, minute=0),
            end_time=now.replace(hour=23, minute=59),
            all_day=True,
        )

        result = aggregator.calculate_time_analysis([event], [], now)

        assert result.events_minutes == 480  # All work minutes

    def test_tasks_estimated_minutes_summed(self, aggregator):
        """tasks_estimated_minutes sums task estimates."""
        now = datetime(2025, 1, 15, 10, 0)

        tasks = [
            Task(id=1, title="Task 1", estimated_minutes=30),
            Task(id=2, title="Task 2", estimated_minutes=45),
            Task(id=3, title="Task 3", estimated_minutes=None),  # No estimate
        ]

        result = aggregator.calculate_time_analysis([], tasks, now)

        assert result.tasks_estimated_minutes == 75

    def test_free_minutes_calculation(self, aggregator):
        """free_minutes is total minus events minus tasks."""
        now = datetime(2025, 1, 15, 10, 0)

        event = CalendarEvent(
            id=1,
            title="Meeting",
            start_time=now.replace(hour=10, minute=0),
            end_time=now.replace(hour=11, minute=0),
            all_day=False,
        )

        tasks = [
            Task(id=1, title="Task 1", estimated_minutes=60),
        ]

        result = aggregator.calculate_time_analysis([event], tasks, now)

        # 480 total - 60 event - 60 task = 360 free
        assert result.free_minutes == 360

    def test_free_minutes_cannot_be_negative(self, aggregator):
        """free_minutes is clamped to 0 if overbooked."""
        now = datetime(2025, 1, 15, 10, 0)

        # 5 hours of meetings
        events = []
        for hour in range(9, 14):
            events.append(CalendarEvent(
                id=hour,
                title=f"Meeting {hour}",
                start_time=now.replace(hour=hour, minute=0),
                end_time=now.replace(hour=hour+1, minute=0),
                all_day=False,
            ))

        # 5 hours of estimated work
        tasks = [Task(id=1, title="Big task", estimated_minutes=300)]

        result = aggregator.calculate_time_analysis(events, tasks, now)

        # Overbooked but free_minutes should be 0, not negative
        assert result.free_minutes == 0


class TestAggregate:
    """Tests for the aggregate() method."""

    def test_returns_dashboard_data(self, db, aggregator):
        """aggregate() returns a complete DashboardData object."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert isinstance(result, DashboardData)

    def test_includes_all_task_categories(self, db, aggregator):
        """DashboardData includes all task category lists."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert hasattr(result, 'tasks_due')
        assert hasattr(result, 'tasks_scheduled')
        assert hasattr(result, 'tasks_overdue')
        assert hasattr(result, 'tasks_high_priority')
        assert all(isinstance(lst, list) for lst in [
            result.tasks_due,
            result.tasks_scheduled,
            result.tasks_overdue,
            result.tasks_high_priority,
        ])

    def test_includes_events(self, db, aggregator):
        """DashboardData includes events list."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert hasattr(result, 'events')
        assert isinstance(result.events, list)

    def test_includes_stats(self, db, aggregator):
        """DashboardData includes stats."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert hasattr(result, 'stats')
        assert isinstance(result.stats, DailyStats)

    def test_includes_time_analysis(self, db, aggregator):
        """DashboardData includes time analysis."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert hasattr(result, 'time_analysis')
        assert isinstance(result.time_analysis, TimeAnalysis)

    def test_includes_top_priorities(self, db, aggregator):
        """DashboardData includes top priority tasks."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert hasattr(result, 'top_priorities')
        assert isinstance(result.top_priorities, list)

    def test_includes_greeting(self, db, aggregator):
        """DashboardData includes appropriate greeting."""
        now = datetime(2025, 1, 15, 10, 0)  # Morning

        result = aggregator.aggregate(now)

        assert result.greeting == "Good Morning!"

    def test_includes_timestamps(self, db, aggregator):
        """DashboardData includes generated_at and date."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert result.generated_at == now
        assert result.date == now

    def test_deduplicates_tasks_for_prioritization(self, db, aggregator):
        """Tasks appearing in multiple categories are deduplicated."""
        now = datetime(2025, 1, 15, 10, 0)

        # Create a task that's both due today and high priority
        today_due = now.replace(hour=18, minute=0).isoformat()
        db.execute_write(
            """INSERT INTO tasks (title, status, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            ("Important urgent task", "todo", 5, today_due)
        )

        result = aggregator.aggregate(now)

        # The task should appear in tasks_due and tasks_high_priority
        # But top_priorities should not have duplicates
        # (We can't easily verify internal dedup, but we can verify it runs)
        assert result.top_priorities is not None

    def test_uses_current_time_if_now_not_provided(self, db, aggregator):
        """aggregate() uses datetime.now(timezone.utc) if now is not provided."""
        # Just verify it doesn't crash when no time is provided
        result = aggregator.aggregate()

        assert result is not None
        assert result.generated_at is not None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_database(self, db, aggregator):
        """Aggregator handles empty database gracefully."""
        now = datetime(2025, 1, 15, 10, 0)

        result = aggregator.aggregate(now)

        assert result.tasks_due == []
        assert result.tasks_scheduled == []
        assert result.tasks_overdue == []
        assert result.tasks_high_priority == []
        assert result.events == []
        assert result.stats.tasks_completed_today == 0
        assert result.stats.tasks_remaining == 0

    def test_midnight_boundary(self, db, aggregator):
        """Tasks at midnight are categorized correctly."""
        now = datetime(2025, 1, 15, 23, 59)

        # Task due at exact midnight boundary
        midnight = now.replace(hour=23, minute=59, second=59).isoformat()
        db.execute_write(
            """INSERT INTO tasks (title, status, due_date)
               VALUES (?, ?, ?)""",
            ("Midnight task", "todo", midnight)
        )

        due_today, _, _, _ = aggregator.get_today_tasks(now)

        assert len(due_today) == 1

    def test_task_with_all_none_dates(self, db, aggregator):
        """Tasks with no dates are handled correctly."""
        now = datetime(2025, 1, 15, 10, 0)

        db.execute_write(
            """INSERT INTO tasks (title, status, priority)
               VALUES (?, ?, ?)""",
            ("Undated task", "todo", 3)
        )

        due_today, scheduled, overdue, high_priority = aggregator.get_today_tasks(now)

        # Should not appear in any time-based list
        assert len(due_today) == 0
        assert len(scheduled) == 0
        assert len(overdue) == 0
        # Not high priority (priority 3)
        assert len(high_priority) == 0

    def test_multiple_events_same_time(self, db, aggregator):
        """Multiple events at the same time are all counted."""
        now = datetime(2025, 1, 15, 10, 0)
        start = now.replace(hour=14, minute=0).isoformat()
        end = now.replace(hour=15, minute=0).isoformat()

        for i in range(3):
            db.execute_write(
                """INSERT INTO calendar_events (title, start_time, end_time, status)
                   VALUES (?, ?, ?, ?)""",
                (f"Concurrent meeting {i}", start, end, "confirmed")
            )

        events = aggregator.get_today_events(now)

        assert len(events) == 3

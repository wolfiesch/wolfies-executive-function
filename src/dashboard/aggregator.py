"""
Data aggregation module for AI Life Planner Dashboard.

Collects and combines data from multiple sources (tasks, calendar, etc.)
into a unified DashboardData structure for display.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, time, timezone
from typing import List, Optional, Tuple

from src.core.database import Database
from src.core.config import Config
from src.core.models import Task, CalendarEvent
from src.dashboard.prioritizer import Prioritizer, ScoredTask


@dataclass
class DailyStats:
    """Statistics for the dashboard."""
    tasks_completed_today: int = 0
    tasks_remaining: int = 0
    tasks_overdue: int = 0
    events_today: int = 0
    completion_rate: float = 0.0


@dataclass
class TimeAnalysis:
    """Time budget analysis for the day."""
    work_hours_start: time
    work_hours_end: time
    total_work_minutes: int
    events_minutes: int
    tasks_estimated_minutes: int
    free_minutes: int


@dataclass
class DashboardData:
    """Complete dashboard data structure."""
    generated_at: datetime
    date: datetime
    greeting: str

    # Task lists
    tasks_due: List[Task]
    tasks_scheduled: List[Task]
    tasks_overdue: List[Task]
    tasks_high_priority: List[Task]

    # Calendar
    events: List[CalendarEvent]

    # Computed
    top_priorities: List[ScoredTask]
    stats: DailyStats
    time_analysis: TimeAnalysis


class DashboardAggregator:
    """
    Central data aggregation for the Today dashboard.

    Queries multiple data sources and combines them into a unified
    DashboardData structure for display.
    """

    def __init__(self, db: Database, config: Optional[Config] = None):
        """
        Initialize aggregator.

        Args:
            db: Database connection
            config: Configuration (creates default if not provided)
        """
        self.db = db
        self.config = config if config else Config()
        self.prioritizer = Prioritizer(self.config)

    def _get_greeting(self, now: datetime) -> str:
        """
        Generate appropriate greeting based on time of day.

        Args:
            now: Current datetime

        Returns:
            Greeting string
        """
        hour = now.hour

        if hour < 12:
            return "Good Morning!"
        elif hour < 17:
            return "Good Afternoon!"
        elif hour < 21:
            return "Good Evening!"
        else:
            return "Good Night!"

    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object."""
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))

    def _get_work_hours(self) -> Tuple[time, time]:
        """Get configured work hours."""
        start_str = self.config.get("work_hours_start", "preferences", "09:00")
        end_str = self.config.get("work_hours_end", "preferences", "17:00")
        return self._parse_time(start_str), self._parse_time(end_str)

    def get_today_tasks(
        self,
        now: Optional[datetime] = None
    ) -> Tuple[List[Task], List[Task], List[Task], List[Task]]:
        """
        Get tasks relevant to today.

        Args:
            now: Current datetime (defaults to utcnow)

        Returns:
            Tuple of (due_today, scheduled_today, overdue, high_priority_unscheduled)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Tasks due today (not done/cancelled)
        due_today_query = """
            SELECT * FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND due_date >= ? AND due_date <= ?
            ORDER BY priority DESC, due_date ASC
        """
        due_rows = self.db.execute(
            due_today_query,
            (today_start.isoformat(), today_end.isoformat())
        )
        due_today = [Task.from_dict(dict(r)) for r in due_rows]

        # Tasks scheduled for today (not done/cancelled)
        scheduled_query = """
            SELECT * FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND scheduled_start >= ? AND scheduled_start <= ?
            ORDER BY scheduled_start ASC
        """
        scheduled_rows = self.db.execute(
            scheduled_query,
            (today_start.isoformat(), today_end.isoformat())
        )
        scheduled_today = [Task.from_dict(dict(r)) for r in scheduled_rows]

        # Overdue tasks (due before today, not done/cancelled)
        overdue_query = """
            SELECT * FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND due_date < ?
            ORDER BY due_date ASC, priority DESC
        """
        overdue_rows = self.db.execute(overdue_query, (today_start.isoformat(),))
        overdue = [Task.from_dict(dict(r)) for r in overdue_rows]

        # High priority tasks without due date (P4-P5, not done/cancelled)
        high_priority_query = """
            SELECT * FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND priority >= 4
            AND due_date IS NULL
            AND scheduled_start IS NULL
            ORDER BY priority DESC
        """
        high_priority_rows = self.db.execute(high_priority_query)
        high_priority = [Task.from_dict(dict(r)) for r in high_priority_rows]

        return due_today, scheduled_today, overdue, high_priority

    def get_today_events(
        self,
        now: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """
        Get calendar events for today.

        Args:
            now: Current datetime (defaults to utcnow)

        Returns:
            List of CalendarEvent objects sorted by start time
        """
        if now is None:
            now = datetime.now(timezone.utc)

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        query = """
            SELECT * FROM calendar_events
            WHERE status != 'cancelled'
            AND (
                (start_time >= ? AND start_time <= ?)
                OR (all_day = 1 AND date(start_time) = date(?))
            )
            ORDER BY start_time ASC
        """

        rows = self.db.execute(
            query,
            (today_start.isoformat(), today_end.isoformat(), now.isoformat())
        )

        return [CalendarEvent.from_dict(dict(r)) for r in rows]

    def calculate_time_analysis(
        self,
        events: List[CalendarEvent],
        tasks: List[Task],
        now: Optional[datetime] = None
    ) -> TimeAnalysis:
        """
        Calculate time budget for the day.

        Args:
            events: Today's calendar events
            tasks: Today's tasks (with estimates)
            now: Current datetime

        Returns:
            TimeAnalysis with time budget breakdown
        """
        if now is None:
            now = datetime.now(timezone.utc)

        work_start, work_end = self._get_work_hours()

        # Calculate total work minutes
        work_start_dt = now.replace(
            hour=work_start.hour,
            minute=work_start.minute,
            second=0,
            microsecond=0
        )
        work_end_dt = now.replace(
            hour=work_end.hour,
            minute=work_end.minute,
            second=0,
            microsecond=0
        )
        total_work_minutes = int((work_end_dt - work_start_dt).total_seconds() / 60)

        # Calculate event minutes (within work hours only)
        events_minutes = 0
        for event in events:
            if event.all_day:
                # All-day events block entire work day
                events_minutes = total_work_minutes
                break

            if event.start_time and event.end_time:
                # Clip to work hours
                event_start = max(event.start_time, work_start_dt)
                event_end = min(event.end_time, work_end_dt)

                if event_end > event_start:
                    duration = int((event_end - event_start).total_seconds() / 60)
                    events_minutes += duration

        # Calculate task estimated minutes
        tasks_estimated = sum(
            t.estimated_minutes or 0
            for t in tasks
        )

        # Calculate free time
        free_minutes = max(0, total_work_minutes - events_minutes - tasks_estimated)

        return TimeAnalysis(
            work_hours_start=work_start,
            work_hours_end=work_end,
            total_work_minutes=total_work_minutes,
            events_minutes=events_minutes,
            tasks_estimated_minutes=tasks_estimated,
            free_minutes=free_minutes,
        )

    def get_daily_stats(self, now: Optional[datetime] = None) -> DailyStats:
        """
        Get completion statistics for today.

        Args:
            now: Current datetime

        Returns:
            DailyStats with counts and completion rate
        """
        if now is None:
            now = datetime.now(timezone.utc)

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Tasks completed today
        completed_query = """
            SELECT COUNT(*) as count FROM tasks
            WHERE status = 'done'
            AND completed_at >= ?
        """
        completed_row = self.db.execute_one(completed_query, (today_start.isoformat(),))
        completed_today = completed_row['count'] if completed_row else 0

        # Tasks remaining (not done/cancelled)
        remaining_query = """
            SELECT COUNT(*) as count FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
        """
        remaining_row = self.db.execute_one(remaining_query)
        remaining = remaining_row['count'] if remaining_row else 0

        # Overdue tasks
        overdue_query = """
            SELECT COUNT(*) as count FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND due_date < ?
        """
        overdue_row = self.db.execute_one(overdue_query, (today_start.isoformat(),))
        overdue = overdue_row['count'] if overdue_row else 0

        # Events today
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        events_query = """
            SELECT COUNT(*) as count FROM calendar_events
            WHERE status != 'cancelled'
            AND start_time >= ? AND start_time <= ?
        """
        events_row = self.db.execute_one(
            events_query,
            (today_start.isoformat(), today_end.isoformat())
        )
        events_today = events_row['count'] if events_row else 0

        # Calculate completion rate
        total_relevant = completed_today + remaining
        completion_rate = (
            (completed_today / total_relevant * 100)
            if total_relevant > 0 else 0.0
        )

        return DailyStats(
            tasks_completed_today=completed_today,
            tasks_remaining=remaining,
            tasks_overdue=overdue,
            events_today=events_today,
            completion_rate=completion_rate,
        )

    def aggregate(self, now: Optional[datetime] = None) -> DashboardData:
        """
        Aggregate all data for the dashboard.

        Main entry point for collecting all dashboard data.

        Args:
            now: Current datetime (defaults to utcnow)

        Returns:
            Complete DashboardData structure
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Get tasks
        due_today, scheduled_today, overdue, high_priority = self.get_today_tasks(now)

        # Get events
        events = self.get_today_events(now)

        # Get stats
        stats = self.get_daily_stats(now)

        # Combine all active tasks for prioritization (deduplicate by ID)
        seen_ids = set()
        all_active_tasks = []
        for task in due_today + scheduled_today + overdue + high_priority:
            if task.id not in seen_ids:
                seen_ids.add(task.id)
                all_active_tasks.append(task)

        # Calculate time analysis
        time_analysis = self.calculate_time_analysis(
            events,
            scheduled_today + due_today,
            now
        )

        # Get top priorities
        top_priorities = self.prioritizer.get_top_priorities(
            all_active_tasks,
            n=5,
            now=now,
            available_minutes=time_analysis.free_minutes
        )

        return DashboardData(
            generated_at=now,
            date=now,
            greeting=self._get_greeting(now),
            tasks_due=due_today,
            tasks_scheduled=scheduled_today,
            tasks_overdue=overdue,
            tasks_high_priority=high_priority,
            events=events,
            top_priorities=top_priorities,
            stats=stats,
            time_analysis=time_analysis,
        )

"""
Unit tests for the prioritizer module.
Tests the priority scoring algorithm.
"""

import pytest
from datetime import datetime, timedelta, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.models import Task
from src.dashboard.prioritizer import (
    Prioritizer,
    ScoredTask,
    calculate_urgency_score,
    calculate_importance_score,
    calculate_time_fit_score,
    calculate_context_score,
)


class TestUrgencyScore:
    """Tests for urgency score calculation."""

    def test_overdue_task_has_max_urgency(self):
        """Overdue tasks should have urgency score of 1.0."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Overdue task",
            due_date=now - timedelta(days=3),
            status="todo"
        )
        score = calculate_urgency_score(task, now)
        assert score == 1.0

    def test_due_today_has_high_urgency(self):
        """Tasks due today should have urgency score of 0.9."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Due today",
            due_date=now.replace(hour=23, minute=59),
            status="todo"
        )
        score = calculate_urgency_score(task, now)
        assert score == 0.9

    def test_due_tomorrow_has_moderate_urgency(self):
        """Tasks due tomorrow should have urgency score of 0.7."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Due tomorrow",
            due_date=now + timedelta(days=1),
            status="todo"
        )
        score = calculate_urgency_score(task, now)
        assert score == 0.7

    def test_due_this_week_has_medium_urgency(self):
        """Tasks due within a week should have urgency score of 0.5."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Due this week",
            due_date=now + timedelta(days=5),
            status="todo"
        )
        score = calculate_urgency_score(task, now)
        assert score == 0.5

    def test_no_due_date_has_low_urgency(self):
        """Tasks without due date should have urgency score of 0.1."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="No due date",
            due_date=None,
            status="todo"
        )
        score = calculate_urgency_score(task, now)
        assert score == 0.1

    def test_far_future_due_date_has_low_urgency(self):
        """Tasks due far in the future should have urgency score of 0.1."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Due next month",
            due_date=now + timedelta(days=30),
            status="todo"
        )
        score = calculate_urgency_score(task, now)
        assert score == 0.1


class TestImportanceScore:
    """Tests for importance score calculation."""

    def test_priority_5_has_max_importance(self):
        """Priority 5 (Critical) should have importance score of 1.0."""
        task = Task(id=1, title="Critical", priority=5)
        score = calculate_importance_score(task)
        assert score == 1.0

    def test_priority_4_has_high_importance(self):
        """Priority 4 (High) should have importance score of 0.8."""
        task = Task(id=1, title="High", priority=4)
        score = calculate_importance_score(task)
        assert score == 0.8

    def test_priority_3_has_normal_importance(self):
        """Priority 3 (Normal) should have importance score of 0.5."""
        task = Task(id=1, title="Normal", priority=3)
        score = calculate_importance_score(task)
        assert score == 0.5

    def test_priority_2_has_low_importance(self):
        """Priority 2 (Low) should have importance score of 0.3."""
        task = Task(id=1, title="Low", priority=2)
        score = calculate_importance_score(task)
        assert score == 0.3

    def test_priority_1_has_minimal_importance(self):
        """Priority 1 (Minimal) should have importance score of 0.1."""
        task = Task(id=1, title="Minimal", priority=1)
        score = calculate_importance_score(task)
        assert score == 0.1


class TestTimeFitScore:
    """Tests for time fit score calculation."""

    def test_no_estimate_gives_neutral_score(self):
        """Tasks without time estimate should have neutral score of 0.5."""
        task = Task(id=1, title="No estimate", estimated_minutes=None)
        score = calculate_time_fit_score(task, available_minutes=60)
        assert score == 0.5

    def test_no_available_time_gives_neutral_score(self):
        """No available time context should give neutral score."""
        task = Task(id=1, title="Has estimate", estimated_minutes=30)
        score = calculate_time_fit_score(task, available_minutes=None)
        assert score == 0.5

    def test_task_fits_perfectly_gives_max_score(self):
        """Task that fits available time well should have high score."""
        task = Task(id=1, title="Fits well", estimated_minutes=45)
        score = calculate_time_fit_score(task, available_minutes=60)
        assert score == 1.0

    def test_task_too_long_gives_low_score(self):
        """Task longer than available time should have low score."""
        task = Task(id=1, title="Too long", estimated_minutes=120)
        score = calculate_time_fit_score(task, available_minutes=60)
        assert score == 0.2


class TestContextScore:
    """Tests for context score calculation."""

    def test_scheduled_task_gets_bonus(self):
        """Scheduled tasks should get a context bonus."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Scheduled",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1)
        )
        score = calculate_context_score(task)
        assert score > 0.5

    def test_subtask_gets_slight_penalty(self):
        """Subtasks should get a slight context penalty."""
        task = Task(id=1, title="Subtask", parent_task_id=5)
        score = calculate_context_score(task)
        assert score < 0.5


class TestPrioritizer:
    """Tests for the Prioritizer class."""

    def test_score_tasks_returns_sorted_list(self):
        """score_tasks should return tasks sorted by score (descending)."""
        now = datetime.now(timezone.utc)

        tasks = [
            Task(id=1, title="Low priority", priority=1),
            Task(id=2, title="High priority", priority=5),
            Task(id=3, title="Medium priority", priority=3),
        ]

        prioritizer = Prioritizer()
        scored = prioritizer.score_tasks(tasks, now)

        # Should be sorted by score (highest first)
        assert scored[0].task.priority == 5
        assert scored[1].task.priority == 3
        assert scored[2].task.priority == 1

    def test_get_top_priorities_limits_results(self):
        """get_top_priorities should return only top N tasks."""
        tasks = [
            Task(id=i, title=f"Task {i}", priority=3)
            for i in range(10)
        ]

        prioritizer = Prioritizer()
        top = prioritizer.get_top_priorities(tasks, n=3)

        assert len(top) == 3

    def test_scored_task_contains_breakdown(self):
        """ScoredTask should contain score breakdown for transparency."""
        task = Task(id=1, title="Test task", priority=4, due_date=datetime.now(timezone.utc))

        prioritizer = Prioritizer()
        scored = prioritizer.score_task(task)

        assert "urgency" in scored.breakdown
        assert "importance" in scored.breakdown
        assert "time_fit" in scored.breakdown
        assert "context" in scored.breakdown

    def test_combined_scoring_weights_correctly(self):
        """Combined score should weight components correctly."""
        # Create a task with known scores
        now = datetime.now(timezone.utc)
        task = Task(
            id=1,
            title="Known scores",
            priority=5,  # importance = 1.0
            due_date=now - timedelta(days=1),  # urgency = 1.0 (overdue)
        )

        prioritizer = Prioritizer()
        scored = prioritizer.score_task(task, now)

        # Score should be high (urgency + importance are max)
        assert scored.score > 0.7

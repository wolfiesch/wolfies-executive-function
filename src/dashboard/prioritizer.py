"""
Priority scoring algorithm for AI Life Planner Dashboard.

Scores tasks based on urgency, importance, and time fit to help
users focus on what matters most.

Score formula:
    score = (urgency * 0.4) + (importance * 0.3) + (time_fit * 0.2) + (context * 0.1)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from src.core.models import Task
from src.core.config import Config


@dataclass
class ScoredTask:
    """Task with computed priority score and breakdown."""
    task: Task
    score: float
    urgency_score: float
    importance_score: float
    time_fit_score: float
    context_score: float
    breakdown: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: 'ScoredTask') -> bool:
        """Enable sorting by score (descending)."""
        return self.score > other.score  # Reverse for descending order


def calculate_urgency_score(task: Task, now: Optional[datetime] = None) -> float:
    """
    Calculate urgency score (0.0-1.0) based on due date proximity.

    Scoring:
        - Overdue: 1.0
        - Due today: 0.9
        - Due tomorrow: 0.7
        - Due within 3 days: 0.6
        - Due this week (4-7 days): 0.5
        - Due next week (8-14 days): 0.3
        - Due later or no due date: 0.1

    Args:
        task: Task to score
        now: Current datetime (defaults to utcnow)

    Returns:
        Urgency score between 0.0 and 1.0
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # No due date = low urgency
    if task.due_date is None:
        return 0.1

    # Calculate days until due
    due_date = task.due_date
    # Normalize to date comparison (ignore time component for day-level comparison)
    now_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    due_date_normalized = due_date.replace(hour=23, minute=59, second=59, microsecond=0)

    delta = due_date_normalized - now_date
    days_until_due = delta.days

    if days_until_due < 0:
        # Overdue
        return 1.0
    elif days_until_due == 0:
        # Due today
        return 0.9
    elif days_until_due == 1:
        # Due tomorrow
        return 0.7
    elif days_until_due <= 3:
        # Due within 3 days
        return 0.6
    elif days_until_due <= 7:
        # Due this week
        return 0.5
    elif days_until_due <= 14:
        # Due next week
        return 0.3
    else:
        # Due later
        return 0.1


def calculate_importance_score(task: Task) -> float:
    """
    Calculate importance score (0.0-1.0) based on priority level.

    Priority mapping:
        - P5 (Critical): 1.0
        - P4 (High): 0.8
        - P3 (Normal): 0.5
        - P2 (Low): 0.3
        - P1 (Minimal): 0.1

    Args:
        task: Task to score

    Returns:
        Importance score between 0.0 and 1.0
    """
    priority_map = {
        5: 1.0,   # Critical
        4: 0.8,   # High
        3: 0.5,   # Normal
        2: 0.3,   # Low
        1: 0.1,   # Minimal
    }

    priority = task.priority if task.priority else 3
    # Clamp to valid range
    priority = max(1, min(5, priority))

    return priority_map.get(priority, 0.5)


def calculate_time_fit_score(
    task: Task,
    available_minutes: Optional[int] = None
) -> float:
    """
    Calculate time fit score (0.0-1.0) based on whether task fits available time.

    Scoring:
        - No estimate: 0.5 (neutral)
        - Fits perfectly (task is 50-100% of available time): 1.0
        - Too short (< 30% of slot): 0.4
        - Slightly short (30-50% of slot): 0.7
        - Won't fit (> available time): 0.2

    Args:
        task: Task to score
        available_minutes: Available time in minutes (None = ignore time fit)

    Returns:
        Time fit score between 0.0 and 1.0
    """
    # No estimate = neutral score
    if task.estimated_minutes is None:
        return 0.5

    # No available time context = neutral score
    if available_minutes is None or available_minutes <= 0:
        return 0.5

    estimated = task.estimated_minutes
    ratio = estimated / available_minutes

    if ratio > 1.0:
        # Won't fit in available time
        return 0.2
    elif ratio >= 0.5:
        # Fits well (50-100% of available time)
        return 1.0
    elif ratio >= 0.3:
        # Slightly short (30-50%)
        return 0.7
    else:
        # Too short (< 30%)
        return 0.4


def calculate_context_score(task: Task, config: Optional[Config] = None) -> float:
    """
    Calculate context score (0.0-1.0) based on task metadata and context.

    Currently considers:
        - Has scheduled time (bonus for time-blocked tasks)
        - Is a subtask (slightly lower to prioritize parent tasks)

    Future enhancements:
        - Location/context matching
        - Energy level matching
        - Dependencies

    Args:
        task: Task to score
        config: Configuration (for future context-aware scoring)

    Returns:
        Context score between 0.0 and 1.0
    """
    score = 0.5  # Base neutral score

    # Scheduled tasks get a bonus (user explicitly allocated time)
    if task.is_scheduled():
        score += 0.3

    # Subtasks get a slight penalty (parent tasks often more important)
    if task.parent_task_id is not None:
        score -= 0.1

    # Clamp to valid range
    return max(0.0, min(1.0, score))


class Prioritizer:
    """
    Task prioritization engine.

    Scores and ranks tasks based on urgency, importance, time fit, and context
    to help users focus on what matters most.
    """

    # Weight factors for score components
    URGENCY_WEIGHT = 0.4
    IMPORTANCE_WEIGHT = 0.3
    TIME_FIT_WEIGHT = 0.2
    CONTEXT_WEIGHT = 0.1

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize prioritizer.

        Args:
            config: Configuration for context-aware scoring
        """
        self.config = config

    def score_task(
        self,
        task: Task,
        now: Optional[datetime] = None,
        available_minutes: Optional[int] = None
    ) -> ScoredTask:
        """
        Score a single task.

        Args:
            task: Task to score
            now: Current datetime for urgency calculation
            available_minutes: Available time for time fit calculation

        Returns:
            ScoredTask with computed scores
        """
        if now is None:
            now = datetime.now(timezone.utc)

        urgency = calculate_urgency_score(task, now)
        importance = calculate_importance_score(task)
        time_fit = calculate_time_fit_score(task, available_minutes)
        context = calculate_context_score(task, self.config)

        # Calculate weighted score
        score = (
            urgency * self.URGENCY_WEIGHT +
            importance * self.IMPORTANCE_WEIGHT +
            time_fit * self.TIME_FIT_WEIGHT +
            context * self.CONTEXT_WEIGHT
        )

        # Build breakdown for debugging/transparency
        breakdown = {
            "urgency": {
                "score": urgency,
                "weight": self.URGENCY_WEIGHT,
                "weighted": urgency * self.URGENCY_WEIGHT,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            },
            "importance": {
                "score": importance,
                "weight": self.IMPORTANCE_WEIGHT,
                "weighted": importance * self.IMPORTANCE_WEIGHT,
                "priority": task.priority,
            },
            "time_fit": {
                "score": time_fit,
                "weight": self.TIME_FIT_WEIGHT,
                "weighted": time_fit * self.TIME_FIT_WEIGHT,
                "estimated_minutes": task.estimated_minutes,
                "available_minutes": available_minutes,
            },
            "context": {
                "score": context,
                "weight": self.CONTEXT_WEIGHT,
                "weighted": context * self.CONTEXT_WEIGHT,
                "is_scheduled": task.is_scheduled(),
                "is_subtask": task.parent_task_id is not None,
            },
        }

        return ScoredTask(
            task=task,
            score=score,
            urgency_score=urgency,
            importance_score=importance,
            time_fit_score=time_fit,
            context_score=context,
            breakdown=breakdown,
        )

    def score_tasks(
        self,
        tasks: List[Task],
        now: Optional[datetime] = None,
        available_minutes: Optional[int] = None,
        top_n: Optional[int] = None
    ) -> List[ScoredTask]:
        """
        Score and sort multiple tasks by priority.

        Args:
            tasks: List of tasks to score
            now: Current datetime for urgency calculation
            available_minutes: Available time for time fit calculation
            top_n: If provided, return only top N tasks

        Returns:
            List of ScoredTask sorted by score (highest first)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Score all tasks
        scored = [
            self.score_task(task, now, available_minutes)
            for task in tasks
        ]

        # Sort by score (descending)
        scored.sort()

        # Return top N if specified
        if top_n is not None and top_n > 0:
            return scored[:top_n]

        return scored

    def get_top_priorities(
        self,
        tasks: List[Task],
        n: int = 5,
        now: Optional[datetime] = None,
        available_minutes: Optional[int] = None
    ) -> List[ScoredTask]:
        """
        Get the top N priority tasks.

        Convenience method for getting the most important tasks to focus on.

        Args:
            tasks: List of tasks to prioritize
            n: Number of top tasks to return (default 5)
            now: Current datetime
            available_minutes: Available time context

        Returns:
            List of top N ScoredTask objects
        """
        return self.score_tasks(tasks, now, available_minutes, top_n=n)

"""
Dashboard data aggregation API endpoints.

Provides unified dashboard data by aggregating from multiple sources
(tasks, calendar, goals) using the DashboardAggregator.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_dashboard_aggregator, get_database
from backend.schemas import (
    DashboardResponse,
    DashboardStats,
    TaskResponse,
    EventResponse,
    GoalSummary,
    ActivityItem,
)
from src.dashboard.aggregator import DashboardAggregator
from src.core.database import Database

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/today", response_model=DashboardResponse)
async def get_today_dashboard(
    aggregator: DashboardAggregator = Depends(get_dashboard_aggregator),
    db: Database = Depends(get_database),
):
    """
    Get unified dashboard data for today.

    Aggregates:
    - Task statistics (done, remaining, overdue)
    - Priority tasks for today
    - Upcoming calendar events
    - Goal progress summaries
    - Recent activity feed
    """
    try:
        # Get dashboard data from aggregator
        dashboard_data = aggregator.aggregate()

        # Build response with proper schema conversion
        priority_tasks = []
        for task in dashboard_data.top_priorities[:5]:
            t = task.task  # ScoredTask wraps Task
            # Extract time from due_date if present
            due_time_str = None
            if t.due_date and t.due_date.hour != 0:
                due_time_str = t.due_date.strftime("%H:%M")
            # Get optional fields from context dict if available
            ctx = t.context or {}
            priority_tasks.append(TaskResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                status=t.status,
                priority=t.priority,
                due_date=t.due_date.isoformat() if t.due_date else None,
                due_time=due_time_str,
                estimated_minutes=t.estimated_minutes,
                actual_minutes=t.actual_minutes,
                life_area=ctx.get("life_area"),
                project_id=t.project_id,
                parent_id=t.parent_task_id,
                tags=t.tags or [],
                waiting_for=ctx.get("waiting_for"),
                waiting_since=ctx.get("waiting_since"),
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
                created_at=t.created_at.isoformat() if t.created_at else "",
                updated_at=t.updated_at.isoformat() if t.updated_at else "",
            ))

        upcoming_events = []
        for event in dashboard_data.events[:5]:
            upcoming_events.append(EventResponse(
                id=event.id,
                title=event.title,
                description=event.description,
                start_time=event.start_time.isoformat() if event.start_time else "",
                end_time=event.end_time.isoformat() if event.end_time else "",
                all_day=event.all_day or False,
                location=event.location,
                status=event.status or "confirmed",
                event_type=event.event_type or "meeting",
                color=event.color,
                created_at=event.created_at.isoformat() if event.created_at else "",
                updated_at=event.updated_at.isoformat() if event.updated_at else "",
            ))

        # Get goal summaries
        goal_summaries = _get_goal_summaries(db)

        # Get recent activity
        recent_activity = _get_recent_activity(db)

        return DashboardResponse(
            stats=DashboardStats(
                tasks_today=dashboard_data.stats.tasks_remaining + dashboard_data.stats.tasks_completed_today,
                tasks_overdue=dashboard_data.stats.tasks_overdue,
                completion_rate=dashboard_data.stats.completion_rate,
                streak_days=0,  # TODO: Implement streak tracking
            ),
            priority_tasks=priority_tasks,
            upcoming_events=upcoming_events,
            goal_summaries=goal_summaries,
            recent_activity=recent_activity,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard: {str(e)}")


def _get_goal_summaries(db: Database) -> list[GoalSummary]:
    """Get brief goal summaries for dashboard display."""
    try:
        rows = db.execute("""
            SELECT id, name as title,
                   COALESCE(json_extract(metadata, '$.progress'), 0) as progress,
                   life_area
            FROM projects
            WHERE status = 'active'
            AND para_type = 'goal'
            ORDER BY updated_at DESC
            LIMIT 5
        """)

        return [
            GoalSummary(
                id=row["id"],
                title=row["title"],
                progress=int(row["progress"] or 0),
                life_area=row.get("life_area"),
            )
            for row in rows
        ]
    except Exception:
        return []


def _get_recent_activity(db: Database) -> list[ActivityItem]:
    """Get recent activity items for the dashboard feed."""
    activities = []

    try:
        # Get recently completed tasks
        completed_tasks = db.execute("""
            SELECT id, title, completed_at
            FROM tasks
            WHERE status = 'done'
            AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT 5
        """)

        for task in completed_tasks:
            activities.append(ActivityItem(
                id=f"task-{task['id']}",
                type="task_completed",
                title=f"Completed: {task['title']}",
                timestamp=task["completed_at"],
            ))

        # Get recently created events
        recent_events = db.execute("""
            SELECT id, title, created_at
            FROM calendar_events
            WHERE created_at > datetime('now', '-7 days')
            ORDER BY created_at DESC
            LIMIT 3
        """)

        for event in recent_events:
            activities.append(ActivityItem(
                id=f"event-{event['id']}",
                type="event_created",
                title=f"Created event: {event['title']}",
                timestamp=event["created_at"],
            ))

        # Sort by timestamp descending and limit
        activities.sort(key=lambda x: x.timestamp or "", reverse=True)
        return activities[:10]

    except Exception:
        return []


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    aggregator: DashboardAggregator = Depends(get_dashboard_aggregator),
):
    """
    Get just the statistics portion of the dashboard.

    Lighter-weight endpoint for quick status checks.
    """
    try:
        dashboard_data = aggregator.aggregate()

        return DashboardStats(
            tasks_today=dashboard_data.stats.tasks_remaining + dashboard_data.stats.tasks_completed_today,
            tasks_overdue=dashboard_data.stats.tasks_overdue,
            completion_rate=dashboard_data.stats.completion_rate,
            streak_days=0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load stats: {str(e)}")

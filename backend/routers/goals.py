"""
Goals management API endpoints.

Provides CRUD operations for goals, milestones, and progress tracking,
leveraging the GoalAgent for business logic.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_goal_agent
from backend.schemas import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalListResponse,
    ProgressLogCreate,
    MilestoneSchema,
    AgentResponseSchema,
)
from src.agents import GoalAgent

router = APIRouter(prefix="/goals", tags=["goals"])


def _row_to_goal_response(row: dict) -> GoalResponse:
    """Convert database row to GoalResponse schema."""
    milestones = row.get("milestones", [])
    if isinstance(milestones, str):
        import json
        try:
            milestones = json.loads(milestones)
        except (json.JSONDecodeError, TypeError):
            milestones = []

    milestone_schemas = [
        MilestoneSchema(
            id=m.get("id"),
            title=m.get("title", ""),
            completed=m.get("completed", False),
            completed_at=m.get("completed_at"),
        )
        for m in milestones
    ]

    return GoalResponse(
        id=row["id"],
        title=row["title"],
        description=row.get("description"),
        status=row.get("status", "active"),
        life_area=row.get("life_area"),
        target_date=row.get("target_date"),
        progress=row.get("progress", 0),
        milestones=milestone_schemas,
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


@router.get("/", response_model=GoalListResponse)
async def list_goals(
    status: Optional[str] = Query(None, description="Filter by status"),
    life_area: Optional[str] = Query(None, description="Filter by life area"),
    agent: GoalAgent = Depends(get_goal_agent),
):
    """
    List goals with optional filters.

    Supports filtering by status (active, completed, paused) and life area.
    """
    context = {}
    if status:
        context["status"] = status
    if life_area:
        context["life_area"] = life_area

    response = agent.process("list_goals", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    goals_data = response.data.get("goals", []) if response.data else []

    return GoalListResponse(
        goals=[_row_to_goal_response(g) for g in goals_data],
        total=len(goals_data),
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: int,
    agent: GoalAgent = Depends(get_goal_agent),
):
    """Get a single goal by ID, including milestones."""
    response = agent.process("get_goal", {"goal_id": goal_id})

    if not response.success:
        raise HTTPException(status_code=404, detail=response.message)

    goal_data = response.data.get("goal") if response.data else None
    if not goal_data:
        raise HTTPException(status_code=404, detail="Goal not found")

    return _row_to_goal_response(goal_data)


@router.post("/", response_model=AgentResponseSchema, status_code=201)
async def create_goal(
    goal: GoalCreate,
    agent: GoalAgent = Depends(get_goal_agent),
):
    """Create a new goal with optional milestones."""
    context = {
        "title": goal.title,
        "description": goal.description,
        "life_area": goal.life_area,
        "target_date": goal.target_date,
    }
    if goal.milestones:
        context["milestones"] = [m.model_dump() for m in goal.milestones]

    context = {k: v for k, v in context.items() if v is not None}

    response = agent.process("create_goal", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.put("/{goal_id}", response_model=AgentResponseSchema)
async def update_goal(
    goal_id: int,
    goal: GoalUpdate,
    agent: GoalAgent = Depends(get_goal_agent),
):
    """Update an existing goal."""
    context = {"goal_id": goal_id}
    update_data = goal.model_dump(exclude_unset=True)
    context.update(update_data)

    response = agent.process("update_goal", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.post("/{goal_id}/progress", response_model=AgentResponseSchema)
async def log_progress(
    goal_id: int,
    progress: ProgressLogCreate,
    agent: GoalAgent = Depends(get_goal_agent),
):
    """
    Log progress on a goal.

    Progress delta can be positive (progress made) or negative (setback).
    Total progress is capped between 0-100%.
    """
    context = {
        "goal_id": goal_id,
        "progress_delta": progress.progress_delta,
        "note": progress.note,
    }

    response = agent.process("log_progress", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.post("/{goal_id}/milestones", response_model=AgentResponseSchema)
async def add_milestone(
    goal_id: int,
    milestone: MilestoneSchema,
    agent: GoalAgent = Depends(get_goal_agent),
):
    """Add a new milestone to a goal."""
    context = {
        "goal_id": goal_id,
        "title": milestone.title,
    }

    response = agent.process("add_milestone", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.patch("/{goal_id}/milestones/{milestone_id}/complete", response_model=AgentResponseSchema)
async def complete_milestone(
    goal_id: int,
    milestone_id: str,
    agent: GoalAgent = Depends(get_goal_agent),
):
    """Mark a milestone as complete."""
    context = {
        "goal_id": goal_id,
        "milestone_id": milestone_id,
    }

    response = agent.process("complete_milestone", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )

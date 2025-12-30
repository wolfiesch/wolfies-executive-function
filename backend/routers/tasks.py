"""
Task management API endpoints.

Provides CRUD operations for tasks, leveraging the TaskAgent
for business logic and natural language parsing.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_task_agent
from backend.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    AgentResponseSchema,
)
from backend.websocket import (
    notify_task_created,
    notify_task_updated,
    notify_task_completed,
    notify_task_deleted,
)
from src.agents import TaskAgent

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _row_to_task_response(row: dict) -> TaskResponse:
    """Convert database row to TaskResponse schema."""
    # Parse tags from comma-separated string if needed
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row.get("description"),
        status=row.get("status", "todo"),
        priority=row.get("priority", 3),
        due_date=row.get("due_date"),
        due_time=row.get("due_time"),
        estimated_minutes=row.get("estimated_minutes"),
        actual_minutes=row.get("actual_minutes"),
        life_area=row.get("life_area"),
        project_id=row.get("project_id"),
        parent_id=row.get("parent_task_id"),
        tags=tags,
        waiting_for=row.get("waiting_for"),
        waiting_since=row.get("waiting_since"),
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority"),
    life_area: Optional[str] = Query(None, description="Filter by life area"),
    project_id: Optional[int] = Query(None, description="Filter by project"),
    due_before: Optional[str] = Query(None, description="Filter tasks due before date"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    agent: TaskAgent = Depends(get_task_agent),
):
    """
    List tasks with optional filters.

    Supports filtering by status, priority, life area, project, and due date.
    Results are paginated.
    """
    context = {}
    if status:
        context["status"] = status
    if priority:
        context["priority"] = priority
    if life_area:
        context["life_area"] = life_area
    if project_id:
        context["project_id"] = project_id
    if due_before:
        context["due_before"] = due_before

    response = agent.process("list_tasks", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    tasks_data = response.data.get("tasks", []) if response.data else []

    # Pagination
    total = len(tasks_data)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_tasks = tasks_data[start:end]

    return TaskListResponse(
        tasks=[_row_to_task_response(t) for t in paginated_tasks],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    agent: TaskAgent = Depends(get_task_agent),
):
    """Get a single task by ID."""
    response = agent.process("get_task", {"task_id": task_id})

    if not response.success:
        raise HTTPException(status_code=404, detail=response.message)

    task_data = response.data.get("task") if response.data else None
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    return _row_to_task_response(task_data)


@router.post("/", response_model=AgentResponseSchema, status_code=201)
async def create_task(
    task: TaskCreate,
    agent: TaskAgent = Depends(get_task_agent),
):
    """
    Create a new task.

    The title can include natural language like "tomorrow at 2pm"
    which will be parsed for due date/time.
    """
    context = {
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date,
        "due_time": task.due_time,
        "estimated_minutes": task.estimated_minutes,
        "life_area": task.life_area,
        "project_id": task.project_id,
        "parent_id": task.parent_id,
        "tags": task.tags,
    }
    # Remove None values
    context = {k: v for k, v in context.items() if v is not None}

    response = agent.process("add_task", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    # Broadcast WebSocket notification for real-time updates
    if response.data and response.data.get("task"):
        await notify_task_created(response.data["task"])

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.put("/{task_id}", response_model=AgentResponseSchema)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    agent: TaskAgent = Depends(get_task_agent),
):
    """Update an existing task (PUT - full replacement)."""
    context = {"task_id": task_id}

    # Only include fields that were explicitly set
    update_data = task.model_dump(exclude_unset=True)
    context.update(update_data)

    response = agent.process("update_task", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    # Broadcast WebSocket notification for real-time updates
    if response.data and response.data.get("task"):
        await notify_task_updated(response.data["task"])

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.patch("/{task_id}", response_model=AgentResponseSchema)
async def patch_task(
    task_id: int,
    task: TaskUpdate,
    agent: TaskAgent = Depends(get_task_agent),
):
    """Partially update an existing task (PATCH - partial update)."""
    context = {"task_id": task_id}

    # Only include fields that were explicitly set
    update_data = task.model_dump(exclude_unset=True)
    context.update(update_data)

    response = agent.process("update_task", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    # Broadcast WebSocket notification for real-time updates
    if response.data and response.data.get("task"):
        await notify_task_updated(response.data["task"])

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.patch("/{task_id}/complete", response_model=AgentResponseSchema)
async def complete_task(
    task_id: int,
    agent: TaskAgent = Depends(get_task_agent),
):
    """Mark a task as complete."""
    response = agent.process("complete_task", {"task_id": task_id})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    # Broadcast WebSocket notification for real-time updates
    if response.data and response.data.get("task"):
        await notify_task_completed(response.data["task"])

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.post("/{task_id}/reopen", response_model=AgentResponseSchema)
async def reopen_task(
    task_id: int,
    agent: TaskAgent = Depends(get_task_agent),
):
    """
    Reopen a completed task (mark as todo).

    Used when unchecking a completed task checkbox.
    """
    # Reopen by updating status to 'todo' and clearing completed_at
    context = {
        "task_id": task_id,
        "status": "todo",
        "completed_at": None,
    }
    response = agent.process("update_task", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    # Broadcast WebSocket notification for real-time updates
    if response.data and response.data.get("task"):
        await notify_task_updated(response.data["task"])

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.delete("/{task_id}", response_model=AgentResponseSchema)
async def delete_task(
    task_id: int,
    agent: TaskAgent = Depends(get_task_agent),
):
    """Delete a task."""
    response = agent.process("delete_task", {"task_id": task_id})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    # Broadcast WebSocket notification for real-time updates
    await notify_task_deleted(str(task_id))

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
    )


@router.get("/search/", response_model=TaskListResponse)
async def search_tasks(
    q: str = Query(..., min_length=1, description="Search query"),
    agent: TaskAgent = Depends(get_task_agent),
):
    """
    Search tasks by title and description.

    Uses full-text search across task content.
    """
    response = agent.process("search_tasks", {"query": q})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    tasks_data = response.data.get("tasks", []) if response.data else []

    return TaskListResponse(
        tasks=[_row_to_task_response(t) for t in tasks_data],
        total=len(tasks_data),
        page=1,
        per_page=50,
    )

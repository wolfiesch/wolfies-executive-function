"""
Pydantic schemas for API request/response validation.

These schemas provide:
- Type safety for API inputs and outputs
- Automatic validation and error messages
- OpenAPI documentation generation
- Serialization/deserialization

Design note: Schemas mirror the frontend TypeScript types in
frontend/src/types/models.ts for consistency.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Base Response Schemas
# =============================================================================

class AgentResponseSchema(BaseModel):
    """Standard response from any agent operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response for API errors."""
    detail: str
    code: Optional[str] = None


# =============================================================================
# Task Schemas
# =============================================================================

class TaskCreate(BaseModel):
    """Request body for creating a task."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)
    due_date: Optional[str] = None  # ISO format or natural language
    due_time: Optional[str] = None  # HH:MM format
    estimated_minutes: Optional[int] = Field(default=None, ge=1)
    life_area: Optional[str] = None
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    """Request body for updating a task."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None  # todo, in_progress, waiting, done, cancelled
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=1)
    life_area: Optional[str] = None
    project_id: Optional[int] = None
    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):
    """Task data returned from API."""
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: int
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    life_area: Optional[str] = None
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    tags: List[str] = []
    waiting_for: Optional[str] = None
    waiting_since: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Response for listing tasks."""
    tasks: List[TaskResponse]
    total: int
    page: int = 1
    per_page: int = 50


# =============================================================================
# Calendar Event Schemas
# =============================================================================

class EventCreate(BaseModel):
    """Request body for creating a calendar event."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: str  # ISO format
    end_time: Optional[str] = None
    all_day: bool = False
    location: Optional[str] = None
    event_type: str = "meeting"  # meeting, focus, personal, deadline
    color: Optional[str] = None


class EventUpdate(BaseModel):
    """Request body for updating an event."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    status: Optional[str] = None  # confirmed, tentative, cancelled
    event_type: Optional[str] = None
    color: Optional[str] = None


class EventResponse(BaseModel):
    """Calendar event data returned from API."""
    id: int
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    all_day: bool
    location: Optional[str] = None
    status: str = "confirmed"
    event_type: str = "meeting"
    color: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Response for listing events."""
    events: List[EventResponse]
    total: int


# =============================================================================
# Note Schemas
# =============================================================================

class NoteCreate(BaseModel):
    """Request body for creating a note."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = ""
    note_type: str = "note"  # note, journal, meeting, reference
    life_area: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pinned: bool = False


class NoteUpdate(BaseModel):
    """Request body for updating a note."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    content: Optional[str] = None
    note_type: Optional[str] = None
    life_area: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


class NoteResponse(BaseModel):
    """Note data returned from API."""
    id: int
    title: str
    content: str
    note_type: str
    life_area: Optional[str] = None
    tags: List[str] = []
    is_pinned: bool = False
    word_count: int = 0
    backlinks: List[str] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Response for listing notes."""
    notes: List[NoteResponse]
    total: int


# =============================================================================
# Goal Schemas
# =============================================================================

class MilestoneSchema(BaseModel):
    """Milestone within a goal."""
    id: Optional[str] = None
    title: str
    completed: bool = False
    completed_at: Optional[str] = None


class GoalCreate(BaseModel):
    """Request body for creating a goal."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    life_area: Optional[str] = None
    target_date: Optional[str] = None
    milestones: Optional[List[MilestoneSchema]] = None


class GoalUpdate(BaseModel):
    """Request body for updating a goal."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None  # active, completed, paused, abandoned
    life_area: Optional[str] = None
    target_date: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class ProgressLogCreate(BaseModel):
    """Request body for logging goal progress."""
    progress_delta: int = Field(..., ge=-100, le=100)
    note: Optional[str] = None


class GoalResponse(BaseModel):
    """Goal data returned from API."""
    id: int
    title: str
    description: Optional[str] = None
    status: str
    life_area: Optional[str] = None
    target_date: Optional[str] = None
    progress: int = 0
    milestones: List[MilestoneSchema] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class GoalListResponse(BaseModel):
    """Response for listing goals."""
    goals: List[GoalResponse]
    total: int


# =============================================================================
# Dashboard Schemas
# =============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    tasks_today: int
    tasks_overdue: int
    completion_rate: float
    streak_days: int = 0


class GoalSummary(BaseModel):
    """Brief goal summary for dashboard."""
    id: int
    title: str
    progress: int
    life_area: Optional[str] = None


class ActivityItem(BaseModel):
    """Recent activity item."""
    id: str
    type: str  # task_completed, goal_progress, note_updated, event_created
    title: str
    timestamp: str


class DashboardResponse(BaseModel):
    """Complete dashboard data."""
    stats: DashboardStats
    priority_tasks: List[TaskResponse]
    upcoming_events: List[EventResponse]
    goal_summaries: List[GoalSummary]
    recent_activity: List[ActivityItem]


# =============================================================================
# Natural Language Schemas
# =============================================================================

class NLPRequest(BaseModel):
    """Request body for natural language processing."""
    query: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None


class NLPResponse(BaseModel):
    """Response from natural language processing."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    parsed: Optional[Dict[str, Any]] = None  # Parsed intent/entities
    suggestions: Optional[List[str]] = None


# =============================================================================
# Project Schemas
# =============================================================================

class ProjectResponse(BaseModel):
    """Project data returned from API."""
    id: int
    name: str
    description: Optional[str] = None
    status: str
    life_area: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    due_date: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Response for listing projects."""
    projects: List[ProjectResponse]
    total: int

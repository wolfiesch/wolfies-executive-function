"""
Calendar event management API endpoints.

Provides CRUD operations for calendar events, leveraging the CalendarAgent
for business logic.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_calendar_agent
from backend.schemas import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventListResponse,
    AgentResponseSchema,
)
from src.agents import CalendarAgent

router = APIRouter(prefix="/events", tags=["calendar"])


def _row_to_event_response(row: dict) -> EventResponse:
    """Convert database row to EventResponse schema."""
    return EventResponse(
        id=row["id"],
        title=row["title"],
        description=row.get("description"),
        start_time=row.get("start_time", ""),
        end_time=row.get("end_time", ""),
        all_day=row.get("all_day", False),
        location=row.get("location"),
        status=row.get("status", "confirmed"),
        event_type=row.get("event_type", "meeting"),
        color=row.get("color"),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


@router.get("/", response_model=EventListResponse)
async def list_events(
    days_ahead: int = Query(7, ge=1, le=365, description="Days ahead to fetch"),
    status: Optional[str] = Query(None, description="Filter by status"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    agent: CalendarAgent = Depends(get_calendar_agent),
):
    """
    List upcoming calendar events.

    By default, returns events for the next 7 days.
    """
    context = {"days_ahead": days_ahead}
    if status:
        context["status"] = status
    if event_type:
        context["event_type"] = event_type

    response = agent.process("list_events", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    events_data = response.data.get("events", []) if response.data else []

    return EventListResponse(
        events=[_row_to_event_response(e) for e in events_data],
        total=len(events_data),
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    agent: CalendarAgent = Depends(get_calendar_agent),
):
    """Get a single event by ID."""
    response = agent.process("get_event", {"event_id": event_id})

    if not response.success:
        raise HTTPException(status_code=404, detail=response.message)

    event_data = response.data.get("event") if response.data else None
    if not event_data:
        raise HTTPException(status_code=404, detail="Event not found")

    return _row_to_event_response(event_data)


@router.post("/", response_model=AgentResponseSchema, status_code=201)
async def create_event(
    event: EventCreate,
    agent: CalendarAgent = Depends(get_calendar_agent),
):
    """Create a new calendar event."""
    context = {
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "all_day": event.all_day,
        "location": event.location,
        "event_type": event.event_type,
        "color": event.color,
    }
    context = {k: v for k, v in context.items() if v is not None}

    response = agent.process("add_event", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.put("/{event_id}", response_model=AgentResponseSchema)
async def update_event(
    event_id: int,
    event: EventUpdate,
    agent: CalendarAgent = Depends(get_calendar_agent),
):
    """Update an existing event."""
    context = {"event_id": event_id}
    update_data = event.model_dump(exclude_unset=True)
    context.update(update_data)

    response = agent.process("update_event", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.delete("/{event_id}", response_model=AgentResponseSchema)
async def delete_event(
    event_id: int,
    agent: CalendarAgent = Depends(get_calendar_agent),
):
    """Delete an event."""
    response = agent.process("delete_event", {"event_id": event_id})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
    )


@router.get("/free-slots/", response_model=AgentResponseSchema)
async def find_free_time(
    date: Optional[str] = Query(None, description="Date to check (ISO format)"),
    duration_minutes: int = Query(60, ge=15, description="Desired slot duration"),
    agent: CalendarAgent = Depends(get_calendar_agent),
):
    """
    Find available time slots on a given day.

    Returns free time slots based on work hours configuration.
    """
    context = {"duration_minutes": duration_minutes}
    if date:
        context["date"] = date

    response = agent.process("find_free_time", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )

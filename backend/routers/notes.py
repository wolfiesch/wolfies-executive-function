"""
Notes management API endpoints.

Provides CRUD operations for notes, leveraging the NoteAgent
for business logic and wiki-link handling.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_note_agent
from backend.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    NoteListResponse,
    AgentResponseSchema,
)
from src.agents import NoteAgent

router = APIRouter(prefix="/notes", tags=["notes"])


def _row_to_note_response(row: dict) -> NoteResponse:
    """Convert database row to NoteResponse schema."""
    tags = row.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    backlinks = row.get("backlinks", [])
    if isinstance(backlinks, str):
        backlinks = [b.strip() for b in backlinks.split(",") if b.strip()]

    return NoteResponse(
        id=row["id"],
        title=row["title"],
        content=row.get("content", ""),
        note_type=row.get("note_type", "note"),
        life_area=row.get("life_area"),
        tags=tags,
        is_pinned=row.get("is_pinned", False),
        word_count=row.get("word_count", 0),
        backlinks=backlinks,
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    note_type: Optional[str] = Query(None, description="Filter by note type"),
    life_area: Optional[str] = Query(None, description="Filter by life area"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    pinned_only: bool = Query(False, description="Only show pinned notes"),
    agent: NoteAgent = Depends(get_note_agent),
):
    """
    List notes with optional filters.

    Supports filtering by type, life area, tag, and pinned status.
    """
    context = {}
    if note_type:
        context["note_type"] = note_type
    if life_area:
        context["life_area"] = life_area
    if tag:
        context["tag"] = tag
    if pinned_only:
        context["pinned_only"] = True

    response = agent.process("list_notes", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    notes_data = response.data.get("notes", []) if response.data else []

    return NoteListResponse(
        notes=[_row_to_note_response(n) for n in notes_data],
        total=len(notes_data),
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    agent: NoteAgent = Depends(get_note_agent),
):
    """Get a single note by ID, including content and backlinks."""
    response = agent.process("get_note", {"note_id": note_id})

    if not response.success:
        raise HTTPException(status_code=404, detail=response.message)

    note_data = response.data.get("note") if response.data else None
    if not note_data:
        raise HTTPException(status_code=404, detail="Note not found")

    return _row_to_note_response(note_data)


@router.post("/", response_model=AgentResponseSchema, status_code=201)
async def create_note(
    note: NoteCreate,
    agent: NoteAgent = Depends(get_note_agent),
):
    """
    Create a new note.

    Wiki-links ([[Note Name]]) in content will be automatically
    processed to create bidirectional links.
    """
    context = {
        "title": note.title,
        "content": note.content,
        "note_type": note.note_type,
        "life_area": note.life_area,
        "tags": note.tags,
        "is_pinned": note.is_pinned,
    }
    context = {k: v for k, v in context.items() if v is not None}

    response = agent.process("create_note", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.put("/{note_id}", response_model=AgentResponseSchema)
async def update_note(
    note_id: int,
    note: NoteUpdate,
    agent: NoteAgent = Depends(get_note_agent),
):
    """Update an existing note."""
    context = {"note_id": note_id}
    update_data = note.model_dump(exclude_unset=True)
    context.update(update_data)

    response = agent.process("update_note", context)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
        suggestions=response.suggestions,
    )


@router.delete("/{note_id}", response_model=AgentResponseSchema)
async def delete_note(
    note_id: int,
    agent: NoteAgent = Depends(get_note_agent),
):
    """Delete a note."""
    response = agent.process("delete_note", {"note_id": note_id})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return AgentResponseSchema(
        success=response.success,
        message=response.message,
        data=response.data,
    )


@router.get("/search/", response_model=NoteListResponse)
async def search_notes(
    q: str = Query(..., min_length=1, description="Search query"),
    agent: NoteAgent = Depends(get_note_agent),
):
    """
    Search notes by title and content.

    Uses full-text search across note content.
    """
    response = agent.process("search_notes", {"query": q})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    notes_data = response.data.get("notes", []) if response.data else []

    return NoteListResponse(
        notes=[_row_to_note_response(n) for n in notes_data],
        total=len(notes_data),
    )


@router.get("/{note_id}/backlinks", response_model=NoteListResponse)
async def get_note_backlinks(
    note_id: int,
    agent: NoteAgent = Depends(get_note_agent),
):
    """
    Get all notes that link to this note.

    Part of the PKM (Personal Knowledge Management) feature
    for bidirectional linking.
    """
    response = agent.process("get_backlinks", {"note_id": note_id})

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    notes_data = response.data.get("backlinks", []) if response.data else []

    return NoteListResponse(
        notes=[_row_to_note_response(n) for n in notes_data],
        total=len(notes_data),
    )

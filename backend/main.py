"""
Life Planner FastAPI Backend

This is the main entry point for the API server that exposes the
agent layer to the React frontend.

Architecture:
- FastAPI handles HTTP routing and request/response validation
- Pydantic schemas ensure type safety
- Agents handle all business logic
- Database provides persistence via SQLite

Run with:
    uvicorn backend.main:app --reload --port 8000

Or:
    python -m backend.main
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.routers import (
    tasks_router,
    calendar_router,
    notes_router,
    goals_router,
    dashboard_router,
    nlp_router,
)
from backend.dependencies import get_database, get_config
from backend.websocket import websocket_endpoint, ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Runs startup and shutdown tasks:
    - Startup: Verify database connection
    - Shutdown: Clean up resources
    """
    # Startup
    try:
        db = get_database()
        config = get_config()
        print(f"Database connected: {db.db_path}")
        print(f"Config loaded from: {config.config_dir}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Run 'python scripts/init_db.py' to create the database.")
        # Allow app to start but endpoints will fail gracefully

    yield

    # Shutdown (cleanup if needed)
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Life Planner API",
    description="""
    AI-powered life planning system API.

    ## Features

    - **Tasks**: Create, update, complete, and search tasks with natural language support
    - **Calendar**: Manage events, find free time, block focus time
    - **Notes**: Create and search notes with wiki-style linking
    - **Goals**: Track goals with milestones and progress logging
    - **Dashboard**: Unified view of today's priorities and stats
    - **NLP**: Natural language interface for all operations

    ## Natural Language Examples

    - "Add a task to buy groceries tomorrow at 3pm"
    - "Schedule a meeting with the team next Monday"
    - "What's on my plate today?"
    - "Create a note about project architecture"
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
# In production, replace with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(notes_router)
app.include_router(goals_router)
app.include_router(dashboard_router)
app.include_router(nlp_router)


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================
# Real-time updates for connected clients.
# Clients subscribe to topics and receive notifications when data changes.
# ============================================================

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Protocol:
    - Client sends: { "type": "subscribe", "topics": ["tasks", "calendar"] }
    - Server sends: { "type": "task_created", "data": {...}, "timestamp": "..." }

    Topics available:
    - tasks: Task create/update/delete/complete events
    - calendar: Event create/update/delete events
    - notes: Note create/update events
    - goals: Goal progress updates
    - dashboard: Dashboard data refresh triggers
    """
    await websocket_endpoint(websocket)


@app.get("/")
async def root():
    """API root - returns basic info and available endpoints."""
    return {
        "name": "Life Planner API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "tasks": "/tasks",
            "events": "/events",
            "notes": "/notes",
            "goals": "/goals",
            "dashboard": "/dashboard/today",
            "nlp": "/nlp/ask",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        db = get_database()
        # Quick database check
        db.execute_one("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Allow running directly with: python -m backend.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

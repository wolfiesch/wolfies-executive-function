"""
Vercel Serverless Function Entry Point

Exposes the FastAPI application as a Vercel serverless function.
All API routes are handled by this single entry point.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set default to use PostgreSQL in production
if 'DATABASE_URL' in os.environ and 'USE_SQLITE' not in os.environ:
    os.environ['USE_SQLITE'] = '0'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import routers
from backend.routers import (
    tasks_router,
    calendar_router,
    notes_router,
    goals_router,
    dashboard_router,
    nlp_router,
)

# Create a lightweight app for serverless
app = FastAPI(
    title="Life Planner API",
    description="AI-powered life planning API",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://wolfie-life-planner.vercel.app",
        "https://*.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(notes_router)
app.include_router(goals_router)
app.include_router(dashboard_router)
app.include_router(nlp_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "life-planner-api"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Mangum adapter for AWS Lambda/Vercel
handler = Mangum(app, lifespan="off")

"""
Dependency injection for FastAPI endpoints.

Provides singleton instances of Database, Config, and MasterAgent
to be used across all API routes.

Pattern: **Dependency Injection** - FastAPI's Depends() mechanism
allows us to inject shared resources into route handlers without
global state, making the code testable and maintainable.
"""

from functools import lru_cache
from typing import Generator
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.database import Database
from src.core.config import Config
from src.agents import MasterAgent, TaskAgent, CalendarAgent, NoteAgent, GoalAgent
from src.dashboard.aggregator import DashboardAggregator


@lru_cache()
def get_config() -> Config:
    """
    Get cached Config instance.

    lru_cache ensures we only create one Config instance
    for the lifetime of the application (singleton pattern).
    """
    return Config()


@lru_cache()
def get_database() -> Database:
    """
    Get cached Database instance.

    The Database class handles connection pooling internally,
    so we only need one instance.
    """
    return Database()


def get_master_agent() -> MasterAgent:
    """
    Get MasterAgent instance for natural language processing.

    Creates a new agent per request to avoid any state issues,
    but shares the underlying DB and Config singletons.
    """
    db = get_database()
    config = get_config()
    return MasterAgent(db, config)


def get_task_agent() -> TaskAgent:
    """Get TaskAgent for direct task operations."""
    db = get_database()
    config = get_config()
    return TaskAgent(db, config)


def get_calendar_agent() -> CalendarAgent:
    """Get CalendarAgent for event operations."""
    db = get_database()
    config = get_config()
    return CalendarAgent(db, config)


def get_note_agent() -> NoteAgent:
    """Get NoteAgent for note operations."""
    db = get_database()
    config = get_config()
    return NoteAgent(db, config)


def get_goal_agent() -> GoalAgent:
    """Get GoalAgent for goal operations."""
    db = get_database()
    config = get_config()
    return GoalAgent(db, config)


def get_dashboard_aggregator() -> DashboardAggregator:
    """Get DashboardAggregator for dashboard data."""
    db = get_database()
    config = get_config()
    return DashboardAggregator(db, config)

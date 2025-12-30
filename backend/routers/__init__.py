"""
API routers for the Life Planner backend.

Each router handles a specific domain:
- tasks: Task CRUD and search
- calendar: Event management
- notes: Note management and search
- goals: Goal tracking and milestones
- dashboard: Aggregated dashboard data
- nlp: Natural language processing endpoint
"""

from .tasks import router as tasks_router
from .calendar import router as calendar_router
from .notes import router as notes_router
from .goals import router as goals_router
from .dashboard import router as dashboard_router
from .nlp import router as nlp_router

__all__ = [
    'tasks_router',
    'calendar_router',
    'notes_router',
    'goals_router',
    'dashboard_router',
    'nlp_router',
]

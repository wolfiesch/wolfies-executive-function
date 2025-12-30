"""
Agent Layer for AI Life Planner

This module implements the sub-agent architecture for the life planner system.
Each agent handles a specific domain (tasks, calendar, notes, goals, reviews) and provides
a consistent interface for processing user requests.

Architecture Overview:
- MasterAgent: Central router that orchestrates specialized sub-agents
- BaseAgent: Abstract base class defining the agent interface
- AgentResponse: Standard response structure for agent outputs
- TaskAgent: Task management (add, complete, list, search, update)
- CalendarAgent: Event scheduling, time blocking, and free time finding
- NoteAgent: Note-taking, journaling, and knowledge management (PKM)
- GoalAgent: Goal tracking, milestones, and progress monitoring (OKR-style)
- ReviewAgent: Daily/weekly reviews, reflections, and productivity insights

Usage:
    from src.agents import MasterAgent, AgentResponse
    from src.core import Database, Config

    db = Database()
    config = Config()

    # Use MasterAgent for natural language routing
    master = MasterAgent(db, config)
    response = master.process("Buy groceries tomorrow")

    # Or use specialized agents directly
    task_agent = TaskAgent(db, config)
    response = task_agent.process("add_task", {"text": "Buy groceries tomorrow"})

    # Use ReviewAgent for daily/weekly reviews
    review_agent = ReviewAgent(db, config)
    response = review_agent.process("daily_review", {})
"""

from .base_agent import BaseAgent, AgentResponse, AgentContext
from .task_agent import TaskAgent
from .calendar_agent import CalendarAgent
from .note_agent import NoteAgent
from .goal_agent import GoalAgent
from .review_agent import ReviewAgent
from .master_agent import MasterAgent

__all__ = [
    'BaseAgent',
    'AgentResponse',
    'AgentContext',
    'TaskAgent',
    'CalendarAgent',
    'NoteAgent',
    'GoalAgent',
    'ReviewAgent',
    'MasterAgent',
]

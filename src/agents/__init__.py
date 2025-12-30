"""
Agent Layer for AI Life Planner

This module implements the sub-agent architecture for the life planner system.
Each agent handles a specific domain (tasks, calendar, notes, etc.) and provides
a consistent interface for processing user requests.

Architecture Overview:
- MasterAgent: Central router that orchestrates specialized sub-agents
- BaseAgent: Abstract base class defining the agent interface
- AgentResponse: Standard response structure for agent outputs
- TaskAgent: Specialized agent for task management

Future agents (planned):
- CalendarAgent: Event scheduling and time blocking
- NoteAgent: Note-taking and knowledge management
- GoalAgent: Goal tracking and progress monitoring
- ReviewAgent: Daily/weekly reviews and reflections

Usage:
    from src.agents import MasterAgent, AgentResponse
    from src.core import Database, Config

    db = Database()
    config = Config()

    # Use MasterAgent for natural language routing
    master = MasterAgent(db, config)
    response = master.process("Buy groceries tomorrow")

    # Or use TaskAgent directly for specific intents
    task_agent = TaskAgent(db, config)
    response = task_agent.process("add_task", {"text": "Buy groceries tomorrow"})
"""

from .base_agent import BaseAgent, AgentResponse, AgentContext
from .task_agent import TaskAgent
from .master_agent import MasterAgent

__all__ = [
    'BaseAgent',
    'AgentResponse',
    'AgentContext',
    'TaskAgent',
    'MasterAgent',
]

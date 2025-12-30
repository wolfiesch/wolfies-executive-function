"""
Base Agent for AI Life Planner
Defines abstract base class and common interfaces for all specialized agents.

The Agent Layer follows a sub-agent architecture pattern where:
- Each agent handles a specific domain (tasks, calendar, notes, etc.)
- Agents share a common interface for lifecycle management
- Agents can hand off requests to other agents when appropriate
- All agents maintain consistent logging and state management
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging
import json


@dataclass
class AgentResponse:
    """
    Standard response structure from any agent.

    Provides a consistent interface for agent outputs, enabling:
    - Success/failure tracking
    - Human-readable messages
    - Structured data payloads
    - Agent-to-agent handoff mechanism

    Attributes:
        success: Whether the operation completed successfully
        message: Human-readable description of the result
        data: Optional structured data (task details, search results, etc.)
        handoff_to: If set, name of agent to hand off to for continued processing
        handoff_context: Context data to pass to the handoff agent
        suggestions: Optional list of follow-up actions the user might want
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    handoff_to: Optional[str] = None
    handoff_context: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for serialization."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "handoff_to": self.handoff_to,
            "handoff_context": self.handoff_context,
            "suggestions": self.suggestions
        }

    @classmethod
    def error(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'AgentResponse':
        """Factory method for creating error responses."""
        return cls(success=False, message=message, data=data)

    @classmethod
    def ok(cls, message: str, data: Optional[Dict[str, Any]] = None,
           suggestions: Optional[List[str]] = None) -> 'AgentResponse':
        """Factory method for creating success responses."""
        return cls(success=True, message=message, data=data, suggestions=suggestions)


@dataclass
class AgentContext:
    """
    Shared context passed between agents during request processing.

    Maintains state that should be accessible across agent handoffs,
    including user preferences, conversation history, and current session data.

    Attributes:
        user_timezone: User's timezone for date/time interpretation
        current_time: Current datetime in UTC
        conversation_history: Recent conversation turns for context
        preferences: User preferences loaded from config
        session_data: Temporary data for current session
    """
    user_timezone: str = "America/Los_Angeles"
    current_time: Optional[datetime] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    session_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.current_time is None:
            self.current_time = datetime.now(timezone.utc)


class BaseAgent(ABC):
    """
    Abstract base class for all Life Planner agents.

    Provides common functionality for:
    - Database access
    - Configuration management
    - Logging
    - Agent-to-agent handoff
    - Intent matching

    Subclasses must implement:
    - can_handle(): Determine if agent can process given intent
    - process(): Execute the actual request handling
    - get_supported_intents(): Return list of intents this agent handles

    Design Pattern: Template Method
    - Base class defines the skeleton of operations
    - Subclasses provide specific implementations
    """

    def __init__(self, db, config, name: str):
        """
        Initialize the base agent.

        Args:
            db: Database instance for data access
            config: Config instance for settings/preferences
            name: Unique identifier for this agent (e.g., "task", "calendar")
        """
        self.db = db
        self.config = config
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self._initialized = False

    def initialize(self) -> bool:
        """
        Perform any required agent initialization.

        Override in subclasses if agent needs startup configuration.
        Returns True if initialization successful.
        """
        self._initialized = True
        self.logger.info(f"{self.name} agent initialized")
        return True

    def cleanup(self) -> None:
        """
        Clean up agent resources before shutdown.

        Override in subclasses if agent needs cleanup logic.
        """
        self._initialized = False
        self.logger.info(f"{self.name} agent cleaned up")

    @abstractmethod
    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the given intent.

        Used by the master agent (router) to find the appropriate
        specialized agent for a request.

        Args:
            intent: The classified intent of the user's request
            context: Additional context that may affect handling capability

        Returns:
            True if this agent can handle the intent, False otherwise
        """
        pass

    @abstractmethod
    def process(self, intent: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process the request and return a response.

        Main entry point for agent functionality. Receives the intent
        and context, performs the required operation, and returns
        a structured response.

        Args:
            intent: The classified intent of the user's request
            context: Request context including parameters, user info, etc.

        Returns:
            AgentResponse with success/failure status and relevant data
        """
        pass

    @abstractmethod
    def get_supported_intents(self) -> List[str]:
        """
        Return list of intents this agent can handle.

        Used for agent discovery and routing configuration.

        Returns:
            List of intent strings (e.g., ["add_task", "complete_task"])
        """
        pass

    def handoff(self, to_agent: str, context: Dict[str, Any],
                reason: str = "") -> AgentResponse:
        """
        Create a handoff response to transfer processing to another agent.

        Used when this agent determines another agent is better suited
        to handle the request, or when a multi-agent workflow is needed.

        Args:
            to_agent: Name of the agent to hand off to
            context: Context to pass to the receiving agent
            reason: Optional explanation for the handoff

        Returns:
            AgentResponse configured for handoff
        """
        message = f"Handing off to {to_agent}"
        if reason:
            message += f": {reason}"

        self.logger.info(f"Handoff from {self.name} to {to_agent}: {reason}")

        return AgentResponse(
            success=True,
            message=message,
            handoff_to=to_agent,
            handoff_context=context
        )

    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an action taken by this agent.

        Provides consistent action logging for debugging and audit trails.

        Args:
            action: Description of the action taken
            details: Optional additional details as key-value pairs
        """
        log_entry = {
            "agent": self.name,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if details:
            log_entry["details"] = details

        self.logger.info(json.dumps(log_entry))

    def validate_required_params(self, context: Dict[str, Any],
                                  required: List[str]) -> Optional[AgentResponse]:
        """
        Validate that required parameters are present in context.

        Helper method for parameter validation in process() implementations.

        Args:
            context: Request context to validate
            required: List of required parameter names

        Returns:
            AgentResponse with error if validation fails, None if valid
        """
        missing = [p for p in required if p not in context or context[p] is None]
        if missing:
            return AgentResponse.error(
                f"Missing required parameters: {', '.join(missing)}"
            )
        return None

    def get_config_value(self, key: str, section: str = "preferences",
                         default: Any = None) -> Any:
        """
        Get a configuration value with fallback to default.

        Args:
            key: Configuration key to retrieve
            section: Configuration section (settings, para, preferences)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, section=section, default=default)

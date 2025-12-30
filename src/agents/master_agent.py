"""
Master Agent (Router) for AI Life Planner

The MasterAgent is the orchestration layer that:
1. Receives natural language input from the user
2. Classifies the intent (task, calendar, note, goal, etc.)
3. Routes to the appropriate specialized agent
4. Handles agent-to-agent handoffs
5. Manages conversation context

This implements the "Master Agent" pattern where a central router delegates
to specialized sub-agents based on the domain of the user's request.

Design Pattern: Router/Dispatcher
- Single entry point for all user requests
- Intent classification determines routing
- Supports chained handoffs between agents
- Maintains conversation context across agent transitions
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import re

from .base_agent import BaseAgent, AgentResponse, AgentContext
from .task_agent import TaskAgent
from .calendar_agent import CalendarAgent
from .note_agent import NoteAgent
from .goal_agent import GoalAgent
from .review_agent import ReviewAgent


class MasterAgent:
    """
    Central routing agent that orchestrates specialized sub-agents.

    The MasterAgent does not inherit from BaseAgent because it serves
    a different role - it routes requests rather than processing them directly.

    Responsibilities:
    - Intent classification from natural language
    - Agent registry management
    - Request routing to appropriate agents
    - Handoff handling between agents
    - Conversation context management
    - Fallback handling for unknown intents

    Attributes:
        agents: Registry of available specialized agents
        intent_patterns: Keyword patterns for intent classification
        context: Shared conversation context
        max_handoff_depth: Maximum chain length to prevent infinite loops
    """

    # Intent classification patterns
    # Maps keywords/phrases to (domain, intent) tuples
    INTENT_PATTERNS = {
        # Task intents
        "task": {
            "add_task": [
                r"\badd\s+(?:a\s+)?task\b", r"\bnew\s+task\b", r"\bcreate\s+(?:a\s+)?task\b",
                r"\btodo\b", r"\bto-do\b", r"\bto do\b",
                r"\bremind\s+me\b", r"\breminder\b",
                r"\bneed\s+to\b", r"\bgot\s+to\b", r"\bgotta\b",
                r"\bput\s+on\s+(?:my\s+)?list\b",
            ],
            "complete_task": [
                r"\bcomplete(?:d)?\b", r"\bdone\b", r"\bfinish(?:ed)?\b",
                r"\bmark\s+(?:as\s+)?(?:done|complete|finished)\b",
                r"\bcheck\s+off\b", r"\btick\s+off\b",
            ],
            "list_tasks": [
                r"\blist\s+(?:my\s+)?tasks?\b", r"\bshow\s+(?:my\s+)?tasks?\b",
                r"\bwhat\s+(?:are\s+)?(?:my\s+)?tasks?\b",
                r"\bwhat(?:'s|s)?\s+on\s+my\s+(?:plate|list)\b",
                r"\bmy\s+tasks?\b",
            ],
            "search_tasks": [
                r"\bsearch\s+(?:for\s+)?tasks?\b", r"\bfind\s+(?:a\s+)?task\b",
                r"\blook(?:ing)?\s+for\s+(?:a\s+)?task\b",
            ],
            "update_task": [
                r"\bupdate\s+task\b", r"\bmodify\s+task\b", r"\bchange\s+task\b",
                r"\bedit\s+task\b", r"\breschedule\s+task\b",
                r"\bset\s+priority\b", r"\bset\s+due\s+date\b",
            ],
        },

        # Calendar intents
        "calendar": {
            "add_event": [
                r"\bschedule\b", r"\bmeeting\b", r"\bevent\b",
                r"\bappointment\b",
                r"\bbook\s+(?:a\s+)?(?:time|slot)\b",
                r"\badd\s+(?:to\s+)?(?:my\s+)?calendar\b",
                r"\bcreate\s+(?:a\s+)?(?:meeting|event|appointment)\b",
            ],
            "list_events": [
                r"\bwhat(?:'s|s)?\s+on\s+(?:my\s+)?calendar\b",
                r"\bshow\s+(?:my\s+)?(?:calendar|schedule)\b",
                r"\bmy\s+(?:schedule|agenda)\b",
                r"\blist\s+(?:my\s+)?(?:events?|meetings?)\b",
                r"\bupcoming\s+(?:events?|meetings?)\b",
            ],
            "find_free_time": [
                r"\bfree\s+time\b", r"\bavailable\s+(?:time|slots?)\b",
                r"\bwhen\s+am\s+i\s+free\b", r"\bfind\s+(?:a\s+)?(?:time|slot)\b",
                r"\bopen\s+(?:time|slots?)\b",
            ],
            "block_time": [
                r"\bblock\s+(?:off\s+)?(?:time|hours?)\b",
                r"\btime\s+block\b", r"\bdeep\s+work\b", r"\bfocus\s+time\b",
            ],
        },

        # Note intents
        "note": {
            "create_note": [
                r"\bnote\b", r"\bwrite\s+down\b", r"\bjot\s+down\b",
                r"\bjot\b", r"\bremember\s+that\b",
                r"\bnote\s+to\s+self\b", r"\bcreate\s+(?:a\s+)?note\b",
                r"\bnew\s+note\b", r"\badd\s+(?:a\s+)?note\b",
            ],
            "add_journal_entry": [
                r"\bjournal\b", r"\bdiary\b", r"\breflect(?:ion)?\b",
                r"\btoday\s+(?:i|was|felt)\b", r"\bmy\s+day\b",
                r"\bdaily\s+(?:entry|log)\b",
            ],
            "search_notes": [
                r"\bsearch\s+(?:my\s+)?notes?\b", r"\bfind\s+(?:a\s+)?note\b",
                r"\blook(?:ing)?\s+(?:in|through)\s+(?:my\s+)?notes?\b",
            ],
            "list_notes": [
                r"\blist\s+(?:my\s+)?notes?\b", r"\bshow\s+(?:my\s+)?notes?\b",
                r"\bmy\s+notes?\b", r"\ball\s+notes?\b",
            ],
            "link_notes": [
                r"\blink\s+notes?\b", r"\bconnect\s+notes?\b",
                r"\brelate\s+(?:to|notes?)\b",
            ],
        },

        # Goal intents
        "goal": {
            "create_goal": [
                r"\bgoal\b", r"\bobjective\b", r"\btarget\b",
                r"\bokr\b", r"\bset\s+(?:a\s+)?goal\b",
                r"\bnew\s+goal\b", r"\bi\s+want\s+to\b",
                r"\bby\s+(?:the\s+)?end\s+of\b",
            ],
            "add_milestone": [
                r"\bmilestone\b", r"\bcheckpoint\b",
                r"\badd\s+(?:a\s+)?milestone\b",
            ],
            "log_progress": [
                r"\bprogress\b", r"\blog\s+progress\b",
                r"\bupdate\s+(?:my\s+)?(?:progress|goal)\b",
                r"\bcompleted\s+\d+\b", r"\bfinished\s+\d+\b",
            ],
            "review_goals": [
                r"\bhow\s+am\s+i\s+doing\b", r"\bgoal\s+review\b",
                r"\breview\s+(?:my\s+)?goals?\b",
                r"\bstatus\s+(?:of\s+)?(?:my\s+)?goals?\b",
                r"\bcheck\s+(?:my\s+)?goals?\b",
            ],
            "list_goals": [
                r"\blist\s+(?:my\s+)?goals?\b", r"\bshow\s+(?:my\s+)?goals?\b",
                r"\bmy\s+goals?\b", r"\ball\s+goals?\b",
            ],
        },

        # Review intents
        "review": {
            "daily_review": [
                r"\bdaily\s+review\b", r"\btoday(?:'s|s)?\s+review\b",
                r"\breview\s+(?:my\s+)?day\b", r"\bhow\s+did\s+(?:my\s+)?day\s+go\b",
                r"\bwhat\s+did\s+i\s+(?:do|accomplish)\s+today\b",
                r"\bend\s+of\s+day\b", r"\beod\s+review\b",
                r"\bwrap\s+up\s+(?:my\s+)?day\b",
            ],
            "weekly_review": [
                r"\bweekly\s+review\b", r"\bthis\s+week(?:'s|s)?\s+review\b",
                r"\breview\s+(?:my\s+)?week\b", r"\bhow\s+(?:was|did)\s+(?:my\s+)?week\b",
                r"\bwhat\s+did\s+i\s+(?:do|accomplish)\s+this\s+week\b",
                r"\bweek\s+(?:in\s+)?review\b", r"\bweekend\s+review\b",
            ],
            "add_reflection": [
                r"\breflect\s+on\s+(?:my\s+)?(?:day|today|week|this)\b",
                r"\badd\s+(?:a\s+)?reflection\b",
                r"\bthink(?:ing)?\s+about\s+(?:my|how)\b",
                r"\bhow\s+(?:i\s+)?feel\s+(?:about|today|right\s+now)\b",
                r"\btoday\s+(?:i\s+)?(?:felt|feel|was)\s+(?:good|bad|happy|stressed|productive)\b",
                r"\bi(?:'m|\s+am)\s+(?:feeling|grateful|happy|stressed|tired|overwhelmed)\b",
                r"\bmy\s+thoughts\s+on\b", r"\bprocessing\s+(?:my|the)\b",
                r"\bgrateful\s+(?:for|that)\b", r"\bthankful\s+(?:for|that)\b",
            ],
            "get_insights": [
                r"\binsights?\b", r"\bpatterns?\b", r"\btrends?\b",
                r"\bproductivity\s+(?:patterns?|insights?|trends?)\b",
                r"\banalyze\s+(?:my\s+)?(?:productivity|performance|habits?)\b",
                r"\bhow\s+(?:am\s+i|have\s+i\s+been)\s+doing\b",
                r"\bwhat(?:'s|s)?\s+working\b",
            ],
            "generate_prompts": [
                r"\breflection\s+prompts?\b", r"\bprompts?\s+(?:for\s+)?reflect(?:ion)?\b",
                r"\bquestions?\s+(?:for|to)\s+reflect\b",
                r"\bwhat\s+should\s+i\s+(?:think|reflect)\s+(?:about|on)\b",
            ],
        },

        # Query intents (can route to multiple agents based on context)
        "query": {
            "status_query": [
                r"^what\b", r"^show\b", r"^list\b",
                r"\bhow\s+many\b", r"\bstatus\b",
            ],
        },
    }

    # Default intents when domain is detected but specific intent unclear
    DEFAULT_INTENTS = {
        "task": "list_tasks",
        "calendar": "list_events",
        "note": "list_notes",
        "goal": "list_goals",
        "review": "daily_review",
        "query": "status_query",
    }

    def __init__(self, db, config):
        """
        Initialize the Master Agent.

        Args:
            db: Database instance for data access
            config: Config instance for settings/preferences
        """
        self.db = db
        self.config = config
        self.logger = logging.getLogger("agent.master")

        # Initialize agent registry
        self.agents: Dict[str, Optional[BaseAgent]] = {
            "task": TaskAgent(db, config),
            "calendar": CalendarAgent(db, config),
            "note": NoteAgent(db, config),
            "goal": GoalAgent(db, config),
            "review": ReviewAgent(db, config),
        }

        # Initialize agents that are available
        for name, agent in self.agents.items():
            if agent is not None:
                agent.initialize()

        # Conversation context
        self.context = AgentContext()

        # Maximum handoff depth to prevent infinite loops
        self.max_handoff_depth = 5

        self.logger.info("MasterAgent initialized with agents: %s",
                        [k for k, v in self.agents.items() if v is not None])

    def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Main entry point for processing user input.

        Classifies the intent, routes to the appropriate agent,
        and handles any agent-to-agent handoffs.

        Args:
            user_input: Natural language input from the user
            context: Optional additional context (preferences, session data, etc.)

        Returns:
            AgentResponse from the processing agent
        """
        if context is None:
            context = {}

        # Add the original user input to context
        context["text"] = user_input
        context["original_input"] = user_input

        # Classify intent
        domain, intent = self.classify_intent(user_input)

        self.logger.info("Classified intent: domain=%s, intent=%s", domain, intent)

        # Route to appropriate agent
        return self.route(intent, domain, context)

    def classify_intent(self, user_input: str) -> Tuple[str, str]:
        """
        Classify the intent of user input.

        Uses pattern matching to determine:
        1. The domain (task, calendar, note, goal)
        2. The specific intent within that domain

        Args:
            user_input: Natural language input from the user

        Returns:
            Tuple of (domain, intent) strings
        """
        text_lower = user_input.lower()

        best_match = None
        best_score = 0

        for domain, intents in self.INTENT_PATTERNS.items():
            for intent, patterns in intents.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        # Score based on pattern specificity (longer patterns = more specific)
                        score = len(pattern)
                        if score > best_score:
                            best_score = score
                            best_match = (domain, intent)

        if best_match:
            return best_match

        # Fallback: try to detect domain even without specific intent
        domain = self._detect_domain(text_lower)
        if domain:
            return domain, self.DEFAULT_INTENTS.get(domain, "unknown")

        # Ultimate fallback: assume task domain for action-oriented input
        # This handles cases like "Buy groceries" which imply task creation
        if self._looks_like_action(text_lower):
            return "task", "add_task"

        return "unknown", "unknown"

    def _detect_domain(self, text: str) -> Optional[str]:
        """
        Detect domain from text when specific intent is unclear.

        Args:
            text: Lowercase user input

        Returns:
            Domain string or None
        """
        domain_keywords = {
            "task": ["task", "todo", "to-do", "remind"],
            "calendar": ["calendar", "schedule", "meeting", "event", "appointment"],
            "note": ["note", "notes", "write down", "jot"],
            "goal": ["goal", "objective", "milestone", "progress"],
            "review": ["review", "reflect", "reflection", "insights", "patterns", "daily review", "weekly review"],
        }

        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return domain

        return None

    def _looks_like_action(self, text: str) -> bool:
        """
        Check if text looks like an action/task command.

        Heuristic: Starts with a verb or imperative phrase.

        Args:
            text: Lowercase user input

        Returns:
            True if text appears to be an action command
        """
        # Common action verbs that suggest task creation
        action_starters = [
            "buy", "get", "pick up", "call", "email", "text", "message",
            "send", "write", "read", "review", "check", "fix", "update",
            "create", "make", "build", "clean", "organize", "prepare",
            "schedule", "book", "plan", "research", "find", "look up",
        ]

        for starter in action_starters:
            if text.startswith(starter) or text.startswith(f"i need to {starter}"):
                return True

        return False

    def route(self, intent: str, domain: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Route a request to the appropriate agent.

        Args:
            intent: The classified intent
            domain: The domain of the intent
            context: Request context including original text

        Returns:
            AgentResponse from the handling agent
        """
        # Get the agent for this domain
        agent = self.get_agent_for_domain(domain)

        if agent is None:
            if domain == "unknown":
                return AgentResponse.error(
                    "I'm not sure what you're asking for. Could you rephrase that? "
                    "I can help with tasks, calendar events, notes, and goals.",
                    data={"detected_domain": domain, "detected_intent": intent}
                )
            else:
                return AgentResponse.error(
                    f"The {domain} agent is not yet available. "
                    "This feature is coming soon!",
                    data={"detected_domain": domain, "detected_intent": intent}
                )

        # Check if agent can handle this intent
        if not agent.can_handle(intent, context):
            # Try to find a fallback intent for this domain
            fallback_intent = self._get_fallback_intent(agent, domain)
            if fallback_intent:
                intent = fallback_intent
            else:
                return AgentResponse.error(
                    f"I understood this is about {domain}, but I'm not sure "
                    f"what action to take. Could you be more specific?"
                )

        # Process the request
        self.logger.info("Routing to %s agent with intent: %s", domain, intent)
        response = agent.process(intent, context)

        # Handle handoffs
        response = self._handle_handoff(response, depth=0)

        return response

    def get_agent_for_domain(self, domain: str) -> Optional[BaseAgent]:
        """
        Get the agent responsible for a given domain.

        Args:
            domain: The domain name (task, calendar, note, goal)

        Returns:
            The agent instance or None if not available
        """
        return self.agents.get(domain)

    def get_agent_for_intent(self, intent: str) -> Optional[BaseAgent]:
        """
        Find an agent that can handle the given intent.

        Searches all registered agents to find one that supports the intent.

        Args:
            intent: The intent to handle

        Returns:
            The agent instance or None if no agent can handle it
        """
        for agent in self.agents.values():
            if agent is not None and agent.can_handle(intent, {}):
                return agent
        return None

    def _get_fallback_intent(self, agent: BaseAgent, domain: str) -> Optional[str]:
        """
        Get a fallback intent for an agent when the detected intent isn't supported.

        Args:
            agent: The agent to find fallback for
            domain: The domain of the agent

        Returns:
            A supported intent string or None
        """
        fallback = self.DEFAULT_INTENTS.get(domain)
        if fallback and agent.can_handle(fallback, {}):
            return fallback

        # Try the first supported intent
        supported = agent.get_supported_intents()
        if supported:
            return supported[0]

        return None

    def _handle_handoff(self, response: AgentResponse, depth: int) -> AgentResponse:
        """
        Handle agent-to-agent handoffs.

        When an agent returns a handoff response, routes the request
        to the target agent with the handoff context.

        Args:
            response: The response from the current agent
            depth: Current handoff depth (to prevent infinite loops)

        Returns:
            Final AgentResponse after all handoffs are complete
        """
        if not response.handoff_to:
            return response

        if depth >= self.max_handoff_depth:
            self.logger.warning("Maximum handoff depth reached (%d)", depth)
            return AgentResponse.error(
                "Processing loop detected. Please try rephrasing your request.",
                data={"last_response": response.to_dict()}
            )

        target_agent = self.agents.get(response.handoff_to)

        if target_agent is None:
            self.logger.warning("Handoff target not available: %s", response.handoff_to)
            # Return the original response message since we can't complete handoff
            return AgentResponse.ok(
                response.message,
                data=response.data,
                suggestions=[f"Note: {response.handoff_to} features coming soon"]
            )

        handoff_context = response.handoff_context or {}

        # Determine intent for handoff
        # The handing-off agent should specify the intent in the context
        intent = handoff_context.get("intent")
        if not intent:
            # Try to classify from the text if available
            if "text" in handoff_context:
                _, intent = self.classify_intent(handoff_context["text"])
            else:
                intent = self.DEFAULT_INTENTS.get(response.handoff_to, "unknown")

        self.logger.info("Handling handoff to %s with intent: %s",
                        response.handoff_to, intent)

        # Process with target agent
        new_response = target_agent.process(intent, handoff_context)

        # Recursively handle any further handoffs
        return self._handle_handoff(new_response, depth + 1)

    def register_agent(self, domain: str, agent: BaseAgent) -> None:
        """
        Register a new agent for a domain.

        Allows dynamic agent registration at runtime.

        Args:
            domain: The domain this agent handles
            agent: The agent instance
        """
        if domain in self.agents and self.agents[domain] is not None:
            self.logger.warning("Replacing existing agent for domain: %s", domain)
            self.agents[domain].cleanup()

        self.agents[domain] = agent
        agent.initialize()
        self.logger.info("Registered agent for domain: %s", domain)

    def unregister_agent(self, domain: str) -> None:
        """
        Unregister an agent for a domain.

        Args:
            domain: The domain to unregister
        """
        if domain in self.agents and self.agents[domain] is not None:
            self.agents[domain].cleanup()
            self.agents[domain] = None
            self.logger.info("Unregistered agent for domain: %s", domain)

    def get_available_domains(self) -> List[str]:
        """
        Get list of domains with available agents.

        Returns:
            List of domain names that have active agents
        """
        return [domain for domain, agent in self.agents.items() if agent is not None]

    def get_all_supported_intents(self) -> Dict[str, List[str]]:
        """
        Get all supported intents across all agents.

        Returns:
            Dictionary mapping domain names to list of supported intents
        """
        result = {}
        for domain, agent in self.agents.items():
            if agent is not None:
                result[domain] = agent.get_supported_intents()
        return result

    def cleanup(self) -> None:
        """
        Clean up all agents before shutdown.
        """
        for agent in self.agents.values():
            if agent is not None:
                agent.cleanup()
        self.logger.info("MasterAgent cleaned up")

    def update_context(self, **kwargs) -> None:
        """
        Update the shared conversation context.

        Args:
            **kwargs: Key-value pairs to update in context
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                self.context.session_data[key] = value

    def add_to_conversation_history(self, role: str, content: str) -> None:
        """
        Add a message to conversation history.

        Args:
            role: "user" or "assistant"
            content: The message content
        """
        self.context.conversation_history.append({
            "role": role,
            "content": content
        })

        # Keep history bounded (last 20 turns)
        if len(self.context.conversation_history) > 40:
            self.context.conversation_history = self.context.conversation_history[-40:]

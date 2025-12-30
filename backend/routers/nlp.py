"""
Natural Language Processing API endpoint.

Provides a unified endpoint for processing natural language input
through the MasterAgent, which routes to appropriate specialized agents.

This is the most flexible endpoint - it accepts any natural language
input and returns the appropriate response based on intent classification.
"""

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_master_agent
from backend.schemas import NLPRequest, NLPResponse
from src.agents import MasterAgent

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.post("/parse", response_model=NLPResponse)
async def parse_natural_language(
    request: NLPRequest,
    agent: MasterAgent = Depends(get_master_agent),
):
    """
    Parse and execute natural language commands.

    Examples:
    - "Add a task to buy groceries tomorrow"
    - "Schedule a meeting with John on Monday at 2pm"
    - "What's on my plate today?"
    - "Create a note about project architecture"
    - "How am I doing on my fitness goal?"

    The MasterAgent classifies the intent and routes to the appropriate
    specialized agent (TaskAgent, CalendarAgent, NoteAgent, GoalAgent).

    Returns the agent's response with parsed entities and any data created.
    """
    try:
        # Build context from request
        context = request.context or {}

        # Process through MasterAgent
        response = agent.process(request.query, context)

        # Extract any parsed information from the response
        parsed = None
        if response.data:
            # Extract commonly parsed fields for frontend display
            parsed = {
                "intent": response.data.get("intent"),
                "domain": response.data.get("domain"),
                "entities": response.data.get("entities", {}),
            }

        return NLPResponse(
            success=response.success,
            message=response.message,
            data=response.data,
            parsed=parsed,
            suggestions=response.suggestions,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process request: {str(e)}"
        )


@router.post("/ask", response_model=NLPResponse)
async def ask_assistant(
    request: NLPRequest,
    agent: MasterAgent = Depends(get_master_agent),
):
    """
    General-purpose assistant endpoint.

    Alias for /parse that emphasizes conversational interaction.
    Use this for chat-style interfaces.
    """
    return await parse_natural_language(request, agent)

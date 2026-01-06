#!/usr/bin/env python3
"""
Apple Reminders MCP Server - Life Planner integration.

T0: Basic create/list/complete/delete reminders
T1: Multi-list support, recurring reminders, priority (future)
T2: Smart scheduling, analytics, natural language parsing (future)

Usage:
    python mcp_server/server.py
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from src.reminders_interface import RemindersInterface
from src.reminder_manager import ReminderManager, validate_positive_int, validate_non_empty_string, validate_priority, validate_tags, validate_recurrence

# Project root directory (for resolving relative paths)
PROJECT_ROOT = Path(__file__).parent.parent

# Configure logging with absolute path
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)  # Ensure log directory exists

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
CONFIG_PATH = PROJECT_ROOT / "config" / "mcp_server.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

# Validation constants
MAX_REMINDERS_LIMIT = 500
MIN_LIMIT = 1


def resolve_path(path_str: str) -> Path:
    """
    Resolve config path relative to PROJECT_ROOT or expand ~.

    MCP servers run from arbitrary working directories, so all paths
    must be resolved relative to the project root or as absolute paths.

    Args:
        path_str: Path string from config (may be relative or use ~)

    Returns:
        Resolved absolute Path
    """
    path = Path(path_str).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


# Initialize server
app = Server(CONFIG["server_name"])

# Initialize components with resolved paths
reminders_interface = RemindersInterface(
    default_list=CONFIG["reminders"]["default_list"]
)
reminder_manager = ReminderManager(
    interface=reminders_interface,
    planner_db_path=str(resolve_path(CONFIG["paths"]["life_planner_db"])),
    auto_logging=CONFIG["features"]["auto_interaction_logging"]
)

logger.info(f"MCP server initialized: {CONFIG['server_name']} v{CONFIG['version']}")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available MCP tools."""
    return [
        types.Tool(
            name="create_reminder",
            description=(
                "Create a new reminder with optional due date, list, priority, recurrence, and tags. "
                "Auto-logs to life planner database if enabled."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Reminder title (required)"
                    },
                    "list_name": {
                        "type": "string",
                        "description": "Target list (default: configured default list)"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Optional due date (ISO 8601 format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes/description"
                    },
                    "priority": {
                        "type": ["number", "string"],
                        "description": "Optional priority: 0-9 or none/low/medium/high"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for organization (e.g., ['work', 'urgent'])"
                    },
                    "recurrence": {
                        "type": "object",
                        "properties": {
                            "frequency": {
                                "type": "string",
                                "enum": ["daily", "weekly", "monthly", "yearly"],
                                "description": "Recurrence frequency"
                            },
                            "interval": {
                                "type": "number",
                                "description": "Recurrence interval (e.g., 2 for every 2 weeks)",
                                "default": 1
                            }
                        },
                        "required": ["frequency"],
                        "description": "Optional recurrence pattern (e.g., {'frequency': 'daily', 'interval': 1})"
                    }
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="list_reminder_lists",
            description="Get all available reminder lists (e.g., Reminders, Work, Personal)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="list_reminders",
            description="List reminders from the configured default list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_name": {
                        "type": "string",
                        "description": "Optional: filter by specific list (default: configured default)"
                    },
                    "completed": {
                        "type": "boolean",
                        "description": "Show completed reminders (default: false)",
                        "default": False
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum reminders to return (default: 50, max: 500)",
                        "default": 50
                    },
                    "tag_filter": {
                        "type": "string",
                        "description": "Optional: filter by tag (e.g., 'work' matches #work)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="complete_reminder",
            description="Mark a reminder as complete",
            inputSchema={
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "string",
                        "description": "The reminder ID (from list_reminders)"
                    }
                },
                "required": ["reminder_id"]
            }
        ),
        types.Tool(
            name="delete_reminder",
            description="Delete a reminder permanently",
            inputSchema={
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "string",
                        "description": "The reminder ID (from list_reminders)"
                    }
                },
                "required": ["reminder_id"]
            }
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle MCP tool invocation."""

    try:
        if name == "create_reminder":
            # Validate title
            title, error = validate_non_empty_string(
                arguments.get("title"), "title"
            )
            if error:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": error})
                )]

            # Validate priority if provided
            priority = arguments.get("priority")
            validated_priority = None
            if priority is not None:
                validated_priority, error = validate_priority(priority, "priority")
                if error:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"success": False, "error": error})
                    )]

            # Validate tags if provided
            tags = arguments.get("tags")
            validated_tags = None
            if tags is not None:
                validated_tags, error = validate_tags(tags, "tags")
                if error:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"success": False, "error": error})
                    )]

            # Validate recurrence if provided
            recurrence = arguments.get("recurrence")
            validated_recurrence = None
            if recurrence is not None:
                validated_recurrence, error = validate_recurrence(recurrence, "recurrence")
                if error:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"success": False, "error": error})
                    )]

            # Create reminder with validation
            result = reminder_manager.create_reminder(
                title=title,
                list_name=arguments.get("list_name"),
                due_date=arguments.get("due_date"),
                notes=arguments.get("notes"),
                priority=validated_priority,
                tags=validated_tags,
                recurrence=validated_recurrence
            )

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "list_reminders":
            # Validate limit
            limit = arguments.get("limit", 50)
            limit, error = validate_positive_int(
                limit, "limit",
                min_val=MIN_LIMIT,
                max_val=MAX_REMINDERS_LIMIT
            )
            if error:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": error})
                )]

            # List reminders
            reminders = reminders_interface.list_reminders(
                list_name=arguments.get("list_name"),
                completed=arguments.get("completed", False),
                limit=limit,
                tag_filter=arguments.get("tag_filter")
            )

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "reminders": reminders,
                    "count": len(reminders)
                }, indent=2)
            )]

        elif name == "complete_reminder":
            # Validate reminder_id
            reminder_id, error = validate_non_empty_string(
                arguments.get("reminder_id"), "reminder_id"
            )
            if error:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": error})
                )]

            # Complete reminder
            result = reminder_manager.complete_reminder(reminder_id)

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "list_reminder_lists":
            # List all available reminder lists
            lists = reminders_interface.list_reminder_lists()

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "lists": lists,
                    "count": len(lists)
                }, indent=2)
            )]

        elif name == "delete_reminder":
            # Validate reminder_id
            reminder_id, error = validate_non_empty_string(
                arguments.get("reminder_id"), "reminder_id"
            )
            if error:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": error})
                )]

            # Delete reminder
            result = reminder_manager.delete_reminder(reminder_id)

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        else:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except Exception as e:
        logger.error(f"Error handling tool {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]


async def main():
    """Run MCP server."""
    logger.info("Starting MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

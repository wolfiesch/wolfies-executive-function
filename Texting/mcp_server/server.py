#!/usr/bin/env python3
"""
iMessage MCP Server - Personalized messaging with Life Planner integration.

Sprint 1: Basic send/receive messages via MCP
Sprint 2: Contact sync and fuzzy matching
Sprint 3: Style learning and personalization
Sprint 4: Context integration from Life Planner

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

from src.messages_interface import MessagesInterface
from src.contacts_manager import ContactsManager

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


def resolve_path(path_str: str) -> str:
    """Resolve a config path relative to PROJECT_ROOT or expand ~."""
    path = Path(path_str)
    if path_str.startswith("~"):
        return str(path.expanduser())
    elif path.is_absolute():
        return str(path)
    else:
        return str(PROJECT_ROOT / path)


# Initialize server
app = Server(CONFIG["server_name"])

# Initialize components with resolved paths
messages = MessagesInterface(resolve_path(CONFIG["paths"]["messages_db"]))
contacts = ContactsManager(resolve_path(CONFIG["paths"]["contacts_config"]))


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available MCP tools.

    Sprint 1 tools:
    - send_message: Send iMessage to a contact
    - get_recent_messages: Retrieve recent message history
    - list_contacts: Show all configured contacts
    """
    return [
        types.Tool(
            name="send_message",
            description=(
                "Send an iMessage to a contact using their name. "
                "The contact must be configured in contacts.json (Sprint 1). "
                "Auto-logs interaction to life planner database if enabled."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_name": {
                        "type": "string",
                        "description": "Name of the contact (exact or partial match)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message text to send"
                    }
                },
                "required": ["contact_name", "message"]
            }
        ),
        types.Tool(
            name="get_recent_messages",
            description=(
                "Retrieve recent message history with a contact. "
                "Requires Full Disk Access permission for Messages database."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_name": {
                        "type": "string",
                        "description": "Name of the contact"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of recent messages to retrieve (default: 20)",
                        "default": 20
                    }
                },
                "required": ["contact_name"]
            }
        ),
        types.Tool(
            name="list_contacts",
            description="List all configured contacts with their phone numbers",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handle MCP tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent responses
    """
    logger.info(f"Tool called: {name} with args: {arguments}")

    try:
        if name == "send_message":
            return await handle_send_message(arguments)
        elif name == "get_recent_messages":
            return await handle_get_recent_messages(arguments)
        elif name == "list_contacts":
            return await handle_list_contacts(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


async def handle_send_message(arguments: dict) -> list[types.TextContent]:
    """
    Handle send_message tool call.

    Args:
        arguments: {"contact_name": str, "message": str}

    Returns:
        Success or error message
    """
    contact_name = arguments["contact_name"]
    message = arguments["message"]

    # Look up contact
    contact = contacts.get_contact_by_name(contact_name)
    if not contact:
        return [
            types.TextContent(
                type="text",
                text=(
                    f"Contact '{contact_name}' not found. "
                    f"Please add to config/contacts.json or check spelling. "
                    f"Available contacts: {', '.join(c.name for c in contacts.list_contacts())}"
                )
            )
        ]

    # Send message
    result = messages.send_message(contact.phone, message)

    if result["success"]:
        response = (
            f"✓ Message sent to {contact.name} ({contact.phone})\n\n"
            f"Message: {message}"
        )
        logger.info(f"Message sent successfully to {contact.name}")

        # TODO Sprint 2: Log interaction to Life Planner database
    else:
        response = (
            f"✗ Failed to send message to {contact.name}\n\n"
            f"Error: {result['error']}\n\n"
            f"Troubleshooting:\n"
            f"- Ensure Messages.app is running\n"
            f"- Check AppleScript permissions in System Settings\n"
            f"- Verify phone number format: {contact.phone}"
        )
        logger.error(f"Failed to send message: {result['error']}")

    return [types.TextContent(type="text", text=response)]


async def handle_get_recent_messages(arguments: dict) -> list[types.TextContent]:
    """
    Handle get_recent_messages tool call.

    Args:
        arguments: {"contact_name": str, "limit": Optional[int]}

    Returns:
        Recent message history or error
    """
    contact_name = arguments["contact_name"]
    limit = arguments.get("limit", 20)

    # Look up contact
    contact = contacts.get_contact_by_name(contact_name)
    if not contact:
        return [
            types.TextContent(
                type="text",
                text=f"Contact '{contact_name}' not found"
            )
        ]

    # Get messages
    message_list = messages.get_recent_messages(contact.phone, limit)

    if not message_list:
        return [
            types.TextContent(
                type="text",
                text=(
                    f"No messages found for {contact.name}.\n\n"
                    f"Note: Requires Full Disk Access permission.\n"
                    f"Grant in: System Settings → Privacy & Security → Full Disk Access"
                )
            )
        ]

    # Format response
    response_lines = [
        f"Recent messages with {contact.name} ({contact.phone}):",
        f"(Showing {len(message_list)} most recent)",
        ""
    ]

    for msg in message_list:
        direction = "You" if msg["is_from_me"] else contact.name
        date = msg["date"][:19] if msg["date"] else "Unknown date"
        text = msg["text"][:100] + "..." if len(msg["text"]) > 100 else msg["text"]

        response_lines.append(f"[{date}] {direction}: {text}")

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def handle_list_contacts(arguments: dict) -> list[types.TextContent]:
    """
    Handle list_contacts tool call.

    Returns:
        List of all configured contacts
    """
    contact_list = contacts.list_contacts()

    if not contact_list:
        return [
            types.TextContent(
                type="text",
                text=(
                    "No contacts configured.\n\n"
                    "Add contacts to: config/contacts.json\n"
                    "Sprint 2 will add auto-sync from macOS Contacts."
                )
            )
        ]

    response_lines = [
        f"Configured Contacts ({len(contact_list)}):",
        ""
    ]

    for contact in contact_list:
        response_lines.append(
            f"• {contact.name} - {contact.phone} ({contact.relationship_type})"
        )
        if contact.notes:
            response_lines.append(f"  Note: {contact.notes}")

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def main():
    """Run the MCP server."""
    logger.info("Starting iMessage MCP Server...")
    logger.info(f"Server name: {CONFIG['server_name']}")
    logger.info(f"Version: {CONFIG['version']}")

    # Check permissions
    permissions = messages.check_permissions()
    if not permissions["messages_db_accessible"]:
        logger.warning("Messages database not accessible - get_recent_messages will not work")
        logger.warning("Grant Full Disk Access in System Settings")

    # Log loaded contacts
    logger.info(f"Loaded {len(contacts.list_contacts())} contacts")

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

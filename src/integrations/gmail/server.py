#!/usr/bin/env python3
"""
Gmail MCP Server - Email integration for Life Planner.

Provides MCP tools for:
- Listing recent emails with filters
- Getting full email content
- Searching emails
- Sending emails
- Getting unread count

Usage:
    python src/integrations/gmail/server.py

MCP Registration:
    claude mcp add -t stdio gmail -- python3 /Users/wolfgangschoenberger/LIFE-PLANNER/src/integrations/gmail/server.py
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from src.integrations.gmail.gmail_client import GmailClient

# Project root directory (for resolving relative paths)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Configure logging with absolute path
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)  # Ensure log directory exists

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'gmail.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"
MAX_EMAIL_BODY_LENGTH = 5000  # Truncate very long emails

# Initialize Gmail client
try:
    gmail_client = GmailClient(str(CREDENTIALS_DIR))
    logger.info("Gmail client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gmail client: {e}")
    gmail_client = None

# Initialize MCP server
app = Server("gmail")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available Gmail MCP tools.

    Tools:
    - list_emails: List recent emails with filters
    - get_email: Get full email content by ID
    - search_emails: Search emails by query
    - send_email: Send an email
    - get_unread_count: Get count of unread emails
    """
    return [
        types.Tool(
            name="list_emails",
            description=(
                "List recent emails with optional filters. "
                "Can filter by unread status, label, sender, and date range."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of emails to return (default: 10)",
                        "default": 10
                    },
                    "unread_only": {
                        "type": "boolean",
                        "description": "Only return unread emails (default: false)",
                        "default": False
                    },
                    "label": {
                        "type": "string",
                        "description": "Filter by Gmail label (e.g., 'INBOX', 'SENT', 'SPAM')"
                    },
                    "sender": {
                        "type": "string",
                        "description": "Filter by sender email address"
                    },
                    "after_date": {
                        "type": "string",
                        "description": "Filter emails after date (format: YYYY/MM/DD)"
                    },
                    "before_date": {
                        "type": "string",
                        "description": "Filter emails before date (format: YYYY/MM/DD)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_email",
            description=(
                "Get full email content by message ID. "
                "Returns subject, sender, recipient, date, body, and metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    }
                },
                "required": ["message_id"]
            }
        ),
        types.Tool(
            name="search_emails",
            description=(
                "Search emails using Gmail search syntax. "
                "Examples: 'subject:meeting', 'from:john@example.com', 'has:attachment'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum results to return (default: 50)",
                        "default": 50
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="send_email",
            description=(
                "Send an email to a recipient. "
                "Sends plain text email from authenticated Gmail account."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (plain text)"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        ),
        types.Tool(
            name="get_unread_count",
            description="Get the count of unread emails in the inbox.",
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

    # Check if Gmail client initialized
    if not gmail_client:
        return [
            types.TextContent(
                type="text",
                text=(
                    "Error: Gmail client not initialized.\n\n"
                    "Please ensure:\n"
                    "1. credentials.json exists in config/google_credentials/\n"
                    "2. OAuth flow completed successfully\n\n"
                    "See logs/gmail.log for details."
                )
            )
        ]

    try:
        if name == "list_emails":
            return await handle_list_emails(arguments)
        elif name == "get_email":
            return await handle_get_email(arguments)
        elif name == "search_emails":
            return await handle_search_emails(arguments)
        elif name == "send_email":
            return await handle_send_email(arguments)
        elif name == "get_unread_count":
            return await handle_get_unread_count(arguments)
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


async def handle_list_emails(arguments: dict) -> list[types.TextContent]:
    """
    Handle list_emails tool call.

    Args:
        arguments: {"max_results": int, "unread_only": bool, "label": str, ...}

    Returns:
        Formatted list of emails
    """
    max_results = arguments.get("max_results", 10)
    unread_only = arguments.get("unread_only", False)
    label = arguments.get("label")
    sender = arguments.get("sender")
    after_date = arguments.get("after_date")
    before_date = arguments.get("before_date")

    emails = gmail_client.list_emails(
        max_results=max_results,
        unread_only=unread_only,
        label=label,
        sender=sender,
        after_date=after_date,
        before_date=before_date
    )

    if not emails:
        filters_applied = []
        if unread_only:
            filters_applied.append("unread")
        if label:
            filters_applied.append(f"label:{label}")
        if sender:
            filters_applied.append(f"from:{sender}")

        filter_text = f" (filters: {', '.join(filters_applied)})" if filters_applied else ""

        return [
            types.TextContent(
                type="text",
                text=f"No emails found{filter_text}"
            )
        ]

    # Format response
    response_lines = [
        f"Recent Emails ({len(emails)} results):",
        ""
    ]

    for email in emails:
        unread_marker = "[UNREAD] " if email['is_unread'] else ""
        subject = email['subject'][:60] + "..." if len(email['subject']) > 60 else email['subject']
        sender_name = email['from'][:40] + "..." if len(email['from']) > 40 else email['from']
        snippet = email['snippet'][:100] + "..." if len(email['snippet']) > 100 else email['snippet']

        response_lines.append(f"{unread_marker}ID: {email['id']}")
        response_lines.append(f"From: {sender_name}")
        response_lines.append(f"Subject: {subject}")
        response_lines.append(f"Date: {email['date']}")
        response_lines.append(f"Preview: {snippet}")
        response_lines.append("")  # Blank line between emails

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def handle_get_email(arguments: dict) -> list[types.TextContent]:
    """
    Handle get_email tool call.

    Args:
        arguments: {"message_id": str}

    Returns:
        Full email details
    """
    message_id = arguments["message_id"]

    email = gmail_client.get_email(message_id)

    if not email:
        return [
            types.TextContent(
                type="text",
                text=f"Email not found: {message_id}"
            )
        ]

    # Truncate very long email bodies
    body = email['body']
    if len(body) > MAX_EMAIL_BODY_LENGTH:
        body = body[:MAX_EMAIL_BODY_LENGTH] + f"\n\n[... truncated {len(body) - MAX_EMAIL_BODY_LENGTH} characters ...]"

    # Format response
    response = f"""Email Details:

ID: {email['id']}
Thread ID: {email['thread_id']}
From: {email['from']}
To: {email['to']}
Date: {email['date']}
Subject: {email['subject']}
Status: {"UNREAD" if email['is_unread'] else "READ"}
Labels: {', '.join(email['labels'])}

Body:
{body}
"""

    return [
        types.TextContent(
            type="text",
            text=response
        )
    ]


async def handle_search_emails(arguments: dict) -> list[types.TextContent]:
    """
    Handle search_emails tool call.

    Args:
        arguments: {"query": str, "max_results": int}

    Returns:
        Search results
    """
    query = arguments["query"]
    max_results = arguments.get("max_results", 50)

    emails = gmail_client.search_emails(query, max_results)

    if not emails:
        return [
            types.TextContent(
                type="text",
                text=f"No emails found matching query: '{query}'"
            )
        ]

    # Format response
    response_lines = [
        f"Search Results for '{query}' ({len(emails)} results):",
        ""
    ]

    for email in emails:
        subject = email['subject'][:60] + "..." if len(email['subject']) > 60 else email['subject']
        sender_name = email['from'][:40] + "..." if len(email['from']) > 40 else email['from']
        snippet = email['snippet'][:100] + "..." if len(email['snippet']) > 100 else email['snippet']

        response_lines.append(f"ID: {email['id']}")
        response_lines.append(f"From: {sender_name}")
        response_lines.append(f"Subject: {subject}")
        response_lines.append(f"Date: {email['date']}")
        response_lines.append(f"Preview: {snippet}")
        response_lines.append("")  # Blank line

    return [
        types.TextContent(
            type="text",
            text="\n".join(response_lines)
        )
    ]


async def handle_send_email(arguments: dict) -> list[types.TextContent]:
    """
    Handle send_email tool call.

    Args:
        arguments: {"to": str, "subject": str, "body": str}

    Returns:
        Success or error message
    """
    to = arguments["to"]
    subject = arguments["subject"]
    body = arguments["body"]

    result = gmail_client.send_email(to, subject, body)

    if result['success']:
        response = f"""Email sent successfully!

To: {to}
Subject: {subject}
Message ID: {result['message_id']}
Thread ID: {result['thread_id']}

Preview:
{body[:200] + '...' if len(body) > 200 else body}
"""
    else:
        response = f"""Failed to send email to {to}

Error: {result['error']}

Troubleshooting:
- Ensure Gmail API is enabled in Google Cloud Console
- Verify OAuth credentials are valid
- Check recipient email address is correct
"""

    return [
        types.TextContent(
            type="text",
            text=response
        )
    ]


async def handle_get_unread_count(arguments: dict) -> list[types.TextContent]:
    """
    Handle get_unread_count tool call.

    Returns:
        Count of unread emails
    """
    count = gmail_client.get_unread_count()

    response = f"Unread emails: {count}"

    return [
        types.TextContent(
            type="text",
            text=response
        )
    ]


async def main():
    """Run the MCP server."""
    logger.info("Starting Gmail MCP Server...")
    logger.info(f"Credentials directory: {CREDENTIALS_DIR}")

    if gmail_client:
        logger.info("Gmail API ready")
    else:
        logger.warning("Gmail client not initialized - tools will not work")

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

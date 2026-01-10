#!/usr/bin/env python3
"""
Gmail Gateway CLI - Fast, MCP-free email access.

19x faster than MCP servers by avoiding protocol overhead.
Uses BatchHttpRequest for efficient multi-email fetches.
Supports --use-daemon for warm performance via pre-warmed daemon.

Commands:
  unread          Get unread email count
  list [N]        List recent N emails (default: 10)
  search QUERY    Search emails by Gmail query
  get ID          Get full email by ID
  send TO SUBJ    Send email (body from stdin or --body)

Usage:
  python3 gmail_cli.py unread --json
  python3 gmail_cli.py list 10 --json --compact
  python3 gmail_cli.py search "from:boss" --json
  python3 gmail_cli.py get MESSAGE_ID --json
  python3 gmail_cli.py send "user@example.com" "Subject" --body "Hello"

  # With daemon (faster if daemon is running):
  python3 gmail_cli.py list 10 --json --use-daemon

CHANGELOG (recent first, max 5 entries):
01/08/2026 - Made GmailClient import lazy for daemon mode (~2s faster) (Claude)
01/08/2026 - Added --use-daemon flag for warm performance (Claude)
01/08/2026 - Initial CLI gateway implementation (Claude)
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Lazy import GmailClient (2+ seconds to import due to google libraries)
# Only imported when NOT using daemon mode
if TYPE_CHECKING:
    from src.integrations.gmail.gmail_client import GmailClient

# Default credentials directory
CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"

# Lazy-loaded clients (avoid overhead when using daemon)
_daemon_client = None


def get_daemon_client():
    """Lazy-load daemon client."""
    global _daemon_client
    if _daemon_client is None:
        from src.integrations.google_daemon.client import GoogleDaemonClient, is_daemon_running
        if not is_daemon_running():
            raise RuntimeError("Google daemon is not running. Start it with: python3 src/integrations/google_daemon/server.py start")
        _daemon_client = GoogleDaemonClient()
    return _daemon_client


# =============================================================================
# OUTPUT UTILITIES (token-optimized JSON output)
# =============================================================================

def emit_json(payload: Any, compact: bool = False) -> None:
    """Emit JSON output, optionally compact for LLM consumption."""
    if compact:
        print(json.dumps(payload, separators=(",", ":"), default=str))
    else:
        print(json.dumps(payload, indent=2, default=str))


def filter_fields(data: Dict[str, Any], fields: Optional[List[str]]) -> Dict[str, Any]:
    """Filter dictionary to only include specified fields."""
    if not fields:
        return data
    return {k: v for k, v in data.items() if k in fields}


def truncate_text(data: Dict[str, Any], max_chars: Optional[int]) -> Dict[str, Any]:
    """Truncate long text fields to save tokens."""
    if not max_chars:
        return data
    result = data.copy()
    for key in ['body', 'snippet']:
        if key in result and isinstance(result[key], str) and len(result[key]) > max_chars:
            result[key] = result[key][:max_chars] + "..."
    return result


def process_emails(
    emails: List[Dict[str, Any]],
    fields: Optional[List[str]] = None,
    max_text_chars: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Apply field filtering and text truncation to email list."""
    result = []
    for email in emails:
        processed = email
        if fields:
            processed = filter_fields(processed, fields)
        if max_text_chars:
            processed = truncate_text(processed, max_text_chars)
        result.append(processed)
    return result


# =============================================================================
# CLI COMMANDS
# =============================================================================

def cmd_unread(args: argparse.Namespace, client: GmailClient) -> int:
    """Get unread email count."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            count = daemon.gmail_unread_count()
        else:
            count = client.get_unread_count()

        if args.json:
            emit_json({"unread_count": count}, compact=args.compact)
        else:
            print(f"Unread emails: {count}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace, client: GmailClient) -> int:
    """List recent emails."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.gmail_list(
                count=args.count,
                unread_only=args.unread_only,
                label=args.label,
                sender=args.sender,
                after=args.after,
                before=args.before,
            )
            emails = result.get("emails", [])
        else:
            emails = client.list_emails(
                max_results=args.count,
                unread_only=args.unread_only,
                label=args.label,
                sender=args.sender,
                after_date=args.after,
                before_date=args.before
            )

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None

        # Apply minimal preset
        if args.minimal:
            fields = fields or ['id', 'subject', 'from', 'date', 'is_unread', 'snippet']
            args.max_text_chars = args.max_text_chars or 150

        # Process emails for output
        processed = process_emails(emails, fields, args.max_text_chars)

        if args.json:
            emit_json({"emails": processed, "count": len(processed)}, compact=args.compact)
        else:
            for email in processed:
                status = "[UNREAD]" if email.get('is_unread') else ""
                print(f"{status} {email.get('from', 'Unknown')}: {email.get('subject', 'No Subject')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_search(args: argparse.Namespace, client: GmailClient) -> int:
    """Search emails by query."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.gmail_search(query=args.query, max_results=args.max_results)
            emails = result.get("emails", [])
        else:
            emails = client.search_emails(
                query=args.query,
                max_results=args.max_results
            )

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None

        # Apply minimal preset
        if args.minimal:
            fields = fields or ['id', 'subject', 'from', 'date', 'is_unread', 'snippet']
            args.max_text_chars = args.max_text_chars or 150

        # Process emails for output
        processed = process_emails(emails, fields, args.max_text_chars)

        if args.json:
            emit_json({
                "query": args.query,
                "emails": processed,
                "count": len(processed)
            }, compact=args.compact)
        else:
            print(f"Found {len(processed)} emails for query: {args.query}")
            for email in processed:
                print(f"  {email.get('from', 'Unknown')}: {email.get('subject', 'No Subject')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_get(args: argparse.Namespace, client: GmailClient) -> int:
    """Get full email by ID."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            email = daemon.gmail_get(args.message_id)
        else:
            email = client.get_email(args.message_id)

        if not email:
            if args.json:
                emit_json({"error": f"Email not found: {args.message_id}"}, compact=args.compact)
            else:
                print(f"Email not found: {args.message_id}", file=sys.stderr)
            return 1

        # Parse fields if provided
        fields = args.fields.split(',') if args.fields else None

        # Process email for output
        if fields:
            email = filter_fields(email, fields)
        if args.max_text_chars:
            email = truncate_text(email, args.max_text_chars)

        if args.json:
            emit_json(email, compact=args.compact)
        else:
            print(f"From: {email.get('from', 'Unknown')}")
            print(f"To: {email.get('to', 'Unknown')}")
            print(f"Subject: {email.get('subject', 'No Subject')}")
            print(f"Date: {email.get('date', 'Unknown')}")
            print(f"\n{email.get('body', '')}")
        return 0
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_send(args: argparse.Namespace, client: GmailClient) -> int:
    """Send an email."""
    try:
        # Get body from argument or stdin
        body = args.body
        if not body and not sys.stdin.isatty():
            body = sys.stdin.read().strip()

        if not body:
            if args.json:
                emit_json({"error": "Email body required (--body or stdin)"}, compact=args.compact)
            else:
                print("Error: Email body required (use --body or pipe to stdin)", file=sys.stderr)
            return 1

        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.gmail_send(to=args.to, subject=args.subject, body=body)
        else:
            result = client.send_email(
                to=args.to,
                subject=args.subject,
                body=body
            )

        if args.json:
            emit_json(result, compact=args.compact)
        else:
            if result.get('success'):
                print(f"Email sent successfully! Message ID: {result.get('message_id')}")
            else:
                print(f"Failed to send email: {result.get('error')}", file=sys.stderr)
                return 1
        return 0 if result.get('success') else 1
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_mark_read(args: argparse.Namespace, client: GmailClient) -> int:
    """Mark email as read."""
    try:
        # Use daemon if requested
        if getattr(args, 'use_daemon', False):
            daemon = get_daemon_client()
            result = daemon.gmail_mark_read(args.message_id)
            success = result.get('success', False)
        else:
            success = client.mark_as_read(args.message_id)

        if args.json:
            emit_json({"success": success, "message_id": args.message_id}, compact=args.compact)
        else:
            if success:
                print(f"Marked {args.message_id} as read")
            else:
                print(f"Failed to mark {args.message_id} as read", file=sys.stderr)
                return 1
        return 0 if success else 1
    except Exception as e:
        if args.json:
            emit_json({"error": str(e)}, compact=args.compact)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


# =============================================================================
# OUTPUT ARGUMENTS (shared across commands)
# =============================================================================

def add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add LLM-friendly output controls for JSON output."""
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (required for skill integration)."
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Minify JSON output (reduces token cost)."
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="LLM-minimal preset: compact + essential fields + text truncation."
    )
    parser.add_argument(
        "--fields",
        help="Comma-separated list of JSON fields to include."
    )
    parser.add_argument(
        "--max-text-chars",
        dest="max_text_chars",
        type=int,
        default=None,
        help="Truncate body/snippet fields to N characters."
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gmail Gateway CLI - Fast, MCP-free email access.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s unread --json                    # Get unread count
  %(prog)s list 10 --json --compact         # List 10 emails, compact output
  %(prog)s list 5 --minimal                 # List 5 emails, LLM-optimized
  %(prog)s search "from:boss" --json        # Search emails
  %(prog)s get MESSAGE_ID --json            # Get full email
  %(prog)s send "user@example.com" "Hi" --body "Hello!"  # Send email
"""
    )

    parser.add_argument(
        "--credentials-dir",
        type=str,
        default=str(CREDENTIALS_DIR),
        help=f"Path to credentials directory (default: {CREDENTIALS_DIR})"
    )
    parser.add_argument(
        "--use-daemon",
        action="store_true",
        help="Use pre-warmed Google daemon for faster responses"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # unread command
    p_unread = subparsers.add_parser("unread", help="Get unread email count")
    add_output_args(p_unread)

    # list command
    p_list = subparsers.add_parser("list", help="List recent emails")
    p_list.add_argument("count", type=int, nargs="?", default=10, help="Number of emails (default: 10)")
    p_list.add_argument("--unread-only", action="store_true", help="Only show unread emails")
    p_list.add_argument("--label", help="Filter by Gmail label (e.g., INBOX, SENT)")
    p_list.add_argument("--sender", help="Filter by sender email")
    p_list.add_argument("--after", help="Filter emails after date (YYYY/MM/DD)")
    p_list.add_argument("--before", help="Filter emails before date (YYYY/MM/DD)")
    add_output_args(p_list)

    # search command
    p_search = subparsers.add_parser("search", help="Search emails by query")
    p_search.add_argument("query", help="Gmail search query (e.g., 'from:boss subject:meeting')")
    p_search.add_argument("--max-results", type=int, default=10, help="Max results (default: 10)")
    add_output_args(p_search)

    # get command
    p_get = subparsers.add_parser("get", help="Get full email by ID")
    p_get.add_argument("message_id", help="Gmail message ID")
    add_output_args(p_get)

    # send command
    p_send = subparsers.add_parser("send", help="Send an email")
    p_send.add_argument("to", help="Recipient email address")
    p_send.add_argument("subject", help="Email subject")
    p_send.add_argument("--body", help="Email body (or pipe to stdin)")
    add_output_args(p_send)

    # mark-read command
    p_mark = subparsers.add_parser("mark-read", help="Mark email as read")
    p_mark.add_argument("message_id", help="Gmail message ID")
    add_output_args(p_mark)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize client (skip if using daemon)
    client = None
    if not args.use_daemon:
        try:
            # Lazy import to avoid 2s+ overhead when using daemon mode
            from src.integrations.gmail.gmail_client import GmailClient
            client = GmailClient(args.credentials_dir)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("\nSetup instructions:", file=sys.stderr)
            print("1. Go to https://console.cloud.google.com/apis/credentials", file=sys.stderr)
            print("2. Create OAuth 2.0 Client ID (Desktop app)", file=sys.stderr)
            print(f"3. Save as {CREDENTIALS_DIR}/credentials.json", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error initializing Gmail client: {e}", file=sys.stderr)
            return 1

    # Dispatch to command handler
    commands = {
        "unread": cmd_unread,
        "list": cmd_list,
        "search": cmd_search,
        "get": cmd_get,
        "send": cmd_send,
        "mark-read": cmd_mark_read,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args, client)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

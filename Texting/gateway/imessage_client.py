#!/usr/bin/env python3
"""
iMessage Gateway Client - Standalone CLI for iMessage operations.

No MCP server required. Queries Messages.db directly and uses
the imessage-mcp library for contact resolution and message parsing.

This is the primary interface for iMessage operations, offering 19x faster
execution than the deprecated MCP server approach.

Usage:
    python3 gateway/imessage_client.py find "Angus" --query "SF"
    python3 gateway/imessage_client.py messages "John" --limit 20
    python3 gateway/imessage_client.py recent --limit 10
    python3 gateway/imessage_client.py unread
    python3 gateway/imessage_client.py send "John" "Running late!"
    python3 gateway/imessage_client.py send-by-phone +14155551234 "Hi"
    python3 gateway/imessage_client.py contacts
    python3 gateway/imessage_client.py analytics "Sarah" --days 30
    python3 gateway/imessage_client.py search "dinner plans"    # Semantic search (RAG)
    python3 gateway/imessage_client.py index --source=imessage  # Index for RAG
"""

import sys
import argparse
import json
import atexit
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from src.messages_interface import MessagesInterface
    from src.contacts_manager import ContactsManager
except ImportError as e:
    print(f"Error: Could not import modules: {e}")
    print(f"Make sure you're running from the imessage-mcp repository root")
    print(f"Expected path: {REPO_ROOT}")
    sys.exit(1)

# Default config path (relative to repo root)
CONTACTS_CONFIG = REPO_ROOT / "config" / "contacts.json"

# Valid RAG sources (single source of truth)
VALID_RAG_SOURCES = ['imessage', 'superwhisper', 'notes', 'local', 'gmail', 'slack', 'calendar']


def get_interfaces():
    """Initialize MessagesInterface and ContactsManager."""
    mi = MessagesInterface()
    cm = ContactsManager(str(CONTACTS_CONFIG))

    # Register cleanup to close database connections on exit
    # This prevents subprocess hanging due to unclosed SQLite connections
    def cleanup():
        try:
            if hasattr(cm, 'close'):
                cm.close()
        except Exception:
            pass  # Ignore cleanup errors

    atexit.register(cleanup)
    return mi, cm


def resolve_contact(cm: ContactsManager, name: str):
    """Resolve contact name to Contact object using fuzzy matching."""
    contact = cm.get_contact_by_name(name)
    # get_contact_by_name already does partial matching
    if contact and contact.name.lower() != name.lower():
        print(f"Matched '{name}' to '{contact.name}'", file=sys.stderr)
    return contact


def handle_contact_not_found(name: str, cm: ContactsManager) -> int:
    """Handle contact not found with helpful suggestions."""
    print(f"Contact '{name}' not found.", file=sys.stderr)

    # Find similar contacts using fuzzy matching
    try:
        from fuzzywuzzy import fuzz
        matches = []
        for contact in cm.contacts:
            ratio = fuzz.partial_ratio(name.lower(), contact.name.lower())
            if ratio > 60:
                matches.append((contact.name, ratio))
        matches.sort(key=lambda x: x[1], reverse=True)

        if matches:
            print("\nDid you mean:", file=sys.stderr)
            for match_name, score in matches[:5]:
                print(f"  - {match_name}", file=sys.stderr)
        else:
            print(f"\nAvailable contacts: {', '.join(c.name for c in cm.contacts[:10])}...", file=sys.stderr)
    except ImportError:
        # fuzzywuzzy not available, show basic list
        print(f"Available contacts: {', '.join(c.name for c in cm.contacts[:10])}...", file=sys.stderr)

    print("\nTip: Use 'contacts' command to see all contacts, or 'add-contact' to add new ones.", file=sys.stderr)
    return 1


def handle_db_access_error() -> int:
    """Handle Messages.db access errors with actionable guidance."""
    print("Error: Cannot access Messages database.", file=sys.stderr)
    print("\nThis usually means Full Disk Access is not enabled.", file=sys.stderr)
    print("\nTo fix:", file=sys.stderr)
    print("  1. Open System Settings > Privacy & Security > Full Disk Access", file=sys.stderr)
    print("  2. Enable access for Terminal (or your terminal app)", file=sys.stderr)
    print("  3. Restart your terminal", file=sys.stderr)
    return 1


def parse_date_arg(value: str) -> datetime | None:
    """Parse a YYYY-MM-DD date string into a datetime."""
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def cmd_find(args):
    """Find messages with a contact (keyword search)."""
    mi, cm = get_interfaces()
    contact = resolve_contact(cm, args.contact)

    if not contact:
        return handle_contact_not_found(args.contact, cm)

    # Use efficient database-level search when query provided
    if args.query:
        messages = mi.search_messages(query=args.query, phone=contact.phone, limit=args.limit)
    else:
        messages = mi.get_messages_by_phone(contact.phone, limit=args.limit)

    if args.json:
        print(json.dumps(messages, indent=2, default=str))
    else:
        print(f"Messages with {contact.name} ({contact.phone}):")
        print("-" * 60)

        for m in messages:
            sender = "Me" if m.get('is_from_me') else contact.name
            text = m.get('text', '[media/attachment]') or '[media/attachment]'
            timestamp = m.get('timestamp', '')
            print(f"{timestamp} | {sender}: {text[:200]}")

    return 0


def cmd_messages(args):
    """Get messages with a specific contact."""
    mi, cm = get_interfaces()
    contact = resolve_contact(cm, args.contact)

    if not contact:
        print(f"Contact '{args.contact}' not found.", file=sys.stderr)
        return 1

    messages = mi.get_messages_by_phone(contact.phone, limit=args.limit)

    if args.json:
        print(json.dumps(messages, indent=2, default=str))
    else:
        if not messages:
            print("No messages found.")
            return 0

        for m in messages:
            sender = "Me" if m.get('is_from_me') else contact.name
            text = m.get('text', '[media]') or '[media]'
            print(f"{sender}: {text[:200]}")

    return 0


def cmd_recent(args):
    """Get recent conversations across all contacts."""
    mi, _ = get_interfaces()

    conversations = mi.get_all_recent_conversations(limit=args.limit)

    if args.json:
        print(json.dumps(conversations, indent=2, default=str))
    else:
        if not conversations:
            print("No recent conversations found.")
            return 0

        print("Recent Conversations:")
        print("-" * 60)
        for conv in conversations:
            handle = conv.get('handle_id', 'Unknown')
            last_msg = conv.get('last_message', '')[:80]
            timestamp = conv.get('last_message_date', '')
            print(f"{handle}: {last_msg} ({timestamp})")

    return 0


def cmd_unread(args):
    """Get unread messages."""
    mi, _ = get_interfaces()

    messages = mi.get_unread_messages(limit=args.limit)

    if args.json:
        print(json.dumps(messages, indent=2, default=str))
    else:
        if not messages:
            print("No unread messages.")
            return 0

        print(f"Unread Messages ({len(messages)}):")
        print("-" * 60)
        for m in messages:
            sender = m.get('sender', 'Unknown')
            text = m.get('text', '[media]') or '[media]'
            print(f"{sender}: {text[:150]}")

    return 0


def cmd_send(args):
    """Send a message to a contact."""
    mi, cm = get_interfaces()
    contact = resolve_contact(cm, args.contact)

    if not contact:
        return handle_contact_not_found(args.contact, cm)

    message = " ".join(args.message)

    print(f"Sending to {contact.name} ({contact.phone}): {message[:50]}...", file=sys.stderr)
    result = mi.send_message(contact.phone, message)

    if result.get('success'):
        # Log interaction for CRM tracking
        cm.log_interaction(
            phone=contact.phone,
            direction="sent",
            message_preview=message[:100],
            channel="imessage"
        )
        print("Message sent successfully.", file=sys.stderr)
        return 0
    else:
        print(f"Failed to send: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1


def cmd_send_by_phone(args):
    """Send a message directly to a phone number (no contact lookup)."""
    mi, cm = get_interfaces()

    # Normalize phone number (strip formatting characters)
    phone = args.phone.strip().translate(str.maketrans('', '', ' ()-.'))

    message = " ".join(args.message)

    print(f"Sending to {phone}: {message[:50]}...", file=sys.stderr)
    result = mi.send_message(phone, message)

    if result.get('success'):
        # Log interaction for CRM tracking
        cm.log_interaction(
            phone=phone,
            direction="sent",
            message_preview=message[:100],
            channel="imessage"
        )
        if args.json:
            print(json.dumps({"success": True, "phone": phone, "message": message}))
        else:
            print("Message sent successfully.", file=sys.stderr)
        return 0
    else:
        error = result.get('error', 'Unknown error')
        if args.json:
            print(json.dumps({"success": False, "phone": phone, "error": error}))
        else:
            print(f"Failed to send: {error}", file=sys.stderr)
        return 1


def cmd_contacts(args):
    """List all contacts."""
    _, cm = get_interfaces()

    if args.json:
        print(json.dumps([c.to_dict() for c in cm.contacts], indent=2))
    else:
        print(f"Contacts ({len(cm.contacts)}):")
        print("-" * 40)
        for c in cm.contacts:
            print(f"{c.name}: {c.phone}")

    return 0


def cmd_analytics(args):
    """Get conversation analytics for a contact."""
    mi, cm = get_interfaces()

    if args.contact:
        contact = resolve_contact(cm, args.contact)
        if not contact:
            print(f"Contact '{args.contact}' not found.", file=sys.stderr)
            return 1
        analytics = mi.get_conversation_analytics(contact.phone, days=args.days)
    else:
        analytics = mi.get_conversation_analytics(days=args.days)

    if args.json:
        print(json.dumps(analytics, indent=2, default=str))
    else:
        print("Conversation Analytics:")
        print("-" * 40)
        for key, value in analytics.items():
            print(f"{key}: {value}")

    return 0


def cmd_followup(args):
    """Detect messages needing follow-up."""
    mi, cm = get_interfaces()

    followups = mi.detect_follow_up_needed(days=args.days, min_stale_days=args.stale)

    if args.json:
        print(json.dumps(followups, indent=2, default=str))
    else:
        # Check if there are any action items
        summary = followups.get("summary", {})
        total_items = summary.get("total_action_items", 0) if summary else 0

        # Also count items across categories if no summary
        if not total_items:
            for key, items in followups.items():
                if key not in ("summary", "analysis_period_days") and isinstance(items, list):
                    total_items += len(items)

        if not total_items:
            print("No follow-ups needed.")
            return 0

        print("Follow-ups Needed:")
        print("-" * 60)

        # Iterate through categories (skip metadata keys)
        for category, items in followups.items():
            if category in ("summary", "analysis_period_days"):
                continue
            if not items or not isinstance(items, list):
                continue

            print(f"\n--- {category.replace('_', ' ').title()} ---")
            for item in items:
                phone = item.get('phone')
                contact = cm.get_contact_by_phone(phone) if phone else None
                name = contact.name if contact else phone or "Unknown"
                text = item.get('text') or item.get('last_message', '')
                date = item.get('date', '')
                print(f"  {name}: {text[:100]} ({date})")

    return 0


# =============================================================================
# T0 COMMANDS - Core Features
# =============================================================================


def cmd_groups(args):
    """List all group chats."""
    mi, _ = get_interfaces()

    groups = mi.list_group_chats(limit=args.limit)

    if args.json:
        print(json.dumps(groups, indent=2, default=str))
    else:
        if not groups:
            print("No group chats found.")
            return 0

        print(f"Group Chats ({len(groups)}):")
        print("-" * 60)
        for g in groups:
            name = g.get('display_name') or g.get('group_id', 'Unknown')
            participants = g.get('participant_count', 0)
            msg_count = g.get('message_count', 0)
            print(f"{name} ({participants} members, {msg_count} messages)")
            print(f"  ID: {g.get('group_id', 'N/A')}")

    return 0


def cmd_group_messages(args):
    """Get messages from a group chat."""
    mi, _ = get_interfaces()

    if not args.group_id and not args.participant:
        print("Error: Must provide --group-id or --participant", file=sys.stderr)
        return 1

    messages = mi.get_group_messages(
        group_id=args.group_id,
        participant_filter=args.participant,
        limit=args.limit
    )

    if args.json:
        print(json.dumps(messages, indent=2, default=str))
    else:
        if not messages:
            print("No group messages found.")
            return 0

        print(f"Group Messages ({len(messages)}):")
        print("-" * 60)
        for m in messages:
            sender = "Me" if m.get('is_from_me') else m.get('sender_handle', 'Unknown')
            text = m.get('text', '[media]') or '[media]'
            date = m.get('date', '')
            print(f"[{date}] {sender}: {text[:150]}")

    return 0


def cmd_attachments(args):
    """Get attachments (photos, videos, files) from messages."""
    mi, cm = get_interfaces()

    phone = None
    if args.contact:
        contact = resolve_contact(cm, args.contact)
        if not contact:
            print(f"Contact '{args.contact}' not found.", file=sys.stderr)
            return 1
        phone = contact.phone

    attachments = mi.get_attachments(
        phone=phone,
        mime_type_filter=args.type,
        limit=args.limit
    )

    if args.json:
        print(json.dumps(attachments, indent=2, default=str))
    else:
        if not attachments:
            print("No attachments found.")
            return 0

        print(f"Attachments ({len(attachments)}):")
        print("-" * 60)
        for a in attachments:
            filename = a.get('filename') or a.get('transfer_name', 'Unknown')
            mime = a.get('mime_type', 'unknown')
            size = a.get('total_bytes', 0)
            size_str = f"{size / 1024:.1f}KB" if size else "N/A"
            date = a.get('message_date', '')
            print(f"{filename} ({mime}, {size_str}) - {date}")

    return 0


def cmd_add_contact(args):
    """Add a new contact."""
    _, cm = get_interfaces()

    try:
        cm.add_contact(
            name=args.name,
            phone=args.phone,
            relationship_type=args.relationship,
            notes=args.notes
        )
        print(f"Contact '{args.name}' added successfully.")
        return 0
    except Exception as e:
        print(f"Failed to add contact: {e}", file=sys.stderr)
        return 1


# =============================================================================
# T1 COMMANDS - Advanced Features
# =============================================================================


def cmd_reactions(args):
    """Get reactions (tapbacks) from messages."""
    mi, cm = get_interfaces()

    phone = None
    if args.contact:
        contact = resolve_contact(cm, args.contact)
        if not contact:
            print(f"Contact '{args.contact}' not found.", file=sys.stderr)
            return 1
        phone = contact.phone

    reactions = mi.get_reactions(phone=phone, limit=args.limit)

    if args.json:
        print(json.dumps(reactions, indent=2, default=str))
    else:
        if not reactions:
            print("No reactions found.")
            return 0

        print(f"Reactions ({len(reactions)}):")
        print("-" * 60)
        for r in reactions:
            emoji = r.get('reaction_emoji', '?')
            reactor = "Me" if r.get('is_from_me') else r.get('reactor_handle', 'Unknown')
            original = r.get('original_message_preview', '')[:50]
            date = r.get('date', '')
            print(f"{emoji} by {reactor} on \"{original}...\" ({date})")

    return 0


def cmd_links(args):
    """Extract URLs shared in conversations."""
    mi, cm = get_interfaces()

    phone = None
    if args.contact:
        contact = resolve_contact(cm, args.contact)
        if not contact:
            print(f"Contact '{args.contact}' not found.", file=sys.stderr)
            return 1
        phone = contact.phone

    days = None if getattr(args, "all_time", False) else (args.days if args.days is not None else 30)
    links = mi.extract_links(phone=phone, days=days, limit=args.limit)

    if args.json:
        print(json.dumps(links, indent=2, default=str))
    else:
        if not links:
            print("No links found.")
            return 0

        print(f"Shared Links ({len(links)}):")
        print("-" * 60)
        for link in links:
            url = link.get('url', 'N/A')
            sender = "Me" if link.get('is_from_me') else link.get('sender_handle', 'Unknown')
            date = link.get('date', '')
            print(f"{url}")
            print(f"  From: {sender} ({date})")

    return 0


def cmd_voice(args):
    """Get voice messages with file paths."""
    mi, cm = get_interfaces()

    phone = None
    if args.contact:
        contact = resolve_contact(cm, args.contact)
        if not contact:
            print(f"Contact '{args.contact}' not found.", file=sys.stderr)
            return 1
        phone = contact.phone

    voice_msgs = mi.get_voice_messages(phone=phone, limit=args.limit)

    if args.json:
        print(json.dumps(voice_msgs, indent=2, default=str))
    else:
        if not voice_msgs:
            print("No voice messages found.")
            return 0

        print(f"Voice Messages ({len(voice_msgs)}):")
        print("-" * 60)
        for v in voice_msgs:
            path = v.get('attachment_path', 'N/A')
            sender = "Me" if v.get('is_from_me') else v.get('sender_handle', 'Unknown')
            size = v.get('size_bytes', 0)
            size_str = f"{size / 1024:.1f}KB" if size else "N/A"
            date = v.get('date', '')
            print(f"{path}")
            print(f"  From: {sender}, Size: {size_str}, Date: {date}")

    return 0


def cmd_thread(args):
    """Get messages in a reply thread."""
    mi, _ = get_interfaces()

    if not args.guid:
        print("Error: Must provide --guid for message thread", file=sys.stderr)
        return 1

    thread = mi.get_message_thread(message_guid=args.guid, limit=args.limit)

    if args.json:
        print(json.dumps(thread, indent=2, default=str))
    else:
        if not thread:
            print("No thread messages found.")
            return 0

        print(f"Thread Messages ({len(thread)}):")
        print("-" * 60)
        for m in thread:
            sender = "Me" if m.get('is_from_me') else m.get('sender_handle', 'Unknown')
            text = m.get('text', '[media]') or '[media]'
            date = m.get('date', '')
            is_originator = " [THREAD START]" if m.get('is_thread_originator') else ""
            print(f"[{date}] {sender}: {text[:150]}{is_originator}")

    return 0


# =============================================================================
# T2 COMMANDS - Discovery Features
# =============================================================================


def cmd_handles(args):
    """List all unique phone/email handles from recent messages."""
    mi, _ = get_interfaces()

    handles = mi.list_recent_handles(days=args.days, limit=args.limit)

    if args.json:
        print(json.dumps(handles, indent=2, default=str))
    else:
        if not handles:
            print("No handles found.")
            return 0

        print(f"Recent Handles ({len(handles)}):")
        print("-" * 60)
        for h in handles:
            handle = h.get('handle', 'Unknown')
            msg_count = h.get('message_count', 0)
            last_date = h.get('last_message_date', '')
            print(f"{handle} ({msg_count} messages, last: {last_date})")

    return 0


def cmd_unknown(args):
    """Find messages from senders not in contacts."""
    mi, cm = get_interfaces()

    known_phones = [c.phone for c in cm.contacts]
    unknown = mi.search_unknown_senders(
        known_phones=known_phones,
        days=args.days,
        limit=args.limit
    )

    if args.json:
        print(json.dumps(unknown, indent=2, default=str))
    else:
        if not unknown:
            print("No unknown senders found.")
            return 0

        print(f"Unknown Senders ({len(unknown)}):")
        print("-" * 60)
        for u in unknown:
            handle = u.get('handle', 'Unknown')
            msg_count = u.get('message_count', 0)
            last_date = u.get('last_message_date', '')
            print(f"{handle} ({msg_count} messages, last: {last_date})")
            # Show sample messages if available
            messages = u.get('messages', [])
            for msg in messages[:2]:
                text = msg.get('text', '')[:80] if msg.get('text') else '[media]'
                print(f"  \"{text}\"")

    return 0


def cmd_discover(args):
    """Discover frequent texters that could be added as contacts."""
    mi, cm = get_interfaces()

    # Get all frequent contacts from Messages.db
    frequent = mi.discover_frequent_contacts(
        days=args.days,
        limit=args.limit,
        min_messages=args.min_messages
    )

    # Filter out numbers that are already in contacts
    known_phones = {c.phone.replace('+', '').replace('-', '').replace(' ', '')
                    for c in cm.contacts}

    unknown_frequent = []
    for contact in frequent:
        handle = contact.get('handle', '')
        # Normalize handle for comparison
        normalized = handle.replace('+', '').replace('-', '').replace(' ', '')
        if not any(normalized.endswith(kp) or kp.endswith(normalized)
                   for kp in known_phones if len(kp) >= 10):
            unknown_frequent.append(contact)

    if args.json:
        print(json.dumps(unknown_frequent, indent=2, default=str))
    else:
        if not unknown_frequent:
            print("All frequent contacts are already in your contacts list.")
            return 0

        print(f"Discovered {len(unknown_frequent)} frequent contacts not in your list:")
        print("-" * 60)
        for i, contact in enumerate(unknown_frequent, 1):
            handle = contact.get('handle', 'Unknown')
            msg_count = contact.get('message_count', 0)
            sent = contact.get('sent_count', 0)
            received = contact.get('received_count', 0)
            last_date = contact.get('last_message_date', 'N/A')

            print(f"\n{i}. {handle}")
            print(f"   Messages: {msg_count} ({sent} sent, {received} received)")
            print(f"   Last active: {last_date}")

            # Show sample messages
            samples = contact.get('sample_messages', [])
            if samples:
                print("   Recent messages:")
                for msg in samples[:2]:
                    direction = "You" if msg.get('is_from_me') else "Them"
                    text = msg.get('text', '')[:60]
                    print(f"     {direction}: \"{text}\"")

        print("\n" + "-" * 60)
        print("Tip: Use 'add-contact' to add any of these to your contacts.")

    return 0


def cmd_scheduled(args):
    """Get scheduled messages (pending sends)."""
    mi, _ = get_interfaces()

    scheduled = mi.get_scheduled_messages()

    if args.json:
        print(json.dumps(scheduled, indent=2, default=str))
    else:
        if not scheduled:
            print("No scheduled messages.")
            return 0

        print(f"Scheduled Messages ({len(scheduled)}):")
        print("-" * 60)
        for s in scheduled:
            text = s.get('text', '[media]') or '[media]'
            recipient = s.get('recipient_handle', 'Unknown')
            sched_date = s.get('scheduled_date', 'N/A')
            print(f"To: {recipient}")
            print(f"  Message: {text[:100]}")
            print(f"  Scheduled for: {sched_date}")

    return 0


def cmd_summary(args):
    """Get conversation formatted for AI summarization."""
    mi, cm = get_interfaces()

    contact = resolve_contact(cm, args.contact)
    if not contact:
        print(f"Contact '{args.contact}' not found.", file=sys.stderr)
        return 1

    try:
        start_date = parse_date_arg(getattr(args, "start", None))
        end_date = parse_date_arg(getattr(args, "end", None))
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD for --start/--end.", file=sys.stderr)
        return 1

    days = None
    if not (start_date or end_date):
        days = args.days

    summary = mi.get_conversation_for_summary(
        phone=contact.phone,
        days=days,
        limit=args.limit,
        offset=getattr(args, "offset", 0),
        order=getattr(args, "order", "asc"),
        start_date=start_date,
        end_date=end_date
    )

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"Conversation Summary: {contact.name}")
        print("-" * 60)
        stats = summary.get('key_stats', {})
        print(f"Messages: {summary.get('message_count', 0)}")
        print(f"Date range: {summary.get('date_range', 'N/A')}")
        print(f"Last interaction: {summary.get('last_interaction', 'N/A')}")
        if stats:
            print(f"Sent: {stats.get('sent', 0)}, Received: {stats.get('received', 0)}")
        topics = summary.get('recent_topics', [])
        if topics:
            print(f"Recent topics: {', '.join(topics[:5])}")
        print("\n--- Conversation Text ---")
        print(summary.get('conversation_text', '')[:2000])
        if len(summary.get('conversation_text', '')) > 2000:
            print("... (truncated, use --json for full output)")

    return 0


# =============================================================================
# STYLE ANALYSIS COMMANDS - Message Pattern Analysis
# =============================================================================


def get_style_analyzer():
    """Get StyleAnalyzer instance (lazy import for faster startup)."""
    from src.style_analyzer import StyleAnalyzer
    return StyleAnalyzer()


def cmd_style_analyze(args):
    """Analyze a contact's messaging style."""
    mi, cm = get_interfaces()

    # Resolve contact
    contact = resolve_contact(cm, args.contact)
    if not contact:
        return handle_contact_not_found(args.contact, cm)

    try:
        analyzer = get_style_analyzer()
        profile = analyzer.analyze_contact(
            contact_name=contact.name,
            limit=args.limit,
            days=args.days,
        )

        if args.json:
            print(json.dumps(profile.to_dict(), indent=2, default=str))
        else:
            print(f"Style Profile: {profile.contact_name}")
            print("=" * 60)
            print(f"\nSummary: {profile.get_style_summary()}")
            print(f"\nMessages analyzed: {profile.message_count}")
            print(f"Avg message length: {profile.avg_word_count:.1f} words")

            print(f"\nFormality: {profile._formality_level()} ({profile.formality_score:.0%})")
            print(f"  Uses punctuation: {'Yes' if profile.uses_punctuation else 'No'}")
            print(f"  Uses capitalization: {'Yes' if profile.uses_capitalization else 'No'}")
            print(f"  Uses contractions: {'Yes' if profile.uses_contractions else 'No'}")

            print(f"\nEmoji usage: {profile.emoji_frequency:.1f} per message")
            if profile.top_emojis:
                print(f"  Favorites: {' '.join(profile.top_emojis[:5])}")

            if profile.common_greetings:
                print(f"\nCommon greetings: {', '.join(profile.common_greetings)}")
            if profile.common_phrases:
                print(f"Common phrases: {', '.join(profile.common_phrases)}")

            if profile.avg_response_time_minutes:
                print(f"\nAvg response time: {profile.avg_response_time_minutes:.0f} minutes")
            if profile.active_hours:
                hours = [f"{h}:00" for h in profile.active_hours[:3]]
                print(f"Most active: {', '.join(hours)}")

            print(f"\n--- Style Guidance ---")
            print(analyzer.generate_style_guidance(profile))

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error analyzing style: {e}", file=sys.stderr)
        return 1


# =============================================================================
# DRAFTING COMMANDS - Context-Aware Message Drafting
# =============================================================================


def get_drafter():
    """Get MessageDrafter instance (lazy import for faster startup)."""
    from src.drafting import MessageDrafter
    return MessageDrafter()


def cmd_draft(args):
    """Create a context-aware message draft."""
    mi, cm = get_interfaces()

    # Resolve contact
    contact = resolve_contact(cm, args.contact)
    if not contact:
        return handle_contact_not_found(args.contact, cm)

    try:
        drafter = get_drafter()

        # Get the message if provided
        message = " ".join(args.message) if args.message else None

        # Create draft
        draft = drafter.create_draft(
            contact_name=contact.name,
            message=message,
            topic=args.topic,
            intent=args.intent,
            use_template=args.template,
        )

        if args.json:
            print(json.dumps(draft.to_dict(), indent=2, default=str))
        else:
            if args.send:
                # Send immediately
                success = mi.send_message(draft.contact_phone, draft.message)
                if success:
                    print(f"✓ Sent to {draft.contact_name}: {draft.message}")
                else:
                    print(f"✗ Failed to send message", file=sys.stderr)
                    return 1
            else:
                # Show preview
                print(drafter.format_draft_preview(draft))
                print("")
                print("To send this message, add --send flag")
                print(f"  Example: draft '{args.contact}' --send")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error creating draft: {e}", file=sys.stderr)
        return 1


def cmd_draft_context(args):
    """Show drafting context for a contact."""
    mi, cm = get_interfaces()

    # Resolve contact
    contact = resolve_contact(cm, args.contact)
    if not contact:
        return handle_contact_not_found(args.contact, cm)

    try:
        drafter = get_drafter()
        context = drafter.gather_context(
            contact_name=contact.name,
            topic=args.topic,
            intent=args.intent,
            message_limit=args.limit,
        )

        if args.json:
            print(json.dumps(context.to_dict(), indent=2, default=str))
        else:
            print(f"Drafting Context: {context.contact_name}")
            print("=" * 50)

            if context.conversation_gap_hours:
                if context.conversation_gap_hours < 1:
                    gap = f"{int(context.conversation_gap_hours * 60)} minutes"
                elif context.conversation_gap_hours < 24:
                    gap = f"{int(context.conversation_gap_hours)} hours"
                else:
                    gap = f"{int(context.conversation_gap_hours / 24)} days"
                print(f"\nLast interaction: {gap} ago")

            if context.last_message_from_contact:
                preview = context.last_message_from_contact[:100]
                if len(context.last_message_from_contact) > 100:
                    preview += "..."
                print(f"\nTheir last message:")
                print(f"  \"{preview}\"")

            if context.last_message_to_contact:
                preview = context.last_message_to_contact[:100]
                if len(context.last_message_to_contact) > 100:
                    preview += "..."
                print(f"\nYour last message:")
                print(f"  \"{preview}\"")

            if context.style_guidance:
                print(f"\nStyle guidance: {context.style_guidance}")

            if context.suggested_replies:
                print(f"\nSuggested replies:")
                for i, suggestion in enumerate(context.suggested_replies, 1):
                    print(f"  {i}. {suggestion}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error getting context: {e}", file=sys.stderr)
        return 1


# =============================================================================
# TEMPLATE COMMANDS - Reusable Message Templates
# =============================================================================


def get_template_manager():
    """Get TemplateManager instance (lazy import for faster startup)."""
    from src.templates import TemplateManager
    return TemplateManager()


def cmd_template_list(args):
    """List available message templates."""
    try:
        tm = get_template_manager()
        templates = tm.list_templates()

        if args.json:
            print(json.dumps([t.to_dict() for t in templates], indent=2, default=str))
        else:
            if not templates:
                print("No templates available.")
                return 0

            print(f"Message Templates ({len(templates)}):")
            print("-" * 70)
            for t in templates:
                custom_marker = " [custom]" if t.is_custom else ""
                vars_str = ", ".join(f"{{{v}}}" for v in t.variables) if t.variables else "(no variables)"
                print(f"\n  {t.id}{custom_marker}")
                print(f"    {t.name}: {t.description}")
                print(f"    Variables: {vars_str}")
                print(f"    Preview: {t.template[:60]}{'...' if len(t.template) > 60 else ''}")

        return 0

    except Exception as e:
        print(f"Error listing templates: {e}", file=sys.stderr)
        return 1


def cmd_template_use(args):
    """Use a template to send a message."""
    mi, cm = get_interfaces()

    # Resolve contact
    contact = resolve_contact(cm, args.contact)
    if not contact:
        return handle_contact_not_found(args.contact, cm)

    try:
        tm = get_template_manager()
        template = tm.find_template(args.template)

        if not template:
            print(f"Template '{args.template}' not found.", file=sys.stderr)
            print("\nAvailable templates:", file=sys.stderr)
            for t in tm.list_templates()[:5]:
                print(f"  - {t.id}: {t.name}", file=sys.stderr)
            return 1

        # Build variables dict from args
        variables = {"name": contact.name}
        if args.topic:
            variables["topic"] = args.topic
        if args.date:
            variables["date"] = args.date
        if args.time:
            variables["time"] = args.time
        if args.custom:
            variables["custom"] = args.custom

        # Check for missing required variables
        missing = [v for v in template.variables if v not in variables or not variables[v]]
        if missing:
            print(f"Missing required variable(s): {', '.join(missing)}", file=sys.stderr)
            print(f"\nUsage: template-use {args.template} {args.contact}", file=sys.stderr)
            for var in template.variables:
                if var != "name":
                    print(f"  --{var} <value>", file=sys.stderr)
            return 1

        # Render the message
        message = template.render(**variables)

        if args.preview:
            print(f"Preview (not sent):")
            print(f"  To: {contact.name} ({contact.phone})")
            print(f"  Message: {message}")
            return 0

        # Send the message
        print(f"Sending to {contact.name}: {message[:50]}...", file=sys.stderr)
        result = mi.send_message(contact.phone, message)

        if result.get('success'):
            cm.log_interaction(
                phone=contact.phone,
                direction="sent",
                message_preview=message[:100],
                channel="imessage"
            )
            if args.json:
                print(json.dumps({"sent": True, "to": contact.name, "message": message}))
            else:
                print(f"✓ Sent using '{template.name}' template")
            return 0
        else:
            print(f"Failed to send: {result.get('error', 'Unknown error')}", file=sys.stderr)
            return 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error using template: {e}", file=sys.stderr)
        return 1


def cmd_template_add(args):
    """Create a custom message template."""
    try:
        tm = get_template_manager()

        template = tm.create_template(
            template_id=args.id,
            name=args.name,
            template=args.template,
            description=args.description or f"Custom template: {args.name}",
        )

        if args.json:
            print(json.dumps(template.to_dict(), indent=2, default=str))
        else:
            print(f"✓ Created template '{template.id}'")
            print(f"  Name: {template.name}")
            print(f"  Variables: {', '.join(f'{{{v}}}' for v in template.variables) or '(none)'}")
            print(f"  Preview: {template.template}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error creating template: {e}", file=sys.stderr)
        return 1


def cmd_template_delete(args):
    """Delete a custom template."""
    try:
        tm = get_template_manager()

        template = tm.get_template(args.id)
        if not template:
            print(f"Template '{args.id}' not found.", file=sys.stderr)
            return 1

        if not template.is_custom:
            print(f"Cannot delete built-in template '{args.id}'.", file=sys.stderr)
            return 1

        if tm.delete_template(args.id):
            if args.json:
                print(json.dumps({"deleted": True, "id": args.id}))
            else:
                print(f"✓ Deleted template '{args.id}'")
            return 0
        else:
            print(f"Failed to delete template '{args.id}'", file=sys.stderr)
            return 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error deleting template: {e}", file=sys.stderr)
        return 1


# =============================================================================
# SCHEDULING COMMANDS - Delayed Message Delivery
# =============================================================================


def get_scheduler():
    """Get MessageScheduler instance (lazy import for faster startup)."""
    from src.scheduler import MessageScheduler
    return MessageScheduler()


def cmd_schedule_add(args):
    """Schedule a message for future delivery."""
    mi, cm = get_interfaces()

    # Resolve contact
    contact = resolve_contact(cm, args.contact)
    if not contact:
        return handle_contact_not_found(args.contact, cm)

    # Parse scheduled time
    from src.scheduler import parse_time
    scheduled_at = parse_time(args.time)

    if not scheduled_at:
        print(f"Error: Could not parse time '{args.time}'", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  'tomorrow at 9am'", file=sys.stderr)
        print("  'in 2 hours'", file=sys.stderr)
        print("  '2026-01-05T09:00:00'", file=sys.stderr)
        return 1

    if scheduled_at < datetime.now():
        print(f"Error: Cannot schedule in the past: {scheduled_at}", file=sys.stderr)
        return 1

    message = " ".join(args.message)

    try:
        scheduler = get_scheduler()
        scheduled = scheduler.schedule(
            phone=contact.phone,
            message=message,
            scheduled_at=scheduled_at,
            contact_name=contact.name,
            contact_id=contact.id,
            recurrence=args.recur,
        )

        if args.json:
            print(json.dumps(scheduled.to_dict(), indent=2, default=str))
        else:
            print(f"✓ Scheduled message #{scheduled.id}")
            print(f"  To: {contact.name} ({contact.phone})")
            print(f"  When: {scheduled_at.strftime('%Y-%m-%d %I:%M %p')}")
            print(f"  Message: {message[:50]}{'...' if len(message) > 50 else ''}")
            if args.recur:
                print(f"  Recurring: {args.recur}")
            print(f"\nTo cancel: schedule-cancel {scheduled.id}")

        return 0

    except Exception as e:
        print(f"Error scheduling message: {e}", file=sys.stderr)
        return 1


def cmd_schedule_list(args):
    """List scheduled messages."""
    from src.scheduler import ScheduleStatus

    try:
        scheduler = get_scheduler()

        # Determine status filter
        status = None
        if args.status:
            try:
                status = ScheduleStatus(args.status)
            except ValueError:
                print(f"Invalid status: {args.status}", file=sys.stderr)
                print(f"Valid statuses: pending, sent, cancelled, failed", file=sys.stderr)
                return 1

        messages = scheduler.list_scheduled(
            status=status,
            limit=args.limit,
            include_past=args.all,
        )

        if args.json:
            print(json.dumps([m.to_dict() for m in messages], indent=2, default=str))
        else:
            if not messages:
                print("No scheduled messages found.")
                return 0

            print(f"Scheduled Messages ({len(messages)}):")
            print("-" * 70)
            for msg in messages:
                status_icon = {
                    "pending": "⏳",
                    "sent": "✓",
                    "cancelled": "✗",
                    "failed": "⚠",
                }.get(msg.status.value, "?")

                time_str = msg.scheduled_at.strftime("%Y-%m-%d %I:%M %p")
                name = msg.contact_name or msg.phone
                preview = msg.message[:40] + ("..." if len(msg.message) > 40 else "")

                print(f"  #{msg.id} {status_icon} {time_str} | {name}: {preview}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run: python scripts/migrations/003_add_scheduled_messages.py", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error listing scheduled messages: {e}", file=sys.stderr)
        return 1


def cmd_schedule_cancel(args):
    """Cancel a scheduled message."""
    try:
        scheduler = get_scheduler()

        # Get message first to show details
        msg = scheduler.get_by_id(args.id)
        if not msg:
            print(f"Scheduled message #{args.id} not found.", file=sys.stderr)
            return 1

        if msg.status.value != "pending":
            print(f"Cannot cancel: message status is '{msg.status.value}'", file=sys.stderr)
            return 1

        if scheduler.cancel(args.id):
            if args.json:
                print(json.dumps({"cancelled": True, "id": args.id}))
            else:
                print(f"✓ Cancelled scheduled message #{args.id}")
                print(f"  To: {msg.contact_name or msg.phone}")
                print(f"  Was scheduled for: {msg.scheduled_at.strftime('%Y-%m-%d %I:%M %p')}")
            return 0
        else:
            print(f"Failed to cancel message #{args.id}", file=sys.stderr)
            return 1

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error cancelling message: {e}", file=sys.stderr)
        return 1


def cmd_schedule_send(args):
    """Send all due scheduled messages now."""
    mi, _ = get_interfaces()

    try:
        scheduler = get_scheduler()

        # Get due messages first
        due = scheduler.get_due_messages()
        if not due:
            print("No messages are due to be sent.")
            return 0

        print(f"Found {len(due)} message(s) ready to send...")

        # Send them
        results = scheduler.send_due_messages(mi)

        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"\n✓ Sent: {results['sent']}")
            if results['failed'] > 0:
                print(f"⚠ Failed: {results['failed']}")
                for err in results['errors']:
                    print(f"  - {err}")

        return 0 if results['failed'] == 0 else 1

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error sending scheduled messages: {e}", file=sys.stderr)
        return 1


# =============================================================================
# RAG COMMANDS - Semantic Search & Knowledge Base
# =============================================================================


def get_unified_retriever():
    """Get UnifiedRetriever instance (lazy import for faster startup)."""
    from src.rag.unified import UnifiedRetriever
    return UnifiedRetriever()


def cmd_index(args):
    """Index content from a source for semantic search."""
    import time
    start = time.time()

    source = args.source.lower()

    if source not in VALID_RAG_SOURCES:
        print(f"Error: Unknown source '{source}'", file=sys.stderr)
        print(f"Valid sources: {', '.join(VALID_RAG_SOURCES)}", file=sys.stderr)
        return 1

    try:
        if source == 'imessage':
            # iMessage needs MessagesInterface and ContactsManager
            mi, cm = get_interfaces()
            from src.rag.unified import UnifiedRetriever
            from src.rag.unified.imessage_indexer import ImessageIndexer

            retriever = UnifiedRetriever()
            indexer = ImessageIndexer(
                messages_interface=mi,
                contacts_manager=cm,
                store=retriever.store,
            )
            result = indexer.index(
                days=args.days,
                limit=args.limit,
                contact_name=args.contact,
                incremental=not args.full,
            )
        elif source == 'superwhisper':
            retriever = get_unified_retriever()
            result = retriever.index_superwhisper(days=args.days, limit=args.limit)
        elif source == 'notes':
            retriever = get_unified_retriever()
            result = retriever.index_notes(days=args.days, limit=args.limit)
        elif source == 'local':
            retriever = get_unified_retriever()
            result = retriever.index_local_sources(days=args.days)
        else:
            # Gmail, Slack, Calendar require pre-fetched data
            print(f"Error: Source '{source}' requires pre-fetched data.", file=sys.stderr)
            print("Use the appropriate MCP tools to fetch data first, then pass to the indexer.", file=sys.stderr)
            return 1

        elapsed = time.time() - start

        if args.json:
            result['elapsed_seconds'] = elapsed
            print(json.dumps(result, indent=2, default=str))
        else:
            chunks_indexed = result.get('chunks_indexed', 0)
            chunks_found = result.get('chunks_found', chunks_indexed)
            print(f"✓ Indexed {source}")
            print(f"  Chunks found: {chunks_found}")
            print(f"  Chunks indexed: {chunks_indexed}")
            print(f"  Duration: {elapsed:.1f}s")

            if source == 'local':
                by_source = result.get('by_source', {})
                for src, info in by_source.items():
                    print(f"  - {src}: {info.get('chunks_indexed', 0)} chunks")

        return 0

    except Exception as e:
        print(f"Error indexing {source}: {e}", file=sys.stderr)
        return 1


def cmd_search(args):
    """Semantic search across indexed knowledge base."""
    try:
        retriever = get_unified_retriever()

        # Parse sources if provided
        sources = None
        if args.sources:
            sources = [s.strip() for s in args.sources.split(',')]

        results = retriever.search(
            query=args.query,
            sources=sources,
            limit=args.limit,
            days=args.days,
        )

        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            if not results:
                print(f'No results found for: "{args.query}"')
                return 0

            print(f'Found {len(results)} result(s) for: "{args.query}"')
            print("-" * 60)

            for i, result in enumerate(results, 1):
                score = result.get('score', 0) * 100
                source = result.get('source', 'unknown')
                title = result.get('title') or result.get('context_id', '')[:30]
                timestamp = result.get('timestamp', '')[:10] if result.get('timestamp') else ''
                text = result.get('text', '')[:200]

                print(f"\n[{i}] [{source}] {title} | {timestamp} | {score:.0f}% match")
                print(f"    {text}...")

        return 0

    except Exception as e:
        print(f"Error searching: {e}", file=sys.stderr)
        return 1


def cmd_ask(args):
    """Get AI-formatted context from knowledge base."""
    try:
        retriever = get_unified_retriever()

        # Parse sources if provided
        sources = None
        if args.sources:
            sources = [s.strip() for s in args.sources.split(',')]

        context = retriever.ask(
            question=args.question,
            sources=sources,
            limit=args.limit,
            days=args.days,
        )

        if args.json:
            print(json.dumps({"question": args.question, "context": context}, indent=2))
        else:
            print(context)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_stats(args):
    """Show statistics about the indexed knowledge base."""
    try:
        retriever = get_unified_retriever()
        stats = retriever.get_stats(source=args.source)

        if args.json:
            print(json.dumps(stats, indent=2, default=str))
        else:
            total = stats.get('total_chunks', 0)
            if total == 0:
                print("Knowledge base is empty.")
                print("\nRun 'index --source=<source>' to start indexing:")
                print("  index --source=imessage      Index iMessage conversations")
                print("  index --source=superwhisper  Index voice transcriptions")
                print("  index --source=notes         Index markdown notes")
                print("  index --source=local         Index all local sources")
                return 0

            print("Knowledge Base Statistics")
            print("=" * 40)
            print(f"Total chunks indexed: {total}")
            print(f"Unique participants: {stats.get('unique_participants', 0)}")
            print(f"Unique tags: {stats.get('unique_tags', 0)}")

            by_source = stats.get('by_source', {})
            if by_source:
                print("\nBy Source:")
                for src, info in sorted(by_source.items()):
                    count = info.get('chunk_count', 0)
                    if count > 0:
                        oldest = info.get('oldest', 'N/A')[:10] if info.get('oldest') else 'N/A'
                        newest = info.get('newest', 'N/A')[:10] if info.get('newest') else 'N/A'
                        print(f"  {src}: {count} chunks ({oldest} to {newest})")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_clear(args):
    """Clear indexed data from the knowledge base."""
    try:
        retriever = get_unified_retriever()

        # Get current stats for confirmation
        stats = retriever.get_stats(source=args.source)
        total = stats.get('total_chunks', 0)

        if total == 0:
            print("Nothing to clear - knowledge base is empty.")
            return 0

        if not args.force:
            source_msg = f" for source '{args.source}'" if args.source else ""
            print(f"About to delete {total} chunks{source_msg}.")
            print("Use --force to confirm deletion.")
            return 1

        deleted = retriever.clear(source=args.source)

        if args.json:
            print(json.dumps({"deleted_chunks": deleted, "source": args.source or "all"}, indent=2))
        else:
            print(f"✓ Deleted {deleted} chunks")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_sources(args):
    """List available and indexed sources."""
    try:
        retriever = get_unified_retriever()

        available = retriever.list_sources()
        indexed = retriever.get_indexed_sources()
        stats = retriever.get_stats()
        by_source = stats.get('by_source', {})

        if args.json:
            result = {
                "available": available,
                "indexed": indexed,
                "details": {
                    src: by_source.get(src, {}).get('chunk_count', 0)
                    for src in available
                }
            }
            print(json.dumps(result, indent=2))
        else:
            print("Available Sources:")
            print("-" * 40)
            for src in available:
                count = by_source.get(src, {}).get('chunk_count', 0)
                status = f"({count} chunks)" if count > 0 else "(not indexed)"
                marker = "✓" if src in indexed else " "
                print(f"  {marker} {src} {status}")

            print("\nTo index a source:")
            print("  index --source=<source> [--days=30]")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Run the iMessage Gateway CLI."""
    parser = argparse.ArgumentParser(
        description="iMessage Gateway - Standalone CLI for iMessage operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s find "Angus" --query "SF"       Find messages with Angus containing "SF"
  %(prog)s messages "John" --limit 10      Get last 10 messages with John
  %(prog)s recent                          Show recent conversations
  %(prog)s unread                          Show unread messages
  %(prog)s send "John" "Running late!"     Send message to John
  %(prog)s send-by-phone +14155551234 "Hi" Send directly to phone number
  %(prog)s contacts                        List all contacts
  %(prog)s followup --days 7               Find messages needing follow-up
  %(prog)s search "dinner plans"           Semantic search across indexed messages
  %(prog)s index --source=imessage         Index iMessages for semantic search
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # find command (keyword search in messages)
    p_find = subparsers.add_parser('find', help='Find messages with a contact (keyword search)')
    p_find.add_argument('contact', help='Contact name (fuzzy matched)')
    p_find.add_argument('--query', '-q', help='Text to search for in messages')
    p_find.add_argument('--limit', '-l', type=int, default=30, choices=range(1, 501), metavar='N',
                        help='Max messages to return (1-500, default: 30)')
    p_find.add_argument('--json', action='store_true', help='Output as JSON')
    p_find.set_defaults(func=cmd_find)

    # messages command
    p_messages = subparsers.add_parser('messages', help='Get messages with a contact')
    p_messages.add_argument('contact', help='Contact name')
    p_messages.add_argument('--limit', '-l', type=int, default=20, choices=range(1, 501), metavar='N',
                            help='Max messages (1-500, default: 20)')
    p_messages.add_argument('--json', action='store_true', help='Output as JSON')
    p_messages.set_defaults(func=cmd_messages)

    # recent command
    p_recent = subparsers.add_parser('recent', help='Get recent conversations')
    p_recent.add_argument('--limit', '-l', type=int, default=10, choices=range(1, 501), metavar='N',
                          help='Max conversations (1-500, default: 10)')
    p_recent.add_argument('--json', action='store_true', help='Output as JSON')
    p_recent.set_defaults(func=cmd_recent)

    # unread command
    p_unread = subparsers.add_parser('unread', help='Get unread messages')
    p_unread.add_argument('--limit', '-l', type=int, default=20, choices=range(1, 501), metavar='N',
                          help='Max messages (1-500, default: 20)')
    p_unread.add_argument('--json', action='store_true', help='Output as JSON')
    p_unread.set_defaults(func=cmd_unread)

    # send command
    p_send = subparsers.add_parser('send', help='Send a message')
    p_send.add_argument('contact', help='Contact name')
    p_send.add_argument('message', nargs='+', help='Message to send')
    p_send.set_defaults(func=cmd_send)

    # send-by-phone command
    p_send_phone = subparsers.add_parser('send-by-phone', help='Send message directly to phone number')
    p_send_phone.add_argument('phone', help='Phone number (e.g., +14155551234)')
    p_send_phone.add_argument('message', nargs='+', help='Message to send')
    p_send_phone.add_argument('--json', action='store_true', help='Output as JSON')
    p_send_phone.set_defaults(func=cmd_send_by_phone)

    # contacts command
    p_contacts = subparsers.add_parser('contacts', help='List all contacts')
    p_contacts.add_argument('--json', action='store_true', help='Output as JSON')
    p_contacts.set_defaults(func=cmd_contacts)

    # analytics command
    p_analytics = subparsers.add_parser('analytics', help='Get conversation analytics')
    p_analytics.add_argument('contact', nargs='?', help='Contact name (optional)')
    p_analytics.add_argument('--days', '-d', type=int, default=30, choices=range(1, 366), metavar='N',
                             help='Days to analyze (1-365, default: 30)')
    p_analytics.add_argument('--json', action='store_true', help='Output as JSON')
    p_analytics.set_defaults(func=cmd_analytics)

    # followup command
    p_followup = subparsers.add_parser('followup', help='Detect messages needing follow-up')
    p_followup.add_argument('--days', '-d', type=int, default=7, choices=range(1, 366), metavar='N',
                            help='Days to look back (1-365, default: 7)')
    p_followup.add_argument('--stale', '-s', type=int, default=2, choices=range(1, 366), metavar='N',
                            help='Min stale days (1-365, default: 2)')
    p_followup.add_argument('--json', action='store_true', help='Output as JSON')
    p_followup.set_defaults(func=cmd_followup)

    # =========================================================================
    # T0 COMMANDS - Core Features
    # =========================================================================

    # groups command
    p_groups = subparsers.add_parser('groups', help='List all group chats')
    p_groups.add_argument('--limit', '-l', type=int, default=50, choices=range(1, 501), metavar='N',
                          help='Max groups to return (1-500, default: 50)')
    p_groups.add_argument('--json', action='store_true', help='Output as JSON')
    p_groups.set_defaults(func=cmd_groups)

    # group-messages command
    p_group_msg = subparsers.add_parser('group-messages', help='Get messages from a group chat')
    p_group_msg.add_argument('--group-id', '-g', dest='group_id', help='Group chat ID')
    p_group_msg.add_argument('--participant', '-p', help='Filter by participant phone/email')
    p_group_msg.add_argument('--limit', '-l', type=int, default=50, choices=range(1, 501), metavar='N',
                             help='Max messages (1-500, default: 50)')
    p_group_msg.add_argument('--json', action='store_true', help='Output as JSON')
    p_group_msg.set_defaults(func=cmd_group_messages)

    # attachments command
    p_attach = subparsers.add_parser('attachments', help='Get attachments (photos, videos, files)')
    p_attach.add_argument('contact', nargs='?', help='Contact name (optional)')
    p_attach.add_argument('--type', '-t', help='MIME type filter (e.g., "image/", "video/")')
    p_attach.add_argument('--limit', '-l', type=int, default=50, choices=range(1, 501), metavar='N',
                          help='Max attachments (1-500, default: 50)')
    p_attach.add_argument('--json', action='store_true', help='Output as JSON')
    p_attach.set_defaults(func=cmd_attachments)

    # add-contact command
    p_add = subparsers.add_parser('add-contact', help='Add a new contact')
    p_add.add_argument('name', help='Contact name')
    p_add.add_argument('phone', help='Phone number (e.g., +14155551234 or +1-415-555-1234)')
    p_add.add_argument('--relationship', '-r', default='other',
                       choices=['friend', 'family', 'colleague', 'professional', 'other'],
                       help='Relationship type (default: other)')
    p_add.add_argument('--notes', '-n', help='Notes about the contact')
    p_add.set_defaults(func=cmd_add_contact)

    # =========================================================================
    # T1 COMMANDS - Advanced Features
    # =========================================================================

    # reactions command
    p_react = subparsers.add_parser('reactions', help='Get reactions (tapbacks) from messages')
    p_react.add_argument('contact', nargs='?', help='Contact name (optional)')
    p_react.add_argument('--limit', '-l', type=int, default=100, choices=range(1, 501), metavar='N',
                         help='Max reactions (1-500, default: 100)')
    p_react.add_argument('--json', action='store_true', help='Output as JSON')
    p_react.set_defaults(func=cmd_reactions)

    # links command
    p_links = subparsers.add_parser('links', help='Extract URLs shared in conversations')
    p_links.add_argument('contact', nargs='?', help='Contact name (optional)')
    p_links.add_argument('--days', '-d', type=int, choices=range(1, 366), metavar='N',
                         help='Days to look back (1-365)')
    p_links.add_argument('--all-time', action='store_true',
                         help='Search without date cutoff (can be slow)')
    p_links.add_argument('--limit', '-l', type=int, default=100, choices=range(1, 501), metavar='N',
                         help='Max links (1-500, default: 100)')
    p_links.add_argument('--json', action='store_true', help='Output as JSON')
    p_links.set_defaults(func=cmd_links)

    # voice command
    p_voice = subparsers.add_parser('voice', help='Get voice messages with file paths')
    p_voice.add_argument('contact', nargs='?', help='Contact name (optional)')
    p_voice.add_argument('--limit', '-l', type=int, default=50, choices=range(1, 501), metavar='N',
                         help='Max voice messages (1-500, default: 50)')
    p_voice.add_argument('--json', action='store_true', help='Output as JSON')
    p_voice.set_defaults(func=cmd_voice)

    # thread command
    p_thread = subparsers.add_parser('thread', help='Get messages in a reply thread')
    p_thread.add_argument('--guid', '-g', required=True, help='Message GUID to get thread for')
    p_thread.add_argument('--limit', '-l', type=int, default=50, choices=range(1, 501), metavar='N',
                          help='Max messages (1-500, default: 50)')
    p_thread.add_argument('--json', action='store_true', help='Output as JSON')
    p_thread.set_defaults(func=cmd_thread)

    # =========================================================================
    # T2 COMMANDS - Discovery Features
    # =========================================================================

    # handles command
    p_handles = subparsers.add_parser('handles', help='List all phone/email handles from recent messages')
    p_handles.add_argument('--days', '-d', type=int, default=30, choices=range(1, 366), metavar='N',
                           help='Days to look back (1-365, default: 30)')
    p_handles.add_argument('--limit', '-l', type=int, default=100, choices=range(1, 501), metavar='N',
                           help='Max handles (1-500, default: 100)')
    p_handles.add_argument('--json', action='store_true', help='Output as JSON')
    p_handles.set_defaults(func=cmd_handles)

    # unknown command
    p_unknown = subparsers.add_parser('unknown', help='Find messages from senders not in contacts')
    p_unknown.add_argument('--days', '-d', type=int, default=30, choices=range(1, 366), metavar='N',
                           help='Days to look back (1-365, default: 30)')
    p_unknown.add_argument('--limit', '-l', type=int, default=100, choices=range(1, 501), metavar='N',
                           help='Max unknown senders (1-500, default: 100)')
    p_unknown.add_argument('--json', action='store_true', help='Output as JSON')
    p_unknown.set_defaults(func=cmd_unknown)

    # discover command - find frequent texters not in contacts
    p_discover = subparsers.add_parser('discover', help='Discover frequent texters that could be added as contacts')
    p_discover.add_argument('--days', '-d', type=int, default=90, choices=range(1, 366), metavar='N',
                            help='Days to look back (1-365, default: 90)')
    p_discover.add_argument('--limit', '-l', type=int, default=20, choices=range(1, 101), metavar='N',
                            help='Max contacts to discover (1-100, default: 20)')
    p_discover.add_argument('--min-messages', '-m', type=int, default=5, metavar='N',
                            help='Minimum message count to include (default: 5)')
    p_discover.add_argument('--json', action='store_true', help='Output as JSON')
    p_discover.set_defaults(func=cmd_discover)

    # scheduled command
    p_sched = subparsers.add_parser('scheduled', help='Get scheduled messages (pending sends)')
    p_sched.add_argument('--json', action='store_true', help='Output as JSON')
    p_sched.set_defaults(func=cmd_scheduled)

    # summary command
    p_summary = subparsers.add_parser('summary', help='Get conversation formatted for AI summarization')
    p_summary.add_argument('contact', help='Contact name')
    p_summary.add_argument('--days', '-d', type=int, choices=range(1, 366), metavar='N',
                           help='Days to include (1-365)')
    p_summary.add_argument('--start', help='Start date (YYYY-MM-DD)')
    p_summary.add_argument('--end', help='End date (YYYY-MM-DD)')
    p_summary.add_argument('--limit', '-l', type=int, default=200, choices=range(1, 5001), metavar='N',
                           help='Max messages (1-5000, default: 200)')
    p_summary.add_argument('--offset', type=int, default=0,
                           help='Skip this many messages (for pagination)')
    p_summary.add_argument('--order', choices=['asc', 'desc'], default='asc',
                           help='Sort order by date (default: asc)')
    p_summary.add_argument('--json', action='store_true', help='Output as JSON')
    p_summary.set_defaults(func=cmd_summary)

    # =========================================================================
    # TEMPLATE COMMANDS - Reusable Message Templates
    # =========================================================================

    # template-list command - list available templates
    p_tpl_list = subparsers.add_parser('template-list', help='List available message templates')
    p_tpl_list.add_argument('--json', action='store_true', help='Output as JSON')
    p_tpl_list.set_defaults(func=cmd_template_list)

    # template-use command - use a template to send a message
    p_tpl_use = subparsers.add_parser('template-use', help='Use a template to send a message')
    p_tpl_use.add_argument('template', help='Template ID or name (e.g., "thank-you", "birthday")')
    p_tpl_use.add_argument('contact', help='Contact name to send to')
    p_tpl_use.add_argument('--topic', help='Value for {topic} variable')
    p_tpl_use.add_argument('--date', help='Value for {date} variable')
    p_tpl_use.add_argument('--time', help='Value for {time} variable')
    p_tpl_use.add_argument('--custom', help='Value for {custom} variable')
    p_tpl_use.add_argument('--preview', '-p', action='store_true',
                           help='Preview message without sending')
    p_tpl_use.add_argument('--json', action='store_true', help='Output as JSON')
    p_tpl_use.set_defaults(func=cmd_template_use)

    # template-add command - create a custom template
    p_tpl_add = subparsers.add_parser('template-add', help='Create a custom message template')
    p_tpl_add.add_argument('id', help='Unique template ID (lowercase, hyphenated)')
    p_tpl_add.add_argument('name', help='Display name for the template')
    p_tpl_add.add_argument('template', help='Template text with {variables}')
    p_tpl_add.add_argument('--description', '-d', help='Description of when to use')
    p_tpl_add.add_argument('--json', action='store_true', help='Output as JSON')
    p_tpl_add.set_defaults(func=cmd_template_add)

    # template-delete command - delete a custom template
    p_tpl_del = subparsers.add_parser('template-delete', help='Delete a custom template')
    p_tpl_del.add_argument('id', help='Template ID to delete')
    p_tpl_del.add_argument('--json', action='store_true', help='Output as JSON')
    p_tpl_del.set_defaults(func=cmd_template_delete)

    # =========================================================================
    # SCHEDULING COMMANDS - Delayed Message Delivery
    # =========================================================================

    # schedule command - schedule a message for future delivery
    p_schedule = subparsers.add_parser('schedule', help='Schedule a message for future delivery')
    p_schedule.add_argument('contact', help='Contact name')
    p_schedule.add_argument('time', help='When to send (e.g., "tomorrow at 9am", "in 2 hours")')
    p_schedule.add_argument('message', nargs='+', help='Message to send')
    p_schedule.add_argument('--recur', choices=['daily', 'weekly', 'monthly'],
                            help='Make this a recurring message')
    p_schedule.add_argument('--json', action='store_true', help='Output as JSON')
    p_schedule.set_defaults(func=cmd_schedule_add)

    # schedule-list command - list scheduled messages
    p_sched_list = subparsers.add_parser('schedule-list', help='List scheduled messages')
    p_sched_list.add_argument('--status', choices=['pending', 'sent', 'cancelled', 'failed'],
                              help='Filter by status (default: pending)')
    p_sched_list.add_argument('--all', action='store_true',
                              help='Include past messages')
    p_sched_list.add_argument('--limit', '-l', type=int, default=50,
                              help='Max messages to show (default: 50)')
    p_sched_list.add_argument('--json', action='store_true', help='Output as JSON')
    p_sched_list.set_defaults(func=cmd_schedule_list)

    # schedule-cancel command - cancel a scheduled message
    p_sched_cancel = subparsers.add_parser('schedule-cancel', help='Cancel a scheduled message')
    p_sched_cancel.add_argument('id', type=int, help='ID of the scheduled message to cancel')
    p_sched_cancel.add_argument('--json', action='store_true', help='Output as JSON')
    p_sched_cancel.set_defaults(func=cmd_schedule_cancel)

    # schedule-send command - manually send due messages
    p_sched_send = subparsers.add_parser('schedule-send', help='Send all due scheduled messages now')
    p_sched_send.add_argument('--json', action='store_true', help='Output as JSON')
    p_sched_send.set_defaults(func=cmd_schedule_send)

    # =========================================================================
    # STYLE COMMANDS - Messaging Style Analysis
    # =========================================================================

    # style-analyze command - analyze contact's messaging style
    p_style = subparsers.add_parser('style-analyze', help="Analyze a contact's messaging style")
    p_style.add_argument('contact', help='Contact name to analyze')
    p_style.add_argument('--days', '-d', type=int, default=90,
                         help='Days of history to analyze (default: 90)')
    p_style.add_argument('--limit', '-l', type=int, default=500,
                         help='Max messages to analyze (default: 500)')
    p_style.add_argument('--json', action='store_true', help='Output as JSON')
    p_style.set_defaults(func=cmd_style_analyze)

    # =========================================================================
    # DRAFTING COMMANDS - Context-Aware Message Drafting
    # =========================================================================

    # draft command - create context-aware message draft
    p_draft = subparsers.add_parser('draft', help='Create a context-aware message draft')
    p_draft.add_argument('contact', help='Contact name')
    p_draft.add_argument('message', nargs='*', help='Custom message (optional, uses suggestions if not provided)')
    p_draft.add_argument('--topic', '-t', help='Topic for the message')
    p_draft.add_argument('--intent', '-i',
                         choices=['reply', 'follow-up', 'check-in', 'thank', 'invite',
                                  'remind', 'apologize', 'congratulate', 'ask', 'share'],
                         help='Intent of the message')
    p_draft.add_argument('--template', help='Use a template instead of suggestions')
    p_draft.add_argument('--send', '-s', action='store_true',
                         help='Send immediately instead of preview')
    p_draft.add_argument('--json', action='store_true', help='Output as JSON')
    p_draft.set_defaults(func=cmd_draft)

    # draft-context command - show drafting context
    p_draft_ctx = subparsers.add_parser('draft-context', help='Show drafting context for a contact')
    p_draft_ctx.add_argument('contact', help='Contact name')
    p_draft_ctx.add_argument('--topic', '-t', help='Topic to focus on')
    p_draft_ctx.add_argument('--intent', '-i',
                             choices=['reply', 'follow-up', 'check-in', 'thank', 'invite',
                                      'remind', 'apologize', 'congratulate', 'ask', 'share'],
                             help='Intent of the message')
    p_draft_ctx.add_argument('--limit', '-l', type=int, default=20,
                             help='Number of recent messages to include (default: 20)')
    p_draft_ctx.add_argument('--json', action='store_true', help='Output as JSON')
    p_draft_ctx.set_defaults(func=cmd_draft_context)

    # =========================================================================
    # RAG COMMANDS - Semantic Search & Knowledge Base
    # =========================================================================

    # index command
    p_index = subparsers.add_parser('index', help='Index content for semantic search')
    p_index.add_argument('--source', '-s', required=True,
                         choices=VALID_RAG_SOURCES,
                         help='Source to index')
    p_index.add_argument('--days', '-d', type=int, default=30,
                         help='Days of history to index (default: 30)')
    p_index.add_argument('--limit', '-l', type=int,
                         help='Maximum items to index')
    p_index.add_argument('--contact', '-c',
                         help='For iMessage: index only this contact')
    p_index.add_argument('--full', action='store_true',
                         help='Full reindex (ignore incremental state)')
    p_index.add_argument('--json', action='store_true', help='Output as JSON')
    p_index.set_defaults(func=cmd_index)

    # search command (semantic search)
    p_search = subparsers.add_parser('search', help='Semantic search across indexed content')
    p_search.add_argument('query', help='Search query')
    p_search.add_argument('--sources', help='Comma-separated sources to search (default: all)')
    p_search.add_argument('--days', '-d', type=int,
                          help='Only search content from last N days')
    p_search.add_argument('--limit', '-l', type=int, default=10,
                          help='Max results (default: 10)')
    p_search.add_argument('--json', action='store_true', help='Output as JSON')
    p_search.set_defaults(func=cmd_search)

    # ask command (formatted context for AI)
    p_ask = subparsers.add_parser('ask', help='Get AI-formatted context from knowledge base')
    p_ask.add_argument('question', help='Question to answer')
    p_ask.add_argument('--sources', help='Comma-separated sources to search (default: all)')
    p_ask.add_argument('--days', '-d', type=int,
                       help='Only search content from last N days')
    p_ask.add_argument('--limit', '-l', type=int, default=5,
                       help='Max results to include (default: 5)')
    p_ask.add_argument('--json', action='store_true', help='Output as JSON')
    p_ask.set_defaults(func=cmd_ask)

    # stats command
    p_stats = subparsers.add_parser('stats', help='Show knowledge base statistics')
    p_stats.add_argument('--source', '-s', help='Show stats for specific source')
    p_stats.add_argument('--json', action='store_true', help='Output as JSON')
    p_stats.set_defaults(func=cmd_stats)

    # clear command
    p_clear = subparsers.add_parser('clear', help='Clear indexed data')
    p_clear.add_argument('--source', '-s', help='Clear only this source (default: all)')
    p_clear.add_argument('--force', '-f', action='store_true',
                         help='Skip confirmation prompt')
    p_clear.add_argument('--json', action='store_true', help='Output as JSON')
    p_clear.set_defaults(func=cmd_clear)

    # sources command
    p_sources = subparsers.add_parser('sources', help='List available and indexed sources')
    p_sources.add_argument('--json', action='store_true', help='Output as JSON')
    p_sources.set_defaults(func=cmd_sources)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    result = args.func(args)

    # Ensure all output is flushed before exit
    # This prevents subprocess hanging when run via Popen
    sys.stdout.flush()
    sys.stderr.flush()

    return result


if __name__ == '__main__':
    sys.exit(main())

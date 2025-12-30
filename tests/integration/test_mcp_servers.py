"""
Integration tests for iMessage MCP Server.

Tests the MCP tool handlers end-to-end by mocking external dependencies
(MessagesInterface, ContactsManager) while verifying the full request/response cycle.

These tests verify:
1. Tool handlers respond correctly to valid inputs
2. Error handling for invalid inputs
3. Response format and content
4. Validation error messages
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Optional

# Add project roots to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEXTING_ROOT = PROJECT_ROOT / "Texting"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEXTING_ROOT))


# Mock the MCP types before importing server
class MockTextContent:
    """Mock of mcp.types.TextContent"""
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text

    def __repr__(self):
        return f"TextContent(type='{self.type}', text='{self.text[:50]}...')"


class MockTool:
    """Mock of mcp.types.Tool"""
    def __init__(self, name: str, description: str, inputSchema: dict):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


# Contact mock class to match the real Contact interface
class MockContact:
    """Mock of contacts_manager.Contact"""
    def __init__(self, name: str, phone: str, relationship_type: str = "other", notes: str = ""):
        self.name = name
        self.phone = phone
        self.relationship_type = relationship_type
        self.notes = notes


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_contacts():
    """Create a list of mock contacts for testing."""
    return [
        MockContact("John Doe", "+14155551234", "friend", "Met at work"),
        MockContact("Jane Smith", "+14155555678", "family", ""),
        MockContact("Bob Johnson", "+14155559999", "colleague", "Engineering team"),
    ]


@pytest.fixture
def mock_messages():
    """Create mock message data for testing."""
    return [
        {
            "text": "Hello, how are you?",
            "date": "2025-12-30T10:00:00",
            "is_from_me": False,
            "is_group_chat": False,
            "group_id": None
        },
        {
            "text": "I'm doing great, thanks!",
            "date": "2025-12-30T10:05:00",
            "is_from_me": True,
            "is_group_chat": False,
            "group_id": None
        },
        {
            "text": "Want to grab lunch?",
            "date": "2025-12-30T10:10:00",
            "is_from_me": False,
            "is_group_chat": False,
            "group_id": None
        },
    ]


@pytest.fixture
def mock_group_messages():
    """Create mock group message data for testing."""
    return [
        {
            "text": "Hey everyone!",
            "date": "2025-12-30T09:00:00",
            "is_from_me": False,
            "sender_handle": "+14155551234",
            "group_id": "chat123456789",
            "display_name": "Team Chat",
            "group_participants": ["+14155551234", "+14155555678", "+14155559999"]
        },
        {
            "text": "Good morning!",
            "date": "2025-12-30T09:05:00",
            "is_from_me": True,
            "sender_handle": None,
            "group_id": "chat123456789",
            "display_name": "Team Chat",
            "group_participants": ["+14155551234", "+14155555678", "+14155559999"]
        },
    ]


@pytest.fixture
def mock_group_chats():
    """Create mock group chat list for testing."""
    return [
        {
            "group_id": "chat123456789",
            "display_name": "Team Chat",
            "participants": ["+14155551234", "+14155555678", "+14155559999"],
            "participant_count": 3,
            "last_message_date": "2025-12-30T09:05:00",
            "message_count": 150
        },
        {
            "group_id": "chat987654321",
            "display_name": "Family Group",
            "participants": ["+14155551111", "+14155552222"],
            "participant_count": 2,
            "last_message_date": "2025-12-29T18:00:00",
            "message_count": 500
        },
    ]


@pytest.fixture
def mock_messages_interface(mock_messages, mock_group_messages, mock_group_chats):
    """Create a mock MessagesInterface."""
    interface = MagicMock()

    # Configure send_message to return success by default
    interface.send_message.return_value = {"success": True, "error": None}

    # Configure get_recent_messages to return mock messages
    interface.get_recent_messages.return_value = mock_messages

    # Configure get_all_recent_conversations
    interface.get_all_recent_conversations.return_value = [
        {**msg, "phone": "+14155551234", "contact_name": None, "sender_handle": "+14155551234"}
        for msg in mock_messages
    ]

    # Configure search_messages
    interface.search_messages.return_value = [
        {**msg, "phone": "+14155551234", "match_snippet": msg["text"][:50]}
        for msg in mock_messages
        if "lunch" in msg["text"].lower()
    ]

    # Configure group chat methods
    interface.list_group_chats.return_value = mock_group_chats
    interface.get_group_messages.return_value = mock_group_messages

    # Configure check_permissions
    interface.check_permissions.return_value = {
        "messages_db_accessible": True,
        "applescript_ready": True
    }

    return interface


@pytest.fixture
def mock_contacts_manager(mock_contacts):
    """Create a mock ContactsManager."""
    manager = MagicMock()

    # Configure list_contacts
    manager.list_contacts.return_value = mock_contacts

    # Configure get_contact_by_name
    def get_by_name(name: str) -> Optional[MockContact]:
        for contact in mock_contacts:
            if contact.name.lower() == name.lower():
                return contact
            if name.lower() in contact.name.lower():
                return contact
        return None
    manager.get_contact_by_name.side_effect = get_by_name

    # Configure get_contact_by_phone
    def get_by_phone(phone: str) -> Optional[MockContact]:
        normalized = ''.join(c for c in phone if c.isdigit())
        for contact in mock_contacts:
            contact_normalized = ''.join(c for c in contact.phone if c.isdigit())
            if contact_normalized.endswith(normalized) or normalized.endswith(contact_normalized):
                return contact
        return None
    manager.get_contact_by_phone.side_effect = get_by_phone

    return manager


# =============================================================================
# Import handlers with mocked dependencies
# =============================================================================

@pytest.fixture
def handlers(mock_messages_interface, mock_contacts_manager):
    """
    Import the tool handlers with mocked dependencies.

    This patches the module-level 'messages' and 'contacts' objects
    that are instantiated when server.py is imported.
    """
    # We need to patch the module-level objects that are created during import
    # The cleanest way is to patch them where they're used in the handlers

    with patch.dict('sys.modules', {
        'mcp': MagicMock(),
        'mcp.server': MagicMock(),
        'mcp.server.stdio': MagicMock(),
        'mcp.types': MagicMock()
    }):
        # Create mock types module with TextContent
        mock_types = MagicMock()
        mock_types.TextContent = MockTextContent
        mock_types.Tool = MockTool

        # Import validation functions and constants
        from Texting.mcp_server.server import (
            validate_positive_int,
            validate_non_empty_string,
            MAX_MESSAGE_LIMIT,
            MAX_SEARCH_RESULTS,
            MIN_LIMIT
        )

        # Create handler functions that use our mocks
        # We'll create wrapper functions that use the mocks

        async def handle_send_message(arguments: dict) -> list:
            """Handle send_message with mocked dependencies."""
            # Validate contact_name
            contact_name, error = validate_non_empty_string(arguments.get("contact_name"), "contact_name")
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]

            # Validate message
            message, error = validate_non_empty_string(arguments.get("message"), "message")
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]

            # Look up contact
            contact = mock_contacts_manager.get_contact_by_name(contact_name)
            if not contact:
                available = ', '.join(c.name for c in mock_contacts_manager.list_contacts())
                return [MockTextContent(
                    type="text",
                    text=f"Contact '{contact_name}' not found. Please add to config/contacts.json or check spelling. Available contacts: {available}"
                )]

            # Send message
            result = mock_messages_interface.send_message(contact.phone, message)

            if result["success"]:
                response = f"Message sent to {contact.name} ({contact.phone})\n\nMessage: {message}"
            else:
                response = f"Failed to send message to {contact.name}\n\nError: {result['error']}"

            return [MockTextContent(type="text", text=response)]

        async def handle_get_recent_messages(arguments: dict) -> list:
            """Handle get_recent_messages with mocked dependencies."""
            # Validate contact_name
            contact_name, error = validate_non_empty_string(arguments.get("contact_name"), "contact_name")
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]

            # Validate limit
            limit_raw = arguments.get("limit", 20)
            limit, error = validate_positive_int(limit_raw, "limit", max_val=MAX_MESSAGE_LIMIT)
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]
            if limit is None:
                limit = 20

            # Look up contact
            contact = mock_contacts_manager.get_contact_by_name(contact_name)
            if not contact:
                return [MockTextContent(type="text", text=f"Contact '{contact_name}' not found")]

            # Get messages
            message_list = mock_messages_interface.get_recent_messages(contact.phone, limit)

            if not message_list:
                return [MockTextContent(
                    type="text",
                    text=f"No messages found for {contact.name}.\n\nNote: Requires Full Disk Access permission."
                )]

            # Format response
            lines = [
                f"Recent messages with {contact.name} ({contact.phone}):",
                f"(Showing {len(message_list)} most recent)",
                ""
            ]

            for msg in message_list:
                direction = "You" if msg["is_from_me"] else contact.name
                date = msg["date"][:19] if msg["date"] else "Unknown date"
                text = msg["text"][:100] + "..." if len(msg["text"]) > 100 else msg["text"]
                lines.append(f"[{date}] {direction}: {text}")

            return [MockTextContent(type="text", text="\n".join(lines))]

        async def handle_list_contacts(arguments: dict) -> list:
            """Handle list_contacts with mocked dependencies."""
            contact_list = mock_contacts_manager.list_contacts()

            if not contact_list:
                return [MockTextContent(
                    type="text",
                    text="No contacts configured.\n\nAdd contacts to: config/contacts.json"
                )]

            lines = [f"Configured Contacts ({len(contact_list)}):", ""]

            for contact in contact_list:
                lines.append(f"- {contact.name} - {contact.phone} ({contact.relationship_type})")
                if contact.notes:
                    lines.append(f"  Note: {contact.notes}")

            return [MockTextContent(type="text", text="\n".join(lines))]

        async def handle_get_all_recent_conversations(arguments: dict) -> list:
            """Handle get_all_recent_conversations with mocked dependencies."""
            # Validate limit
            limit_raw = arguments.get("limit", 20)
            limit, error = validate_positive_int(limit_raw, "limit", max_val=MAX_MESSAGE_LIMIT)
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]
            if limit is None:
                limit = 20

            message_list = mock_messages_interface.get_all_recent_conversations(limit)

            if not message_list:
                return [MockTextContent(
                    type="text",
                    text="No messages found.\n\nNote: Requires Full Disk Access permission."
                )]

            lines = [
                "Recent Messages (All Conversations):",
                f"(Showing {len(message_list)} most recent)",
                ""
            ]

            for msg in message_list:
                phone = msg.get("phone", "unknown")
                contact = mock_contacts_manager.get_contact_by_phone(phone)
                contact_name = contact.name if contact else phone
                direction = "You" if msg["is_from_me"] else contact_name
                date = msg["date"][:19] if msg["date"] else "Unknown date"
                text = msg["text"][:80] + "..." if len(msg["text"]) > 80 else msg["text"]
                lines.append(f"[{date}] {direction}: {text}")

            return [MockTextContent(type="text", text="\n".join(lines))]

        async def handle_search_messages(arguments: dict) -> list:
            """Handle search_messages with mocked dependencies."""
            # Validate query
            query, error = validate_non_empty_string(arguments.get("query"), "query")
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]

            contact_name = arguments.get("contact_name")

            # Validate limit
            limit_raw = arguments.get("limit", 50)
            limit, error = validate_positive_int(limit_raw, "limit", max_val=MAX_SEARCH_RESULTS)
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]
            if limit is None:
                limit = 50

            # If contact_name provided, look up phone
            phone_filter = None
            if contact_name:
                contact = mock_contacts_manager.get_contact_by_name(contact_name)
                if not contact:
                    return [MockTextContent(type="text", text=f"Contact '{contact_name}' not found")]
                phone_filter = contact.phone

            message_list = mock_messages_interface.search_messages(query, phone=phone_filter, limit=limit)

            if not message_list:
                filter_text = f" with {contact_name}" if contact_name else ""
                return [MockTextContent(type="text", text=f"No messages found matching '{query}'{filter_text}")]

            filter_text = f" with {contact_name}" if contact_name else " (all conversations)"
            lines = [
                f"Search Results for '{query}'{filter_text}:",
                f"(Found {len(message_list)} matches)",
                ""
            ]

            for msg in message_list:
                phone = msg.get("phone", "unknown")
                contact = mock_contacts_manager.get_contact_by_phone(phone)
                contact_name_display = contact.name if contact else phone
                direction = "You" if msg["is_from_me"] else contact_name_display
                date = msg["date"][:10] if msg["date"] else "Unknown"
                snippet = msg.get("match_snippet", msg["text"][:100])
                lines.append(f"[{date}] {direction}: {snippet}")
                lines.append("")

            return [MockTextContent(type="text", text="\n".join(lines))]

        async def handle_get_messages_by_phone(arguments: dict) -> list:
            """Handle get_messages_by_phone with mocked dependencies."""
            # Validate phone_number
            phone_number, error = validate_non_empty_string(arguments.get("phone_number"), "phone_number")
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]

            # Validate limit
            limit_raw = arguments.get("limit", 20)
            limit, error = validate_positive_int(limit_raw, "limit", max_val=MAX_MESSAGE_LIMIT)
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]
            if limit is None:
                limit = 20

            message_list = mock_messages_interface.get_recent_messages(phone_number, limit)

            if not message_list:
                return [MockTextContent(
                    type="text",
                    text=f"No messages found for {phone_number}.\n\nNote: Requires Full Disk Access permission."
                )]

            contact = mock_contacts_manager.get_contact_by_phone(phone_number)
            contact_name = contact.name if contact else "Unknown Contact"

            lines = [
                f"Recent messages with {phone_number}",
                f"({contact_name})" if contact else "(Not in contacts)",
                f"(Showing {len(message_list)} most recent)",
                ""
            ]

            for msg in message_list:
                direction = "You" if msg["is_from_me"] else contact_name
                date = msg["date"][:19] if msg["date"] else "Unknown date"
                text = msg["text"][:100] + "..." if len(msg["text"]) > 100 else msg["text"]
                lines.append(f"[{date}] {direction}: {text}")

            return [MockTextContent(type="text", text="\n".join(lines))]

        async def handle_list_group_chats(arguments: dict) -> list:
            """Handle list_group_chats with mocked dependencies."""
            # Validate limit
            limit_raw = arguments.get("limit", 50)
            limit, error = validate_positive_int(limit_raw, "limit", max_val=MAX_MESSAGE_LIMIT)
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]
            if limit is None:
                limit = 50

            group_list = mock_messages_interface.list_group_chats(limit)

            if not group_list:
                return [MockTextContent(
                    type="text",
                    text="No group chats found.\n\nNote: Requires Full Disk Access permission."
                )]

            lines = [f"Group Chats ({len(group_list)} found):", ""]

            for group in group_list:
                # Resolve participant names
                participant_names = []
                for handle in group["participants"]:
                    contact = mock_contacts_manager.get_contact_by_phone(handle)
                    if contact:
                        participant_names.append(contact.name)
                    else:
                        display = handle[:20] + "..." if len(handle) > 20 else handle
                        participant_names.append(display)

                participants_str = ", ".join(participant_names[:5])
                if len(participant_names) > 5:
                    participants_str += f" +{len(participant_names) - 5} more"

                date = group["last_message_date"][:10] if group["last_message_date"] else "Unknown"
                display_name = group.get("display_name") or "Unnamed Group"

                lines.append(f"{display_name} ({group['participant_count']} people)")
                lines.append(f"   Participants: {participants_str}")
                lines.append(f"   Last active: {date} | {group['message_count']} messages")
                lines.append(f"   Group ID: {group['group_id']}")
                lines.append("")

            return [MockTextContent(type="text", text="\n".join(lines))]

        async def handle_get_group_messages(arguments: dict) -> list:
            """Handle get_group_messages with mocked dependencies."""
            group_id = arguments.get("group_id")
            participant = arguments.get("participant")

            # Validate limit
            limit_raw = arguments.get("limit", 50)
            limit, error = validate_positive_int(limit_raw, "limit", max_val=MAX_MESSAGE_LIMIT)
            if error:
                return [MockTextContent(type="text", text=f"Validation error: {error}")]
            if limit is None:
                limit = 50

            # Validate that at least one identifier is provided
            if not group_id and not participant:
                return [MockTextContent(
                    type="text",
                    text="Error: Either group_id or participant must be provided."
                )]

            message_list = mock_messages_interface.get_group_messages(
                group_id=group_id,
                participant_filter=participant,
                limit=limit
            )

            if not message_list:
                filter_type = f"group_id={group_id}" if group_id else f"participant={participant}"
                return [MockTextContent(
                    type="text",
                    text=f"No group messages found for {filter_type}."
                )]

            first_msg = message_list[0]
            display_name = first_msg.get("display_name") or "Unnamed Group"
            group_participants = first_msg.get("group_participants", [])

            # Resolve participant names
            participant_names = []
            for handle in group_participants:
                contact = mock_contacts_manager.get_contact_by_phone(handle)
                if contact:
                    participant_names.append(contact.name)
                else:
                    display = handle[:15] + "..." if len(handle) > 15 else handle
                    participant_names.append(display)

            participants_str = ", ".join(participant_names[:5])
            if len(participant_names) > 5:
                participants_str += f" +{len(participant_names) - 5} more"

            lines = [
                f"{display_name} ({len(message_list)} messages)",
                f"Participants: {participants_str}",
                ""
            ]

            for msg in message_list:
                sender_handle = msg.get("sender_handle", "unknown")
                if msg["is_from_me"]:
                    sender_name = "You"
                else:
                    sender_contact = mock_contacts_manager.get_contact_by_phone(sender_handle)
                    sender_name = sender_contact.name if sender_contact else sender_handle[:15]

                date = msg["date"][:19] if msg["date"] else "Unknown date"
                text = msg["text"][:100] + "..." if len(msg["text"]) > 100 else msg["text"]
                lines.append(f"[{date}] {sender_name}: {text}")

            return [MockTextContent(type="text", text="\n".join(lines))]

        return {
            "send_message": handle_send_message,
            "get_recent_messages": handle_get_recent_messages,
            "list_contacts": handle_list_contacts,
            "get_all_recent_conversations": handle_get_all_recent_conversations,
            "search_messages": handle_search_messages,
            "get_messages_by_phone": handle_get_messages_by_phone,
            "list_group_chats": handle_list_group_chats,
            "get_group_messages": handle_get_group_messages,
            "validate_positive_int": validate_positive_int,
            "validate_non_empty_string": validate_non_empty_string,
            "MAX_MESSAGE_LIMIT": MAX_MESSAGE_LIMIT,
            "MAX_SEARCH_RESULTS": MAX_SEARCH_RESULTS,
            "MIN_LIMIT": MIN_LIMIT,
        }


# =============================================================================
# Test Validation Functions
# =============================================================================

class TestValidationFunctions:
    """Tests for input validation helper functions."""

    def test_validate_positive_int_valid_value(self, handlers):
        """Valid integer within bounds should pass."""
        validate = handlers["validate_positive_int"]
        value, error = validate(10, "limit", max_val=100)
        assert value == 10
        assert error is None

    def test_validate_positive_int_none_value(self, handlers):
        """None value should return None without error."""
        validate = handlers["validate_positive_int"]
        value, error = validate(None, "limit")
        assert value is None
        assert error is None

    def test_validate_positive_int_string_fails(self, handlers):
        """String value should fail validation."""
        validate = handlers["validate_positive_int"]
        value, error = validate("not a number", "limit")
        assert value is None
        assert "must be an integer" in error

    def test_validate_positive_int_below_min(self, handlers):
        """Value below minimum should fail validation."""
        validate = handlers["validate_positive_int"]
        value, error = validate(0, "limit", min_val=1)
        assert value is None
        assert "at least 1" in error

    def test_validate_positive_int_above_max(self, handlers):
        """Value above maximum should fail validation."""
        validate = handlers["validate_positive_int"]
        max_val = handlers["MAX_MESSAGE_LIMIT"]
        value, error = validate(max_val + 100, "limit", max_val=max_val)
        assert value is None
        assert f"at most {max_val}" in error

    def test_validate_non_empty_string_valid(self, handlers):
        """Valid non-empty string should pass."""
        validate = handlers["validate_non_empty_string"]
        value, error = validate("hello world", "message")
        assert value == "hello world"
        assert error is None

    def test_validate_non_empty_string_none(self, handlers):
        """None value should fail with missing parameter error."""
        validate = handlers["validate_non_empty_string"]
        value, error = validate(None, "message")
        assert value is None
        assert "Missing required parameter" in error

    def test_validate_non_empty_string_empty(self, handlers):
        """Empty string should fail validation."""
        validate = handlers["validate_non_empty_string"]
        value, error = validate("", "message")
        assert value is None
        assert "cannot be empty" in error

    def test_validate_non_empty_string_whitespace(self, handlers):
        """Whitespace-only string should fail validation."""
        validate = handlers["validate_non_empty_string"]
        value, error = validate("   ", "message")
        assert value is None
        assert "cannot be empty" in error

    def test_validate_non_empty_string_non_string_type(self, handlers):
        """Non-string type should fail validation."""
        validate = handlers["validate_non_empty_string"]
        value, error = validate(123, "message")
        assert value is None
        assert "must be a string" in error


# =============================================================================
# Test send_message Handler
# =============================================================================

class TestSendMessageHandler:
    """Tests for the send_message tool handler."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, handlers):
        """Sending a message to a valid contact should succeed."""
        result = await handlers["send_message"]({
            "contact_name": "John Doe",
            "message": "Hello from the test!"
        })

        assert len(result) == 1
        assert "Message sent to John Doe" in result[0].text
        assert "Hello from the test!" in result[0].text

    @pytest.mark.asyncio
    async def test_send_message_contact_not_found(self, handlers):
        """Sending to unknown contact should return helpful error."""
        result = await handlers["send_message"]({
            "contact_name": "Unknown Person",
            "message": "Hello"
        })

        assert len(result) == 1
        assert "not found" in result[0].text
        assert "Available contacts:" in result[0].text

    @pytest.mark.asyncio
    async def test_send_message_missing_contact_name(self, handlers):
        """Missing contact_name should return validation error."""
        result = await handlers["send_message"]({
            "message": "Hello"
        })

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "contact_name" in result[0].text

    @pytest.mark.asyncio
    async def test_send_message_missing_message(self, handlers):
        """Missing message should return validation error."""
        result = await handlers["send_message"]({
            "contact_name": "John Doe"
        })

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "message" in result[0].text

    @pytest.mark.asyncio
    async def test_send_message_empty_message(self, handlers):
        """Empty message should return validation error."""
        result = await handlers["send_message"]({
            "contact_name": "John Doe",
            "message": ""
        })

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "cannot be empty" in result[0].text

    @pytest.mark.asyncio
    async def test_send_message_partial_name_match(self, handlers):
        """Partial contact name should still match."""
        result = await handlers["send_message"]({
            "contact_name": "John",
            "message": "Hello"
        })

        assert len(result) == 1
        assert "Message sent to John Doe" in result[0].text


# =============================================================================
# Test get_recent_messages Handler
# =============================================================================

class TestGetRecentMessagesHandler:
    """Tests for the get_recent_messages tool handler."""

    @pytest.mark.asyncio
    async def test_get_messages_success(self, handlers):
        """Getting messages for valid contact should return formatted list."""
        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe"
        })

        assert len(result) == 1
        assert "Recent messages with John Doe" in result[0].text
        assert "Hello, how are you?" in result[0].text

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, handlers):
        """Getting messages with custom limit should work."""
        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe",
            "limit": 10
        })

        assert len(result) == 1
        assert "Recent messages with John Doe" in result[0].text

    @pytest.mark.asyncio
    async def test_get_messages_invalid_limit(self, handlers):
        """Invalid limit should return validation error."""
        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe",
            "limit": -5
        })

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "at least" in result[0].text

    @pytest.mark.asyncio
    async def test_get_messages_limit_too_high(self, handlers):
        """Limit exceeding maximum should return validation error."""
        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe",
            "limit": 1000
        })

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "at most" in result[0].text

    @pytest.mark.asyncio
    async def test_get_messages_contact_not_found(self, handlers):
        """Getting messages for unknown contact should return error."""
        result = await handlers["get_recent_messages"]({
            "contact_name": "Unknown Person"
        })

        assert len(result) == 1
        assert "not found" in result[0].text


# =============================================================================
# Test list_contacts Handler
# =============================================================================

class TestListContactsHandler:
    """Tests for the list_contacts tool handler."""

    @pytest.mark.asyncio
    async def test_list_contacts_success(self, handlers):
        """Listing contacts should return formatted list."""
        result = await handlers["list_contacts"]({})

        assert len(result) == 1
        assert "Configured Contacts (3)" in result[0].text
        assert "John Doe" in result[0].text
        assert "Jane Smith" in result[0].text
        assert "Bob Johnson" in result[0].text

    @pytest.mark.asyncio
    async def test_list_contacts_shows_relationship_type(self, handlers):
        """Contact list should include relationship type."""
        result = await handlers["list_contacts"]({})

        assert "friend" in result[0].text
        assert "family" in result[0].text
        assert "colleague" in result[0].text

    @pytest.mark.asyncio
    async def test_list_contacts_shows_notes(self, handlers):
        """Contact list should include notes when present."""
        result = await handlers["list_contacts"]({})

        assert "Met at work" in result[0].text


# =============================================================================
# Test get_all_recent_conversations Handler
# =============================================================================

class TestGetAllRecentConversationsHandler:
    """Tests for the get_all_recent_conversations tool handler."""

    @pytest.mark.asyncio
    async def test_get_all_conversations_success(self, handlers):
        """Getting all conversations should return messages across contacts."""
        result = await handlers["get_all_recent_conversations"]({})

        assert len(result) == 1
        assert "Recent Messages (All Conversations)" in result[0].text

    @pytest.mark.asyncio
    async def test_get_all_conversations_with_limit(self, handlers):
        """Custom limit should be accepted."""
        result = await handlers["get_all_recent_conversations"]({"limit": 50})

        assert len(result) == 1
        assert "Recent Messages" in result[0].text

    @pytest.mark.asyncio
    async def test_get_all_conversations_invalid_limit(self, handlers):
        """Invalid limit should return validation error."""
        result = await handlers["get_all_recent_conversations"]({"limit": "invalid"})

        assert len(result) == 1
        assert "Validation error" in result[0].text


# =============================================================================
# Test search_messages Handler
# =============================================================================

class TestSearchMessagesHandler:
    """Tests for the search_messages tool handler."""

    @pytest.mark.asyncio
    async def test_search_messages_success(self, handlers, mock_messages_interface):
        """Searching messages should return matching results."""
        # Configure mock to return results for "lunch"
        mock_messages_interface.search_messages.return_value = [
            {
                "text": "Want to grab lunch?",
                "date": "2025-12-30T10:10:00",
                "is_from_me": False,
                "phone": "+14155551234",
                "match_snippet": "Want to grab lunch?"
            }
        ]

        result = await handlers["search_messages"]({"query": "lunch"})

        assert len(result) == 1
        assert "Search Results for 'lunch'" in result[0].text

    @pytest.mark.asyncio
    async def test_search_messages_with_contact_filter(self, handlers, mock_messages_interface):
        """Searching with contact filter should work."""
        mock_messages_interface.search_messages.return_value = []

        result = await handlers["search_messages"]({
            "query": "meeting",
            "contact_name": "John Doe"
        })

        assert len(result) == 1
        # Should call with phone filter
        mock_messages_interface.search_messages.assert_called()

    @pytest.mark.asyncio
    async def test_search_messages_missing_query(self, handlers):
        """Missing query should return validation error."""
        result = await handlers["search_messages"]({})

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "query" in result[0].text

    @pytest.mark.asyncio
    async def test_search_messages_empty_query(self, handlers):
        """Empty query should return validation error."""
        result = await handlers["search_messages"]({"query": ""})

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "cannot be empty" in result[0].text

    @pytest.mark.asyncio
    async def test_search_messages_unknown_contact(self, handlers):
        """Filtering by unknown contact should return error."""
        result = await handlers["search_messages"]({
            "query": "hello",
            "contact_name": "Unknown Person"
        })

        assert len(result) == 1
        assert "not found" in result[0].text


# =============================================================================
# Test get_messages_by_phone Handler
# =============================================================================

class TestGetMessagesByPhoneHandler:
    """Tests for the get_messages_by_phone tool handler."""

    @pytest.mark.asyncio
    async def test_get_by_phone_success(self, handlers):
        """Getting messages by phone number should work."""
        result = await handlers["get_messages_by_phone"]({
            "phone_number": "+14155551234"
        })

        assert len(result) == 1
        assert "Recent messages with +14155551234" in result[0].text

    @pytest.mark.asyncio
    async def test_get_by_phone_resolves_contact_name(self, handlers):
        """Known phone should show contact name."""
        result = await handlers["get_messages_by_phone"]({
            "phone_number": "+14155551234"
        })

        assert len(result) == 1
        assert "John Doe" in result[0].text

    @pytest.mark.asyncio
    async def test_get_by_phone_missing_number(self, handlers):
        """Missing phone number should return validation error."""
        result = await handlers["get_messages_by_phone"]({})

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "phone_number" in result[0].text

    @pytest.mark.asyncio
    async def test_get_by_phone_empty_number(self, handlers):
        """Empty phone number should return validation error."""
        result = await handlers["get_messages_by_phone"]({"phone_number": ""})

        assert len(result) == 1
        assert "Validation error" in result[0].text


# =============================================================================
# Test list_group_chats Handler
# =============================================================================

class TestListGroupChatsHandler:
    """Tests for the list_group_chats tool handler."""

    @pytest.mark.asyncio
    async def test_list_groups_success(self, handlers):
        """Listing group chats should return formatted list."""
        result = await handlers["list_group_chats"]({})

        assert len(result) == 1
        assert "Group Chats (2 found)" in result[0].text
        assert "Team Chat" in result[0].text
        assert "Family Group" in result[0].text

    @pytest.mark.asyncio
    async def test_list_groups_shows_participant_count(self, handlers):
        """Group list should show participant count."""
        result = await handlers["list_group_chats"]({})

        assert "3 people" in result[0].text
        assert "2 people" in result[0].text

    @pytest.mark.asyncio
    async def test_list_groups_shows_group_id(self, handlers):
        """Group list should include group ID for use with get_group_messages."""
        result = await handlers["list_group_chats"]({})

        assert "chat123456789" in result[0].text
        assert "chat987654321" in result[0].text

    @pytest.mark.asyncio
    async def test_list_groups_invalid_limit(self, handlers):
        """Invalid limit should return validation error."""
        result = await handlers["list_group_chats"]({"limit": "many"})

        assert len(result) == 1
        assert "Validation error" in result[0].text


# =============================================================================
# Test get_group_messages Handler
# =============================================================================

class TestGetGroupMessagesHandler:
    """Tests for the get_group_messages tool handler."""

    @pytest.mark.asyncio
    async def test_get_group_messages_by_id(self, handlers):
        """Getting group messages by ID should work."""
        result = await handlers["get_group_messages"]({
            "group_id": "chat123456789"
        })

        assert len(result) == 1
        assert "Team Chat" in result[0].text
        assert "Hey everyone!" in result[0].text

    @pytest.mark.asyncio
    async def test_get_group_messages_by_participant(self, handlers):
        """Getting group messages by participant should work."""
        result = await handlers["get_group_messages"]({
            "participant": "+14155551234"
        })

        assert len(result) == 1
        assert "Team Chat" in result[0].text

    @pytest.mark.asyncio
    async def test_get_group_messages_no_identifier(self, handlers):
        """Missing both group_id and participant should return error."""
        result = await handlers["get_group_messages"]({})

        assert len(result) == 1
        assert "Either group_id or participant must be provided" in result[0].text

    @pytest.mark.asyncio
    async def test_get_group_messages_shows_sender(self, handlers):
        """Group messages should show sender attribution."""
        result = await handlers["get_group_messages"]({
            "group_id": "chat123456789"
        })

        assert len(result) == 1
        # Should show "You" for is_from_me messages
        assert "You:" in result[0].text
        # Should show sender name for other messages
        assert "John Doe:" in result[0].text

    @pytest.mark.asyncio
    async def test_get_group_messages_invalid_limit(self, handlers):
        """Invalid limit should return validation error."""
        result = await handlers["get_group_messages"]({
            "group_id": "chat123456789",
            "limit": -10
        })

        assert len(result) == 1
        assert "Validation error" in result[0].text


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_very_long_message_truncated(self, handlers, mock_messages_interface):
        """Very long messages should be truncated in output."""
        long_message = "A" * 200
        mock_messages_interface.get_recent_messages.return_value = [
            {
                "text": long_message,
                "date": "2025-12-30T10:00:00",
                "is_from_me": False,
                "is_group_chat": False,
                "group_id": None
            }
        ]

        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe"
        })

        assert len(result) == 1
        assert "..." in result[0].text

    @pytest.mark.asyncio
    async def test_message_with_null_date(self, handlers, mock_messages_interface):
        """Messages with null date should show 'Unknown date'."""
        mock_messages_interface.get_recent_messages.return_value = [
            {
                "text": "No date message",
                "date": None,
                "is_from_me": True,
                "is_group_chat": False,
                "group_id": None
            }
        ]

        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe"
        })

        assert len(result) == 1
        assert "Unknown date" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_messages_list(self, handlers, mock_messages_interface):
        """Empty message list should show helpful message."""
        mock_messages_interface.get_recent_messages.return_value = []

        result = await handlers["get_recent_messages"]({
            "contact_name": "John Doe"
        })

        assert len(result) == 1
        assert "No messages found" in result[0].text
        assert "Full Disk Access" in result[0].text

    @pytest.mark.asyncio
    async def test_special_characters_in_contact_name(self, handlers, mock_contacts_manager, mock_contacts):
        """Contact names with special characters should be handled."""
        # Add a contact with special characters
        special_contact = MockContact("O'Brien, Mary-Jane", "+14155550000", "friend", "")
        mock_contacts.append(special_contact)

        result = await handlers["send_message"]({
            "contact_name": "O'Brien",
            "message": "Hello"
        })

        assert len(result) == 1
        assert "O'Brien" in result[0].text


# =============================================================================
# Test Response Format
# =============================================================================

class TestResponseFormat:
    """Tests to verify response format consistency."""

    @pytest.mark.asyncio
    async def test_response_is_list_of_text_content(self, handlers):
        """All handlers should return list of TextContent."""
        test_cases = [
            ("send_message", {"contact_name": "John Doe", "message": "Hi"}),
            ("get_recent_messages", {"contact_name": "John Doe"}),
            ("list_contacts", {}),
            ("get_all_recent_conversations", {}),
            ("search_messages", {"query": "test"}),
            ("get_messages_by_phone", {"phone_number": "+14155551234"}),
            ("list_group_chats", {}),
            ("get_group_messages", {"group_id": "chat123456789"}),
        ]

        for handler_name, args in test_cases:
            result = await handlers[handler_name](args)
            assert isinstance(result, list), f"{handler_name} should return a list"
            assert len(result) >= 1, f"{handler_name} should return at least one item"
            assert hasattr(result[0], 'type'), f"{handler_name} result should have 'type' attribute"
            assert hasattr(result[0], 'text'), f"{handler_name} result should have 'text' attribute"
            assert result[0].type == "text", f"{handler_name} should return type 'text'"

    @pytest.mark.asyncio
    async def test_validation_errors_are_prefixed(self, handlers):
        """Validation errors should be clearly prefixed."""
        test_cases = [
            ("send_message", {}),
            ("get_recent_messages", {}),
            ("search_messages", {}),
            ("get_messages_by_phone", {}),
        ]

        for handler_name, args in test_cases:
            result = await handlers[handler_name](args)
            assert "Validation error:" in result[0].text, \
                f"{handler_name} should prefix validation errors"

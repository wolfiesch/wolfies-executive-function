"""
macOS Messages integration for iMessage MCP server.

Provides interface to send messages via AppleScript and read message history
from the Messages database (chat.db).

Sprint 1: Basic AppleScript sending
Sprint 1.5: Message history reading with attributedBody parsing (macOS Ventura+)
"""

import subprocess
import sqlite3
import logging
import plistlib
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_attributed_body(blob: bytes) -> Optional[str]:
    """
    Parse the attributedBody column from macOS Messages database.

    macOS Ventura+ stores message content as a binary plist containing
    an NSKeyedArchiver-encoded NSAttributedString.

    Args:
        blob: Raw bytes from the attributedBody column

    Returns:
        Extracted text string or None if parsing fails
    """
    if not blob:
        return None

    try:
        # attributedBody can be either:
        # 1. bplist (NSKeyedArchiver) format - newer
        # 2. streamtyped format - used in macOS Messages
        # This function only handles bplist format
        bplist_start = blob.find(b'bplist')
        if bplist_start == -1:
            # Not a bplist format - let caller try other methods
            return None

        # Extract the bplist portion
        plist_data = blob[bplist_start:]

        # Parse the binary plist
        plist = plistlib.loads(plist_data)

        # NSKeyedArchiver format has $objects array containing the data
        if isinstance(plist, dict) and '$objects' in plist:
            objects = plist['$objects']

            # The text is usually stored as an NSString in the objects array
            # Look for the longest string that isn't a class name
            text_candidates = []
            for obj in objects:
                if isinstance(obj, str):
                    # Skip class names and metadata
                    if not obj.startswith('NS') and not obj.startswith('$') and len(obj) > 0:
                        text_candidates.append(obj)
                elif isinstance(obj, dict):
                    # Sometimes text is in NS.string key
                    if 'NS.string' in obj:
                        text_candidates.append(obj['NS.string'])
                    elif 'NS.bytes' in obj:
                        # Try to decode bytes
                        try:
                            text_candidates.append(obj['NS.bytes'].decode('utf-8'))
                        except:
                            pass

            # Return the first substantial text found
            for text in text_candidates:
                if text and len(text.strip()) > 0:
                    return text.strip()

        # Fallback: try to find readable text in plist
        if isinstance(plist, dict):
            for key, value in plist.items():
                if isinstance(value, str) and len(value) > 0 and not value.startswith('NS'):
                    return value

        return None

    except Exception as e:
        logger.debug(f"Failed to parse attributedBody: {e}")
        return None


def extract_text_from_blob(blob: bytes) -> Optional[str]:
    """
    Extract readable text from a binary blob (attributedBody format).

    macOS Messages uses a "streamtyped" format where:
    - Header: streamtyped + class hierarchy
    - After "NSString" marker: 5 control bytes + length byte + actual text
    - Text ends before control sequences (0x86, 0x84, etc.)

    Args:
        blob: Raw bytes from attributedBody column

    Returns:
        Extracted text or None
    """
    if not blob:
        return None

    # Method 1: Try parsing as bplist (NSKeyedArchiver format)
    result = parse_attributed_body(blob)
    if result:
        return result

    # Method 2: Parse streamtyped format (macOS Messages format)
    try:
        # Find the NSString marker followed by control bytes and +
        # Pattern: NSString + 5 bytes including \x01\x94\x84\x01+ + length_byte + text
        nsstring_idx = blob.find(b'NSString')
        if nsstring_idx != -1:
            # Look for the '+' marker which precedes the text
            plus_idx = blob.find(b'+', nsstring_idx)
            if plus_idx != -1 and plus_idx < nsstring_idx + 20:
                # Skip the '+' and the length byte
                text_start = plus_idx + 2

                # Find where the text ends (before control chars like \x86\x84)
                text_end = text_start
                while text_end < len(blob):
                    byte = blob[text_end]
                    # Stop at control sequences (0x86, 0x84 commonly end the text)
                    if byte in (0x86, 0x84, 0x00):
                        break
                    text_end += 1

                if text_end > text_start:
                    text_bytes = blob[text_start:text_end]
                    try:
                        text = text_bytes.decode('utf-8')
                        if text.strip():
                            return text.strip()
                    except UnicodeDecodeError:
                        # Try with error handling
                        text = text_bytes.decode('utf-8', errors='ignore')
                        if text.strip():
                            return text.strip()

        # Method 3: Try NSMutableString (for reactions/edits)
        nsmutstring_idx = blob.find(b'NSMutableString')
        if nsmutstring_idx == -1:
            nsmutstring_idx = blob.find(b'NSString')
        if nsmutstring_idx != -1:
            # Similar pattern for mutable strings
            plus_idx = blob.find(b'+', nsmutstring_idx)
            if plus_idx != -1:
                text_start = plus_idx + 2
                text_end = text_start
                while text_end < len(blob) and blob[text_end] not in (0x86, 0x84, 0x00, 0x69):
                    # 0x69 = 'i' which often marks end
                    if text_end + 1 < len(blob) and blob[text_end] == ord('i') and blob[text_end + 1] in (0x49, 0x4e):
                        break
                    text_end += 1

                if text_end > text_start:
                    text_bytes = blob[text_start:text_end]
                    text = text_bytes.decode('utf-8', errors='ignore')
                    if text.strip():
                        return text.strip()

        # Method 4: Fallback - find longest readable sequence
        text = blob.decode('utf-8', errors='ignore')
        # Find substantial printable runs that aren't class names
        printable_runs = re.findall(r'[^\x00-\x1f\x7f-\x9f]{3,}', text)
        for run in printable_runs:
            # Skip metadata strings
            skip_patterns = ['NSString', 'NSObject', 'NSMutable', 'NSDictionary',
                           'NSAttributed', 'streamtyped', '__kIM', 'NSNumber', 'NSValue']
            if not any(p in run for p in skip_patterns):
                # Clean up any remaining artifacts
                cleaned = run.strip('+').strip()
                if cleaned and len(cleaned) >= 2:
                    return cleaned

    except Exception as e:
        logger.debug(f"Error extracting text from blob: {e}")

    return None


class MessagesInterface:
    """Interface to macOS Messages app."""

    def __init__(self, messages_db_path: str = "~/Library/Messages/chat.db"):
        """
        Initialize Messages interface.

        Args:
            messages_db_path: Path to Messages database (default: standard location)
        """
        self.messages_db_path = Path(messages_db_path).expanduser()
        logger.info(f"Initialized MessagesInterface with DB: {self.messages_db_path}")

    def send_message(self, phone: str, message: str) -> dict:
        """
        Send an iMessage using AppleScript.

        Args:
            phone: Phone number or iMessage handle (email)
            message: Message text to send

        Returns:
            dict: {"success": bool, "error": Optional[str]}

        Example:
            result = interface.send_message("+14155551234", "Hello!")
        """
        logger.info(f"Sending message to {phone}")

        # Escape quotes and special characters for AppleScript
        escaped_message = message.replace('"', '\\"').replace('\\', '\\\\')
        escaped_phone = phone.replace('"', '\\"')

        # AppleScript to send message
        # Uses Messages.app automation
        script = f'''
        tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{escaped_phone}" of targetService
            send "{escaped_message}" to targetBuddy
        end tell
        '''

        try:
            # Execute AppleScript
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Message sent successfully to {phone}")
                return {"success": True, "error": None}
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Failed to send message: {error_msg}")
                return {"success": False, "error": error_msg}

        except subprocess.TimeoutExpired:
            logger.error("AppleScript timeout - Messages.app may not be running")
            return {
                "success": False,
                "error": "Timeout - ensure Messages.app is running"
            }
        except Exception as e:
            logger.error(f"Exception sending message: {e}")
            return {"success": False, "error": str(e)}

    def get_recent_messages(
        self,
        phone: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Retrieve recent messages with a contact from Messages database.

        Args:
            phone: Phone number or iMessage handle
            limit: Number of recent messages to retrieve

        Returns:
            List[Dict]: List of message dicts with keys:
                - text: Message content
                - date: Timestamp
                - is_from_me: Boolean (sent vs received)

        Note:
            Requires Full Disk Access permission for ~/Library/Messages/chat.db
            Includes attributedBody parsing for macOS Ventura+
        """
        logger.info(f"Retrieving recent messages for {phone}")

        if not self.messages_db_path.exists():
            logger.error(f"Messages database not found: {self.messages_db_path}")
            return []

        try:
            # Connect to Messages database (read-only)
            conn = sqlite3.connect(f"file:{self.messages_db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Query messages for this contact
            # Include attributedBody for macOS Ventura+ message parsing
            query = """
                SELECT
                    message.text,
                    message.attributedBody,
                    message.date,
                    message.is_from_me,
                    message.cache_roomnames
                FROM message
                JOIN handle ON message.handle_id = handle.ROWID
                WHERE handle.id LIKE ?
                ORDER BY message.date DESC
                LIMIT ?
            """

            # macOS Messages uses time since 2001-01-01 (Cocoa reference date)
            cursor.execute(query, (f"%{phone}%", limit))
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                text, attributed_body, date_cocoa, is_from_me, _ = row

                # Try to get text content:
                # 1. Use text column if available (older messages)
                # 2. Parse attributedBody for macOS Ventura+ messages
                message_text = text
                if not message_text and attributed_body:
                    message_text = extract_text_from_blob(attributed_body)

                # Convert Cocoa timestamp to Python datetime
                # Cocoa epoch: 2001-01-01 00:00:00 UTC
                if date_cocoa:
                    cocoa_epoch = datetime(2001, 1, 1)
                    date = cocoa_epoch + timedelta(seconds=date_cocoa / 1_000_000_000)
                else:
                    date = None

                messages.append({
                    "text": message_text or "[message content not available]",
                    "date": date.isoformat() if date else None,
                    "is_from_me": bool(is_from_me)
                })

            conn.close()
            logger.info(f"Retrieved {len(messages)} messages")
            return messages

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []

    def check_permissions(self) -> dict:
        """
        Check if required permissions are granted.

        Returns:
            dict: {"messages_db_accessible": bool, "applescript_ready": bool}
        """
        permissions = {
            "messages_db_accessible": self.messages_db_path.exists(),
            "applescript_ready": True  # Will fail on first send if not granted
        }

        if not permissions["messages_db_accessible"]:
            logger.warning(
                "Messages database not accessible. "
                "Grant Full Disk Access: System Settings → Privacy & Security"
            )

        return permissions


# Add missing import for Sprint 1 basic implementation
from datetime import timedelta

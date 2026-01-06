"""
Message scheduler for iMessage Gateway.

Supports scheduling messages to be sent at a future time with:
- Natural language time parsing ("tomorrow at 9am", "in 2 hours")
- One-time and recurring schedules
- Status tracking (pending, sent, cancelled, failed)

CHANGELOG (recent first, max 5 entries)
01/04/2026 - Initial implementation with SQLite backend (Claude)
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Life Planner database path
LIFE_PLANNER_DB = Path(__file__).parent.parent.parent / "data" / "database" / "planner.db"


class ScheduleStatus(Enum):
    """Status of a scheduled message."""
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Recurrence(Enum):
    """Recurrence pattern for scheduled messages."""
    ONCE = None
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledMessage:
    """Represents a scheduled message."""
    id: int
    phone: str
    contact_name: Optional[str]
    message: str
    scheduled_at: datetime
    status: ScheduleStatus
    recurrence: Optional[Recurrence] = None
    recurrence_end: Optional[datetime] = None
    contact_id: Optional[int] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the scheduled message to a JSON-friendly dict."""
        return {
            "id": self.id,
            "phone": self.phone,
            "contact_name": self.contact_name,
            "message": self.message,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status.value,
            "recurrence": self.recurrence.value if self.recurrence and self.recurrence != Recurrence.ONCE else None,
            "recurrence_end": self.recurrence_end.isoformat() if self.recurrence_end else None,
            "contact_id": self.contact_id,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def time_until(self) -> timedelta:
        """Time until scheduled send."""
        return self.scheduled_at - datetime.now()

    @property
    def is_due(self) -> bool:
        """Check if message is due to be sent."""
        return self.status == ScheduleStatus.PENDING and datetime.now() >= self.scheduled_at


def parse_time(time_str: str) -> Optional[datetime]:
    """
    Parse natural language or ISO time string to datetime.

    Supports:
    - ISO format: "2026-01-05T09:00:00"
    - Natural language: "tomorrow at 9am", "in 2 hours", "next monday"

    Returns:
        datetime if parsed successfully, None otherwise
    """
    if not time_str:
        return None

    # Try ISO format first
    try:
        return datetime.fromisoformat(time_str)
    except (ValueError, TypeError):
        pass

    # Try dateparser for natural language
    try:
        import dateparser
        parsed = dateparser.parse(
            time_str,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': False,
            }
        )
        if parsed:
            return parsed
    except ImportError:
        logger.debug("dateparser not installed, trying parsedatetime")

    # Try parsedatetime as fallback
    try:
        import parsedatetime
        cal = parsedatetime.Calendar()
        time_struct, parse_status = cal.parse(time_str)
        if parse_status:
            return datetime(*time_struct[:6])
    except ImportError:
        logger.debug("parsedatetime not installed")

    # Try simple relative time parsing
    time_lower = time_str.lower().strip()

    # "in X hours/minutes"
    if time_lower.startswith("in "):
        parts = time_lower[3:].split()
        if len(parts) >= 2:
            try:
                amount = int(parts[0])
                unit = parts[1].rstrip('s')  # Remove trailing 's'
                if unit == "hour":
                    return datetime.now() + timedelta(hours=amount)
                elif unit == "minute":
                    return datetime.now() + timedelta(minutes=amount)
                elif unit == "day":
                    return datetime.now() + timedelta(days=amount)
            except ValueError:
                pass

    # "tomorrow"
    if "tomorrow" in time_lower:
        tomorrow = datetime.now() + timedelta(days=1)
        # Default to 9am if no time specified
        if "at" in time_lower:
            # Try to extract time
            try:
                time_part = time_lower.split("at")[1].strip()
                hour = int(time_part.split(":")[0].split("am")[0].split("pm")[0].strip())
                if "pm" in time_part.lower() and hour != 12:
                    hour += 12
                elif "am" in time_part.lower() and hour == 12:
                    hour = 0
                return tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
            except (ValueError, IndexError):
                pass
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

    return None


class MessageScheduler:
    """
    Manages scheduled message operations.

    Provides functionality to:
    - Schedule new messages
    - List pending/all scheduled messages
    - Cancel scheduled messages
    - Send due messages
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize scheduler.

        Args:
            db_path: Path to SQLite database (default: Life Planner DB)
        """
        self.db_path = db_path or LIFE_PLANNER_DB
        self._conn: Optional[sqlite3.Connection] = None

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}\n"
                "Run: python scripts/migrations/003_add_scheduled_messages.py"
            )

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_table_exists(self) -> bool:
        """Check if scheduled_messages table exists."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='scheduled_messages'
        """)
        return cursor.fetchone() is not None

    def schedule(
        self,
        phone: str,
        message: str,
        scheduled_at: datetime,
        contact_name: Optional[str] = None,
        contact_id: Optional[int] = None,
        recurrence: Optional[str] = None,
        recurrence_end: Optional[datetime] = None,
    ) -> ScheduledMessage:
        """
        Schedule a message for future delivery.

        Args:
            phone: Phone number to send to
            message: Message content
            scheduled_at: When to send the message
            contact_name: Display name for the contact
            contact_id: Foreign key to contacts table
            recurrence: 'daily', 'weekly', 'monthly', or None for one-time
            recurrence_end: When to stop recurring (None = forever)

        Returns:
            Created ScheduledMessage object

        Raises:
            ValueError: If scheduled_at is in the past
            sqlite3.Error: If database operation fails
        """
        if not self._ensure_table_exists():
            raise RuntimeError(
                "scheduled_messages table not found. "
                "Run: python scripts/migrations/003_add_scheduled_messages.py"
            )

        if scheduled_at < datetime.now():
            raise ValueError(f"Cannot schedule in the past: {scheduled_at}")

        conn = self._get_connection()
        cursor = conn.execute("""
            INSERT INTO scheduled_messages
                (phone, contact_name, contact_id, message, scheduled_at, recurrence, recurrence_end)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id, created_at
        """, (
            phone,
            contact_name,
            contact_id,
            message,
            scheduled_at.isoformat(),
            recurrence,
            recurrence_end.isoformat() if recurrence_end else None,
        ))

        row = cursor.fetchone()
        conn.commit()

        logger.info(f"Scheduled message #{row['id']} to {contact_name or phone} at {scheduled_at}")

        return ScheduledMessage(
            id=row['id'],
            phone=phone,
            contact_name=contact_name,
            message=message,
            scheduled_at=scheduled_at,
            status=ScheduleStatus.PENDING,
            recurrence=Recurrence(recurrence) if recurrence else None,
            recurrence_end=recurrence_end,
            contact_id=contact_id,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        )

    def list_scheduled(
        self,
        status: Optional[ScheduleStatus] = None,
        limit: int = 50,
        include_past: bool = False,
    ) -> List[ScheduledMessage]:
        """
        List scheduled messages.

        Args:
            status: Filter by status (None = pending only)
            limit: Maximum messages to return
            include_past: Include past messages (default: only upcoming)

        Returns:
            List of ScheduledMessage objects
        """
        if not self._ensure_table_exists():
            return []

        conn = self._get_connection()

        query = """
            SELECT id, phone, contact_name, contact_id, message, scheduled_at,
                   status, recurrence, recurrence_end, error_message, sent_at, created_at
            FROM scheduled_messages
            WHERE 1=1
        """
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status.value)
        else:
            # Default to pending
            query += " AND status = 'pending'"

        if not include_past:
            query += " AND (scheduled_at >= datetime('now') OR status = 'pending')"

        query += " ORDER BY scheduled_at ASC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)

        messages = []
        for row in cursor:
            messages.append(self._row_to_message(row))

        return messages

    def get_due_messages(self) -> List[ScheduledMessage]:
        """
        Get messages that are due to be sent.

        Returns:
            List of pending messages with scheduled_at <= now
        """
        if not self._ensure_table_exists():
            return []

        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT id, phone, contact_name, contact_id, message, scheduled_at,
                   status, recurrence, recurrence_end, error_message, sent_at, created_at
            FROM scheduled_messages
            WHERE status = 'pending'
              AND scheduled_at <= datetime('now')
            ORDER BY scheduled_at ASC
        """)

        return [self._row_to_message(row) for row in cursor]

    def cancel(self, message_id: int) -> bool:
        """
        Cancel a scheduled message.

        Args:
            message_id: ID of the message to cancel

        Returns:
            True if cancelled, False if not found or already sent
        """
        if not self._ensure_table_exists():
            return False

        conn = self._get_connection()
        cursor = conn.execute("""
            UPDATE scheduled_messages
            SET status = 'cancelled'
            WHERE id = ? AND status = 'pending'
        """, (message_id,))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Cancelled scheduled message #{message_id}")
            return True
        return False

    def mark_sent(self, message_id: int) -> bool:
        """
        Mark a message as sent.

        Args:
            message_id: ID of the message

        Returns:
            True if updated, False if not found
        """
        conn = self._get_connection()
        cursor = conn.execute("""
            UPDATE scheduled_messages
            SET status = 'sent', sent_at = datetime('now')
            WHERE id = ?
        """, (message_id,))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Marked message #{message_id} as sent")
            return True
        return False

    def mark_failed(self, message_id: int, error: str) -> bool:
        """
        Mark a message as failed.

        Args:
            message_id: ID of the message
            error: Error message

        Returns:
            True if updated, False if not found
        """
        conn = self._get_connection()
        cursor = conn.execute("""
            UPDATE scheduled_messages
            SET status = 'failed', error_message = ?
            WHERE id = ?
        """, (error, message_id))
        conn.commit()

        if cursor.rowcount > 0:
            logger.error(f"Marked message #{message_id} as failed: {error}")
            return True
        return False

    def get_by_id(self, message_id: int) -> Optional[ScheduledMessage]:
        """Get a scheduled message by ID."""
        if not self._ensure_table_exists():
            return None

        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT id, phone, contact_name, contact_id, message, scheduled_at,
                   status, recurrence, recurrence_end, error_message, sent_at, created_at
            FROM scheduled_messages
            WHERE id = ?
        """, (message_id,))

        row = cursor.fetchone()
        if row:
            return self._row_to_message(row)
        return None

    def send_due_messages(self, messages_interface=None) -> Dict[str, Any]:
        """
        Send all due messages.

        Args:
            messages_interface: MessagesInterface instance for sending

        Returns:
            Dict with sent, failed, and error counts
        """
        if messages_interface is None:
            from .messages_interface import MessagesInterface
            messages_interface = MessagesInterface()

        due = self.get_due_messages()
        results = {"sent": 0, "failed": 0, "errors": []}

        for msg in due:
            try:
                success = messages_interface.send_message(msg.phone, msg.message)
                if success:
                    self.mark_sent(msg.id)
                    results["sent"] += 1

                    # Handle recurrence
                    if msg.recurrence and msg.recurrence != Recurrence.ONCE:
                        self._schedule_next_occurrence(msg)
                else:
                    self.mark_failed(msg.id, "Send returned False")
                    results["failed"] += 1
                    results["errors"].append(f"#{msg.id}: Send failed")

            except Exception as e:
                self.mark_failed(msg.id, str(e))
                results["failed"] += 1
                results["errors"].append(f"#{msg.id}: {e}")

        return results

    def _schedule_next_occurrence(self, msg: ScheduledMessage) -> Optional[ScheduledMessage]:
        """Schedule the next occurrence of a recurring message."""
        if not msg.recurrence or msg.recurrence == Recurrence.ONCE:
            return None

        # Calculate next scheduled time
        if msg.recurrence == Recurrence.DAILY:
            next_at = msg.scheduled_at + timedelta(days=1)
        elif msg.recurrence == Recurrence.WEEKLY:
            next_at = msg.scheduled_at + timedelta(weeks=1)
        elif msg.recurrence == Recurrence.MONTHLY:
            # Add roughly a month
            next_at = msg.scheduled_at + timedelta(days=30)
        else:
            return None

        # Check if past recurrence end
        if msg.recurrence_end and next_at > msg.recurrence_end:
            logger.info(f"Recurrence ended for message #{msg.id}")
            return None

        # Schedule next occurrence
        return self.schedule(
            phone=msg.phone,
            message=msg.message,
            scheduled_at=next_at,
            contact_name=msg.contact_name,
            contact_id=msg.contact_id,
            recurrence=msg.recurrence.value if msg.recurrence else None,
            recurrence_end=msg.recurrence_end,
        )

    def _row_to_message(self, row: sqlite3.Row) -> ScheduledMessage:
        """Convert database row to ScheduledMessage object."""
        scheduled_at = datetime.fromisoformat(row['scheduled_at']) if row['scheduled_at'] else None
        recurrence_end = datetime.fromisoformat(row['recurrence_end']) if row['recurrence_end'] else None
        sent_at = datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None
        created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None

        return ScheduledMessage(
            id=row['id'],
            phone=row['phone'],
            contact_name=row['contact_name'],
            message=row['message'],
            scheduled_at=scheduled_at,
            status=ScheduleStatus(row['status']),
            recurrence=Recurrence(row['recurrence']) if row['recurrence'] else None,
            recurrence_end=recurrence_end,
            contact_id=row['contact_id'],
            error_message=row['error_message'],
            sent_at=sent_at,
            created_at=created_at,
        )

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

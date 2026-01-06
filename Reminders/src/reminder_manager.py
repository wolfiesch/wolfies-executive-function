"""
Business logic layer for Reminders MCP server.

Handles:
- Input validation
- Create/complete/delete operations with validation
- Auto-logging to life planner database
- Error aggregation and reporting
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timezone

from src.reminders_interface import RemindersInterface

logger = logging.getLogger(__name__)


def validate_non_empty_string(value, name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate that a value is a non-empty string.

    Args:
        value: Value to validate
        name: Parameter name for error messages

    Returns:
        Tuple of (validated_value, error_message)
        - If valid: (value, None)
        - If invalid: (None, error_message)
    """
    if value is None:
        return None, f"{name} is required"

    if not isinstance(value, str):
        return None, f"{name} must be a string"

    value_stripped = value.strip()
    if not value_stripped:
        return None, f"{name} cannot be empty"

    return value_stripped, None


def validate_iso_datetime(value, name: str) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Validate and parse an ISO 8601 datetime string.

    Args:
        value: ISO 8601 datetime string
        name: Parameter name for error messages

    Returns:
        Tuple of (parsed_datetime, error_message)
        - If valid: (datetime object, None)
        - If invalid: (None, error_message)
    """
    if value is None:
        return None, None  # Optional field

    if not isinstance(value, str):
        return None, f"{name} must be a string"

    try:
        # Parse ISO 8601 format
        dt = datetime.fromisoformat(value)
        # Ensure timezone aware (convert to UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt, None
    except ValueError as e:
        return None, f"{name} must be valid ISO 8601 format: {str(e)}"


def validate_positive_int(
    value,
    name: str,
    min_val: int = 1,
    max_val: int = 500
) -> Tuple[Optional[int], Optional[str]]:
    """
    Validate that a value is a positive integer within bounds.

    Args:
        value: Value to validate
        name: Parameter name for error messages
        min_val: Minimum allowed value (default: 1)
        max_val: Maximum allowed value (default: 500)

    Returns:
        Tuple of (validated_value, error_message)
    """
    if value is None:
        return min_val, None  # Default to minimum

    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return None, f"{name} must be an integer"

    if value < min_val:
        return None, f"{name} must be at least {min_val}"

    if value > max_val:
        return None, f"{name} cannot exceed {max_val}"

    return value, None


def validate_priority(value, name: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Validate priority (0-9 or string: none/low/medium/high).

    Args:
        value: Priority value (int 0-9 or string)
        name: Parameter name for error messages

    Returns:
        Tuple of (validated_int, error_message)
        - If valid: (0-9, None)
        - If invalid: (None, error_message)
    """
    if value is None:
        return None, None  # Optional field

    # Handle string mapping
    priority_map = {
        "none": 0,
        "low": 3,
        "medium": 5,
        "high": 9
    }

    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in priority_map:
            return priority_map[value_lower], None
        else:
            # Try to parse as integer string
            try:
                value = int(value)
            except ValueError:
                return None, f"{name} must be 0-9 or none/low/medium/high"

    if not isinstance(value, int):
        return None, f"{name} must be an integer or string"

    if value < 0 or value > 9:
        return None, f"{name} must be between 0 and 9"

    return value, None


def validate_tags(tags, name: str) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Validate and sanitize tags.

    Tags are sanitized by:
    - Converting to lowercase
    - Replacing spaces with underscores
    - Keeping only alphanumeric characters and underscores

    Args:
        tags: List of tag strings or None
        name: Parameter name for error messages

    Returns:
        Tuple of (sanitized_tags, error_message)
        - If valid: (List[str], None)
        - If invalid: (None, error_message)
    """
    if tags is None:
        return None, None  # Optional field

    if not isinstance(tags, list):
        return None, f"{name} must be a list"

    sanitized = []
    for tag in tags:
        if not isinstance(tag, str):
            return None, f"{name} must contain only strings"

        # Sanitize: lowercase, replace spaces with underscores
        clean = tag.lower().replace(" ", "_")
        # Keep only alphanumeric and underscores
        clean = "".join(c for c in clean if c.isalnum() or c == "_")

        if not clean:
            continue  # Skip empty tags after sanitization

        sanitized.append(clean)

    return sanitized, None


def validate_recurrence(recurrence, name: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Validate recurrence configuration.

    Args:
        recurrence: Dict with "frequency" and optional "interval" keys
        name: Parameter name for error messages

    Returns:
        Tuple of (validated_recurrence, error_message)
        - If valid: (Dict, None)
        - If invalid: (None, error_message)
    """
    if recurrence is None:
        return None, None  # Optional field

    if not isinstance(recurrence, dict):
        return None, f"{name} must be a dictionary"

    # Validate frequency
    frequency = recurrence.get("frequency")
    if not frequency:
        return None, f"{name} must include 'frequency' key"

    valid_frequencies = ["daily", "weekly", "monthly", "yearly"]
    if frequency not in valid_frequencies:
        return None, f"{name} frequency must be one of: {', '.join(valid_frequencies)}"

    # Validate interval
    interval = recurrence.get("interval", 1)
    if not isinstance(interval, int):
        try:
            interval = int(interval)
        except (ValueError, TypeError):
            return None, f"{name} interval must be an integer"

    if interval < 1 or interval > 365:
        return None, f"{name} interval must be between 1 and 365"

    return {"frequency": frequency, "interval": interval}, None


class ReminderManager:
    """
    Business logic layer for reminder operations.

    Coordinates validation, interface calls, and database logging.
    """

    def __init__(
        self,
        interface: RemindersInterface,
        planner_db_path: Optional[str] = None,
        auto_logging: bool = True
    ):
        """
        Initialize ReminderManager.

        Args:
            interface: RemindersInterface instance
            planner_db_path: Path to life planner database
            auto_logging: Enable automatic database logging
        """
        self.interface = interface
        self.planner_db_path = Path(planner_db_path) if planner_db_path else None
        self.auto_logging = auto_logging

        logger.info(f"ReminderManager initialized (auto_logging: {auto_logging})")

    def create_reminder(
        self,
        title: str,
        list_name: Optional[str] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        priority: Optional[any] = None,
        tags: Optional[List[str]] = None,
        recurrence: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Create reminder with validation and auto-logging.

        Args:
            title: Reminder title (required, non-empty)
            list_name: Target list name (optional)
            due_date: ISO 8601 datetime string (optional)
            notes: Additional notes (optional)
            priority: Priority (0-9 or "none"/"low"/"medium"/"high", optional)
            tags: List of tags (optional, will be sanitized)
            recurrence: Recurrence config (optional, dict with "frequency" and "interval")

        Returns:
            Dict with:
            - success: bool
            - reminder_id: Optional[str]
            - error: Optional[str]
        """
        # Validate title
        validated_title, error = validate_non_empty_string(title, "title")
        if error:
            return {"success": False, "reminder_id": None, "error": error}

        # Validate and parse due_date if provided
        due_datetime = None
        if due_date:
            due_datetime, error = validate_iso_datetime(due_date, "due_date")
            if error:
                return {"success": False, "reminder_id": None, "error": error}

        # Validate priority if provided
        validated_priority = None
        if priority is not None:
            validated_priority, error = validate_priority(priority, "priority")
            if error:
                return {"success": False, "reminder_id": None, "error": error}

        # Validate and sanitize tags if provided
        validated_tags = None
        if tags is not None:
            validated_tags, error = validate_tags(tags, "tags")
            if error:
                return {"success": False, "reminder_id": None, "error": error}

        # Validate recurrence if provided
        validated_recurrence = None
        if recurrence is not None:
            validated_recurrence, error = validate_recurrence(recurrence, "recurrence")
            if error:
                return {"success": False, "reminder_id": None, "error": error}

        # Create reminder via interface
        result = self.interface.create_reminder(
            title=validated_title,
            list_name=list_name,
            due_date=due_datetime,
            notes=notes,
            priority=validated_priority,
            tags=validated_tags,
            recurrence=validated_recurrence
        )

        # Auto-log to database if successful
        if result["success"] and self.auto_logging and self.planner_db_path:
            self._log_interaction(
                action="created",
                reminder_id=result["reminder_id"],
                title=validated_title,
                due_date=due_date,
                notes=notes
            )

        return result

    def complete_reminder(self, reminder_id: str) -> Dict[str, any]:
        """
        Complete reminder with validation and auto-logging.

        Args:
            reminder_id: The reminder's calendarItemIdentifier

        Returns:
            Dict with:
            - success: bool
            - error: Optional[str]
        """
        # Validate reminder_id
        validated_id, error = validate_non_empty_string(reminder_id, "reminder_id")
        if error:
            return {"success": False, "error": error}

        # Complete reminder via interface
        result = self.interface.complete_reminder(validated_id)

        # Auto-log to database if successful
        if result["success"] and self.auto_logging and self.planner_db_path:
            self._log_interaction(
                action="completed",
                reminder_id=validated_id,
                title="[completed]",  # Title not available without extra query
                completion_date=datetime.now(timezone.utc).isoformat()
            )

        return result

    def delete_reminder(self, reminder_id: str) -> Dict[str, any]:
        """
        Delete reminder with validation and auto-logging.

        Args:
            reminder_id: The reminder's calendarItemIdentifier

        Returns:
            Dict with:
            - success: bool
            - error: Optional[str]
        """
        # Validate reminder_id
        validated_id, error = validate_non_empty_string(reminder_id, "reminder_id")
        if error:
            return {"success": False, "error": error}

        # Delete reminder via interface
        result = self.interface.delete_reminder(validated_id)

        # Auto-log to database if successful
        if result["success"] and self.auto_logging and self.planner_db_path:
            self._log_interaction(
                action="deleted",
                reminder_id=validated_id,
                title="[deleted]"  # Title not available after deletion
            )

        return result

    def _log_interaction(
        self,
        action: str,
        reminder_id: str,
        title: str,
        **kwargs
    ):
        """
        Log reminder interaction to life planner database.

        Args:
            action: Action type (created, completed, deleted)
            reminder_id: The reminder's ID
            title: Reminder title
            **kwargs: Additional metadata (due_date, notes, etc.)
        """
        if not self.planner_db_path or not self.planner_db_path.exists():
            logger.warning(f"Database not found at {self.planner_db_path}, skipping log")
            return

        try:
            conn = sqlite3.connect(self.planner_db_path)
            cursor = conn.cursor()

            # Insert interaction log
            cursor.execute("""
                INSERT INTO reminder_interactions
                (timestamp, action, reminder_id, title, due_date, completion_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                action,
                reminder_id,
                title,
                kwargs.get("due_date"),
                kwargs.get("completion_date"),
                json.dumps({k: v for k, v in kwargs.items() if k not in ["due_date", "completion_date"]})
            ))

            conn.commit()
            conn.close()

            logger.info(f"Logged reminder {action}: {title} (ID: {reminder_id})")

        except Exception as e:
            logger.error(f"Failed to log interaction: {e}", exc_info=True)

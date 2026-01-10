"""
macOS Reminders integration for Reminders MCP server.

Provides interface to create reminders via AppleScript and read/manage reminders
via EventKit framework (PyObjC).

Hybrid approach:
- AppleScript for creating reminders (simple, reliable)
- EventKit for reading, completing, deleting (robust querying)

CHANGELOG (recent first, max 5 entries):
01/09/2026 - Increased timeouts from 10s to 15s to reduce intermittent failures (Claude)
"""

import subprocess
import logging
import re
from typing import Optional, List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def escape_applescript_string(s: str) -> str:
    r"""
    Escape a string for safe use in AppleScript.

    AppleScript strings use backslash escapes, so we must:
    1. Escape backslashes first (\ -> \\)
    2. Then escape double quotes (" -> \")

    This prevents injection attacks where user data could break out of
    the quoted string context in AppleScript commands.

    Args:
        s: The string to escape

    Returns:
        Escaped string safe for AppleScript double-quoted strings

    Examples:
        >>> escape_applescript_string('Hello "World"')
        'Hello \\"World\\"'
        >>> escape_applescript_string('Path\\to\\file')
        'Path\\\\to\\\\file'
    """
    if s is None:
        return ""
    # Escape backslashes first, then quotes
    return s.replace('\\', '\\\\').replace('"', '\\"')


def parse_tags_from_notes(notes: str) -> List[str]:
    """
    Parse tags from notes field using hashtag syntax.

    Tags are identified by # followed by word characters.
    Example: "Meeting notes #work #urgent" -> ["work", "urgent"]

    Args:
        notes: Notes text containing hashtags

    Returns:
        List of tag strings (without # prefix)
    """
    if not notes:
        return []

    # Match hashtags: # followed by word characters
    tags = re.findall(r'#(\w+)', notes)
    return tags


def append_tags_to_notes(notes: str, tags: List[str]) -> str:
    """
    Append tags to notes field using hashtag syntax.

    Tags are added at the end separated by newlines if notes exist.

    Args:
        notes: Existing notes text (may be None or empty)
        tags: List of tag strings to append

    Returns:
        Notes with tags appended as "#tag1 #tag2"
    """
    if not tags:
        return notes or ""

    base = notes or ""
    tag_string = " ".join(f"#{tag}" for tag in tags)

    # If there's existing content, add separator
    if base.strip():
        return f"{base}\n\n{tag_string}"
    else:
        return tag_string


class RemindersInterface:
    """
    Interface to macOS Reminders.app.

    Hybrid implementation:
    - AppleScript for creating reminders
    - EventKit (PyObjC) for reading, completing, deleting
    """

    def __init__(self, default_list: str = "Reminders"):
        """
        Initialize RemindersInterface.

        Args:
            default_list: Name of the default reminder list to use
        """
        self.default_list = default_list
        self._event_store = None  # Lazy-loaded EventKit store
        logger.info(f"RemindersInterface initialized with default list: {default_list}")

    @property
    def event_store(self):
        """Lazy-load EventKit event store."""
        if self._event_store is None:
            from EventKit import EKEventStore
            self._event_store = EKEventStore.alloc().init()
            logger.debug("Initialized EKEventStore")
        return self._event_store

    def check_permissions(self) -> Dict[str, bool]:
        """
        Check macOS permissions for Reminders access.

        Returns:
            Dict with permission status:
            - reminders_authorized: EventKit access granted
            - applescript_ready: AppleScript can execute
        """
        from src.reminder_sync import EventKitHelper

        # Check EventKit authorization
        auth_status = EventKitHelper.check_authorization_status()
        reminders_authorized = (auth_status == "authorized")

        # Check AppleScript by attempting a simple query
        applescript_ready = False
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "Reminders" to get name of every list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            applescript_ready = (result.returncode == 0)
        except Exception as e:
            logger.warning(f"AppleScript permission check failed: {e}")

        return {
            "reminders_authorized": reminders_authorized,
            "applescript_ready": applescript_ready
        }

    def list_reminder_lists(self) -> List[Dict[str, str]]:
        """
        Get all available reminder lists.

        Returns:
            List of dicts with:
            - list_id: str (calendar identifier)
            - title: str (display name)
            - color: str (hex color code)
            - type: str (local/caldav/exchange)
        """
        from EventKit import EKEntityTypeReminder

        try:
            # Get all reminder calendars
            calendars = self.event_store.calendarsForEntityType_(EKEntityTypeReminder)

            lists = []
            for calendar in calendars:
                # Extract calendar info
                list_dict = {
                    "list_id": calendar.calendarIdentifier(),
                    "title": calendar.title(),
                    "color": self._color_to_hex(calendar.color()) if calendar.color() else "#000000",
                    "type": self._calendar_type_string(calendar.type())
                }
                lists.append(list_dict)

            logger.info(f"Found {len(lists)} reminder lists")
            return lists

        except Exception as e:
            logger.error(f"Error listing reminder lists: {e}", exc_info=True)
            return []

    def _color_to_hex(self, color) -> str:
        """Convert NSColor to hex string."""
        try:
            # Get RGB components (0.0-1.0)
            red = int(color.redComponent() * 255)
            green = int(color.greenComponent() * 255)
            blue = int(color.blueComponent() * 255)
            return f"#{red:02X}{green:02X}{blue:02X}"
        except:
            return "#000000"

    def _calendar_type_string(self, cal_type: int) -> str:
        """Convert EKCalendarType to string."""
        # 0 = Local, 1 = CalDAV, 2 = Exchange, 3 = Subscription, 4 = Birthday
        type_map = {
            0: "local",
            1: "caldav",
            2: "exchange",
            3: "subscription",
            4: "birthday"
        }
        return type_map.get(cal_type, "unknown")

    def create_reminder(
        self,
        title: str,
        list_name: Optional[str] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        priority: Optional[int] = None,
        tags: Optional[List[str]] = None,
        recurrence: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Create a reminder using hybrid approach.

        Routes to EventKit for recurring reminders (AppleScript doesn't support recurrence).
        Uses AppleScript for simple reminders (proven, reliable).

        Args:
            title: Reminder title (required)
            list_name: Target list (default: self.default_list)
            due_date: Optional due date (Python datetime)
            notes: Optional reminder notes/body
            priority: Optional priority (0-9, where 0=none, 9=highest)
            tags: Optional list of tags (stored as hashtags in notes)
            recurrence: Optional recurrence config (dict with "frequency" and "interval")

        Returns:
            Dict with:
            - success: bool
            - reminder_id: str (if successful)
            - error: Optional[str]
        """
        # Route to EventKit if recurrence is requested
        # (AppleScript doesn't support EKRecurrenceRule)
        if recurrence:
            return self._create_reminder_eventkit(
                title=title,
                list_name=list_name,
                due_date=due_date,
                notes=notes,
                priority=priority,
                tags=tags,
                recurrence=recurrence
            )

        # Otherwise use AppleScript (simpler, proven)
        # Append tags to notes if provided
        full_notes = append_tags_to_notes(notes, tags) if tags else notes

        # Escape inputs for AppleScript safety
        escaped_title = escape_applescript_string(title)
        target_list = list_name if list_name else self.default_list
        escaped_list = escape_applescript_string(target_list)
        escaped_notes = escape_applescript_string(full_notes) if full_notes else ""

        # Build AppleScript command
        script = f'''
tell application "Reminders"
    set myList to list "{escaped_list}"
    tell myList
        set newReminder to make new reminder
        set name of newReminder to "{escaped_title}"
'''

        # Add due date if provided
        if due_date:
            # Convert Python datetime to AppleScript date format: "MM/DD/YYYY HH:MM AM/PM"
            date_str = due_date.strftime("%m/%d/%Y %I:%M %p")
            script += f'''
        set remind me date of newReminder to date "{date_str}"
'''

        # Add notes if provided
        if notes:
            script += f'''
        set body of newReminder to "{escaped_notes}"
'''

        # Add priority if provided
        if priority is not None:
            script += f'''
        set priority of newReminder to {priority}
'''

        # Close the script and return the reminder ID
        script += '''
        return id of newReminder
    end tell
end tell
'''

        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=15  # Increased from 10s to handle Reminders.app latency
            )

            if result.returncode == 0:
                reminder_id = result.stdout.strip()
                logger.info(f"Created reminder: '{title}' (ID: {reminder_id})")
                return {
                    "success": True,
                    "reminder_id": reminder_id,
                    "error": None
                }
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Failed to create reminder: {error_msg}")
                return {
                    "success": False,
                    "reminder_id": None,
                    "error": error_msg or "AppleScript execution failed"
                }

        except subprocess.TimeoutExpired:
            error_msg = "Timeout - ensure Reminders.app is accessible"
            logger.error(error_msg)
            return {
                "success": False,
                "reminder_id": None,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Exception creating reminder: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "reminder_id": None,
                "error": error_msg
            }

    def _create_reminder_eventkit(
        self,
        title: str,
        list_name: Optional[str] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        priority: Optional[int] = None,
        tags: Optional[List[str]] = None,
        recurrence: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Create a reminder using EventKit (for recurring reminders).

        EventKit is required for recurrence support since AppleScript
        doesn't support EKRecurrenceRule.

        Args:
            title: Reminder title (required)
            list_name: Target list (default: self.default_list)
            due_date: Optional due date (Python datetime)
            notes: Optional reminder notes/body
            priority: Optional priority (0-9)
            tags: Optional list of tags
            recurrence: Recurrence config (dict with "frequency" and "interval")

        Returns:
            Dict with success status, reminder_id, and error if any
        """
        from EventKit import EKReminder, EKEntityTypeReminder
        from src.reminder_sync import EventKitHelper

        try:
            # Get target calendar (list)
            calendars = self.event_store.calendarsForEntityType_(EKEntityTypeReminder)
            target_list = list_name if list_name else self.default_list
            calendar = next((c for c in calendars if c.title() == target_list), None)

            if not calendar:
                return {
                    "success": False,
                    "reminder_id": None,
                    "error": f"List not found: {target_list}"
                }

            # Create reminder
            reminder = EKReminder.reminderWithEventStore_(self.event_store)
            reminder.setTitle_(title)
            reminder.setCalendar_(calendar)

            # Set due date if provided
            if due_date:
                components = EventKitHelper.convert_datetime_to_nsdatecomponents(due_date)
                if components:
                    reminder.setDueDateComponents_(components)

            # Set notes with tags if provided
            if notes or tags:
                full_notes = append_tags_to_notes(notes, tags) if tags else notes
                reminder.setNotes_(full_notes)

            # Set priority if provided
            if priority is not None:
                reminder.setPriority_(priority)

            # Add recurrence rule if provided
            if recurrence:
                rule = EventKitHelper.create_recurrence_rule(
                    recurrence["frequency"],
                    recurrence.get("interval", 1)
                )
                if rule:
                    reminder.addRecurrenceRule_(rule)
                else:
                    return {
                        "success": False,
                        "reminder_id": None,
                        "error": "Failed to create recurrence rule"
                    }

            # Save reminder
            success, error = self.event_store.saveReminder_commit_error_(
                reminder, True, None
            )

            if success:
                reminder_id = reminder.calendarItemIdentifier()
                logger.info(f"Created recurring reminder via EventKit: '{title}' (ID: {reminder_id})")
                return {
                    "success": True,
                    "reminder_id": reminder_id,
                    "error": None
                }
            else:
                error_msg = str(error) if error else "Failed to save reminder"
                logger.error(f"EventKit save failed: {error_msg}")
                return {
                    "success": False,
                    "reminder_id": None,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception creating reminder via EventKit: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "reminder_id": None,
                "error": error_msg
            }

    def list_reminders(
        self,
        list_name: Optional[str] = None,
        completed: bool = False,
        limit: int = 50,
        tag_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        List reminders using EventKit.

        Args:
            list_name: Optional - filter by specific list (default: use default_list)
            completed: Show completed reminders (default: False - incomplete only)
            limit: Maximum number of reminders to return (default: 50)
            tag_filter: Optional - filter by tag (e.g., "work" matches #work)

        Returns:
            List of reminder dicts with:
            - reminder_id: str
            - title: str
            - completed: bool
            - due_date: Optional[str] (ISO 8601)
            - notes: Optional[str]
            - creation_date: str
            - completion_date: Optional[str]
            - list_name: str
            - priority: int (0-9)
            - tags: List[str] (parsed from notes)
        """
        from EventKit import EKEntityTypeReminder
        from src.reminder_sync import EventKitHelper
        import threading

        # Check authorization
        auth_status = EventKitHelper.check_authorization_status()
        if auth_status != "authorized":
            logger.error(f"Reminders not authorized: {auth_status}")
            return []

        # Get calendars (reminder lists)
        calendars = self.event_store.calendarsForEntityType_(EKEntityTypeReminder)

        # Filter to specific list if requested
        target_list = list_name if list_name else self.default_list
        filtered_calendars = [c for c in calendars if c.title() == target_list]

        if not filtered_calendars:
            logger.warning(f"No calendars found for list: {target_list}")
            return []

        # Create predicate for reminders
        predicate = self.event_store.predicateForRemindersInCalendars_(filtered_calendars)

        # Fetch reminders (EventKit uses async callbacks)
        reminders_list = []
        fetch_complete = threading.Event()

        def fetch_callback(reminders):
            """Callback for async reminder fetch."""
            nonlocal reminders_list

            if reminders:
                for reminder in reminders:
                    # Filter by completion status
                    if reminder.isCompleted() != completed:
                        continue

                    # Extract reminder data
                    notes_text = reminder.notes() or ""
                    reminder_dict = {
                        "reminder_id": reminder.calendarItemIdentifier(),
                        "title": reminder.title() or "",
                        "completed": reminder.isCompleted(),
                        "due_date": None,
                        "notes": notes_text,
                        "creation_date": None,
                        "completion_date": None,
                        "list_name": reminder.calendar().title(),
                        "priority": reminder.priority(),
                        "tags": parse_tags_from_notes(notes_text)
                    }

                    # Filter by tag if requested
                    if tag_filter and tag_filter.lower() not in [tag.lower() for tag in reminder_dict["tags"]]:
                        continue

                    # Convert dates
                    if reminder.dueDateComponents():
                        due_dt = EventKitHelper.convert_nsdatecomponents_to_datetime(
                            reminder.dueDateComponents()
                        )
                        if due_dt:
                            reminder_dict["due_date"] = due_dt.isoformat()

                    if reminder.creationDate():
                        creation_dt = EventKitHelper.convert_nsdate_to_datetime(
                            reminder.creationDate()
                        )
                        if creation_dt:
                            reminder_dict["creation_date"] = creation_dt.isoformat()

                    if reminder.isCompleted() and reminder.completionDate():
                        completion_dt = EventKitHelper.convert_nsdate_to_datetime(
                            reminder.completionDate()
                        )
                        if completion_dt:
                            reminder_dict["completion_date"] = completion_dt.isoformat()

                    reminders_list.append(reminder_dict)

                    # Limit results
                    if len(reminders_list) >= limit:
                        break

            # Signal completion
            fetch_complete.set()

        # Execute async fetch
        self.event_store.fetchRemindersMatchingPredicate_completion_(
            predicate, fetch_callback
        )

        # Wait for callback to complete (with timeout)
        # Increased from 10s to 15s to handle EventKit async latency
        fetch_complete.wait(timeout=15.0)

        if not fetch_complete.is_set():
            logger.error("EventKit fetch timed out")

        logger.info(f"Retrieved {len(reminders_list)} reminders from '{target_list}'")
        return reminders_list[:limit]

    def get_reminder_by_id(self, reminder_id: str):
        """
        Get a single reminder by ID using EventKit.

        Args:
            reminder_id: The reminder's calendarItemIdentifier

        Returns:
            EKReminder object or None if not found
        """
        try:
            reminder = self.event_store.calendarItemWithIdentifier_(reminder_id)
            if reminder:
                logger.debug(f"Found reminder: {reminder_id}")
                return reminder
            else:
                logger.warning(f"Reminder not found: {reminder_id}")
                return None
        except Exception as e:
            logger.error(f"Error fetching reminder {reminder_id}: {e}")
            return None

    def complete_reminder(self, reminder_id: str) -> Dict[str, any]:
        """
        Mark a reminder as complete using EventKit.

        Args:
            reminder_id: The reminder's calendarItemIdentifier

        Returns:
            Dict with:
            - success: bool
            - error: Optional[str]
        """
        try:
            # Get reminder
            reminder = self.get_reminder_by_id(reminder_id)
            if not reminder:
                return {
                    "success": False,
                    "error": f"Reminder not found: {reminder_id}"
                }

            # Mark as completed
            reminder.setCompleted_(True)

            # Save changes
            success, error = self.event_store.saveReminder_commit_error_(
                reminder, True, None
            )

            if success:
                logger.info(f"Completed reminder: {reminder_id}")
                return {
                    "success": True,
                    "error": None
                }
            else:
                error_msg = str(error) if error else "Failed to save reminder"
                logger.error(f"Failed to complete reminder: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception completing reminder: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

    def delete_reminder(self, reminder_id: str) -> Dict[str, any]:
        """
        Delete a reminder permanently using EventKit.

        Args:
            reminder_id: The reminder's calendarItemIdentifier

        Returns:
            Dict with:
            - success: bool
            - error: Optional[str]
        """
        try:
            # Get reminder
            reminder = self.get_reminder_by_id(reminder_id)
            if not reminder:
                return {
                    "success": False,
                    "error": f"Reminder not found: {reminder_id}"
                }

            # Delete reminder
            success, error = self.event_store.removeReminder_commit_error_(
                reminder, True, None
            )

            if success:
                logger.info(f"Deleted reminder: {reminder_id}")
                return {
                    "success": True,
                    "error": None
                }
            else:
                error_msg = str(error) if error else "Failed to delete reminder"
                logger.error(f"Failed to delete reminder: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception deleting reminder: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

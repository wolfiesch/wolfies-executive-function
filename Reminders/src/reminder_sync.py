"""
PyObjC EventKit integration utilities for Reminders MCP server.

Provides helper functions for:
- EventKit authorization
- NSDate ↔ Python datetime conversions
- NSDateComponents parsing
- EventKit type wrappers
"""

import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EventKitHelper:
    """Helper utilities for PyObjC EventKit integration."""

    @staticmethod
    def request_access() -> bool:
        """
        Request Reminders access authorization from macOS.

        This will prompt the user if they haven't granted permission yet.
        The prompt is blocking - it waits for user response.

        Returns:
            True if authorized, False otherwise
        """
        from EventKit import EKEventStore, EKEntityTypeReminder

        store = EKEventStore.alloc().init()

        # Request access (blocks until user responds to permission dialog)
        granted, error = store.requestAccessToEntityType_error_(
            EKEntityTypeReminder, None
        )

        if not granted:
            logger.error(f"Reminders access denied: {error}")
            return False

        logger.info("Reminders access authorized")
        return True

    @staticmethod
    def convert_nsdate_to_datetime(nsdate) -> Optional[datetime]:
        """
        Convert NSDate to Python datetime.

        Args:
            nsdate: Objective-C NSDate object

        Returns:
            Python datetime in UTC, or None if conversion fails
        """
        if not nsdate:
            return None

        try:
            # NSDate.timeIntervalSince1970() returns seconds since Unix epoch
            timestamp = nsdate.timeIntervalSince1970()
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to convert NSDate: {e}")
            return None

    @staticmethod
    def convert_datetime_to_nsdate(dt: datetime):
        """
        Convert Python datetime to NSDate.

        Args:
            dt: Python datetime object

        Returns:
            Objective-C NSDate object
        """
        from Foundation import NSDate

        if not dt:
            return None

        try:
            timestamp = dt.timestamp()
            return NSDate.dateWithTimeIntervalSince1970_(timestamp)
        except Exception as e:
            logger.warning(f"Failed to convert datetime to NSDate: {e}")
            return None

    @staticmethod
    def convert_nsdatecomponents_to_datetime(components) -> Optional[datetime]:
        """
        Convert NSDateComponents to Python datetime.

        NSDateComponents is used by EventKit for due dates, which can be:
        - Full datetime (year, month, day, hour, minute)
        - Date only (year, month, day) with hour/minute as NSIntegerMax

        Args:
            components: NSDateComponents object from EKReminder

        Returns:
            Python datetime in UTC, or None if invalid/missing
        """
        if not components:
            return None

        try:
            # Extract date components
            year = components.year()
            month = components.month()
            day = components.day()

            # NSIntegerMax is used for "not set" values
            # On 64-bit systems, NSIntegerMax is 9223372036854775807
            NSIntegerMax = 9223372036854775807

            # Extract time components (may be NSIntegerMax if not set)
            hour = components.hour() if components.hour() != NSIntegerMax else 0
            minute = components.minute() if components.minute() != NSIntegerMax else 0

            # Validate date components
            if year <= 0 or month <= 0 or day <= 0:
                logger.debug("Invalid NSDateComponents: missing date")
                return None

            # Create datetime (assume UTC timezone)
            return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)

        except Exception as e:
            logger.warning(f"Failed to convert NSDateComponents: {e}")
            return None

    @staticmethod
    def check_authorization_status() -> str:
        """
        Check current EventKit authorization status.

        Returns:
            String describing status: "not_determined", "restricted", "denied", "authorized"
        """
        from EventKit import EKEventStore

        # The authorization status method is a class method, not instance method
        try:
            # Try the class method approach
            from EventKit import EKAuthorizationStatusAuthorized, EKAuthorizationStatusDenied, EKAuthorizationStatusRestricted
            store = EKEventStore.alloc().init()

            # EKEventStore authorization is checked via requestAccessToEntityType
            # For checking without requesting, we need to try a read operation
            # If we can get calendars, we're authorized
            try:
                calendars = store.calendarsForEntityType_(1)  # 1 = EKEntityTypeReminder
                if calendars is not None:
                    return "authorized"
                else:
                    return "not_determined"
            except:
                return "denied"

        except Exception as e:
            logger.warning(f"Failed to check authorization: {e}")
            return "unknown"

    @staticmethod
    def convert_datetime_to_nsdatecomponents(dt: datetime):
        """
        Convert Python datetime to NSDateComponents.

        NSDateComponents is used by EventKit for due dates in reminders.

        Args:
            dt: Python datetime object

        Returns:
            NSDateComponents object or None if conversion fails
        """
        from Foundation import NSDateComponents

        if not dt:
            return None

        try:
            components = NSDateComponents.alloc().init()
            components.setYear_(dt.year)
            components.setMonth_(dt.month)
            components.setDay_(dt.day)
            components.setHour_(dt.hour)
            components.setMinute_(dt.minute)

            return components

        except Exception as e:
            logger.warning(f"Failed to convert datetime to NSDateComponents: {e}")
            return None

    @staticmethod
    def create_recurrence_rule(frequency: str, interval: int = 1):
        """
        Create an EKRecurrenceRule for recurring reminders.

        Args:
            frequency: Recurrence frequency ("daily", "weekly", "monthly", "yearly")
            interval: Recurrence interval (e.g., 2 for every 2 weeks)

        Returns:
            EKRecurrenceRule object or None if creation fails

        CS Concept: Recurrence Rules
        EKRecurrenceRule defines how often a reminder repeats. The frequency is
        the time unit (daily, weekly, etc.) and interval is "every N units".
        For example, frequency="weekly" and interval=2 means "every 2 weeks".
        """
        from EventKit import (
            EKRecurrenceRule,
            EKRecurrenceFrequencyDaily,
            EKRecurrenceFrequencyWeekly,
            EKRecurrenceFrequencyMonthly,
            EKRecurrenceFrequencyYearly
        )

        # Map frequency strings to EventKit constants
        frequency_map = {
            "daily": EKRecurrenceFrequencyDaily,
            "weekly": EKRecurrenceFrequencyWeekly,
            "monthly": EKRecurrenceFrequencyMonthly,
            "yearly": EKRecurrenceFrequencyYearly
        }

        if frequency not in frequency_map:
            logger.error(f"Invalid recurrence frequency: {frequency}")
            return None

        try:
            ek_freq = frequency_map[frequency]

            # Create recurrence rule with no end date (None)
            # initRecurrenceWithFrequency_interval_end_(frequency, interval, end)
            rule = EKRecurrenceRule.alloc().initRecurrenceWithFrequency_interval_end_(
                ek_freq, interval, None
            )

            logger.debug(f"Created recurrence rule: {frequency} every {interval} period(s)")
            return rule

        except Exception as e:
            logger.error(f"Failed to create recurrence rule: {e}")
            return None

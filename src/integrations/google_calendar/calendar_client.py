#!/usr/bin/env python3
"""
Google Calendar API wrapper for Life Planner.

Provides authenticated access to Google Calendar API with helper methods
for common calendar operations.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dateutil import parser as date_parser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """
    Google Calendar API client with authentication and helper methods.

    Handles OAuth2 authentication, token management, and provides simplified
    methods for calendar operations.
    """

    def __init__(self, credentials_dir: str):
        """
        Initialize the Google Calendar client.

        Args:
            credentials_dir: Path to directory containing credentials.json and token.json
        """
        self.credentials_dir = Path(credentials_dir)
        self.credentials_file = self.credentials_dir / "credentials.json"
        self.token_file = self.credentials_dir / "token.json"
        self.service = None

        # Ensure credentials directory exists
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.

        Uses stored token if available, otherwise initiates OAuth flow.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        creds = None

        # Load existing token
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
                logger.info("Loaded existing credentials from token.json")
            except Exception as e:
                logger.warning(f"Failed to load token.json: {e}")

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                # Need to run OAuth flow
                if not self.credentials_file.exists():
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    logger.error("Please run scripts/setup_google_oauth.py first")
                    return False

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Completed OAuth flow, obtained new credentials")
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    return False

            # Save credentials for next run
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Saved credentials to {self.token_file}")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")

        # Build service
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Successfully built Google Calendar service")
            return True
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            return False

    def list_events(
        self,
        calendar_id: str = 'primary',
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10,
        order_by: str = 'startTime'
    ) -> List[Dict[str, Any]]:
        """
        List calendar events within a time range.

        Args:
            calendar_id: Calendar ID (default: 'primary')
            time_min: Start of time range (default: now)
            time_max: End of time range (default: None)
            max_results: Maximum number of events to return
            order_by: How to order results ('startTime' or 'updated')

        Returns:
            List of event dictionaries
        """
        if not self.service:
            logger.error("Service not initialized. Call authenticate() first.")
            return []

        # Default to now if no time_min specified
        if time_min is None:
            time_min = datetime.now(timezone.utc)

        try:
            # Build query parameters
            params = {
                'calendarId': calendar_id,
                'timeMin': time_min.isoformat() + 'Z',
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': order_by
            }

            if time_max:
                params['timeMax'] = time_max.isoformat() + 'Z'

            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])

            logger.info(f"Retrieved {len(events)} events")
            return events

        except HttpError as e:
            logger.error(f"HTTP error listing events: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return []

    def get_event(self, event_id: str, calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """
        Get details of a specific event.

        Args:
            event_id: Event ID
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            Event dictionary or None if not found
        """
        if not self.service:
            logger.error("Service not initialized. Call authenticate() first.")
            return None

        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"Retrieved event: {event.get('summary', 'No title')}")
            return event

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Event not found: {event_id}")
            else:
                logger.error(f"HTTP error getting event: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return None

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new calendar event.

        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            Created event dictionary or None if failed
        """
        if not self.service:
            logger.error("Service not initialized. Call authenticate() first.")
            return None

        # Build event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }

        if description:
            event['description'] = description

        if location:
            event['location'] = location

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        try:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            logger.info(f"Created event: {created_event.get('summary')} (ID: {created_event.get('id')})")
            return created_event

        except HttpError as e:
            logger.error(f"HTTP error creating event: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None

    def find_free_time(
        self,
        duration_minutes: int,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = 'primary',
        working_hours_start: int = 9,
        working_hours_end: int = 17
    ) -> List[Dict[str, datetime]]:
        """
        Find available time slots within a date range.

        Args:
            duration_minutes: Required duration in minutes
            time_min: Search start time (default: now)
            time_max: Search end time (default: 7 days from now)
            calendar_id: Calendar ID (default: 'primary')
            working_hours_start: Start of working hours (default: 9am)
            working_hours_end: End of working hours (default: 5pm)

        Returns:
            List of free time slot dictionaries with 'start' and 'end' keys
        """
        if not self.service:
            logger.error("Service not initialized. Call authenticate() first.")
            return []

        # Defaults
        if time_min is None:
            time_min = datetime.now(timezone.utc)
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        # Get all events in the time range
        events = self.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=250,
            order_by='startTime'
        )

        # Extract busy periods
        busy_periods = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})

            # Parse start/end times
            start_dt = date_parser.parse(start.get('dateTime', start.get('date')))
            end_dt = date_parser.parse(end.get('dateTime', end.get('date')))

            busy_periods.append({
                'start': start_dt,
                'end': end_dt
            })

        # Find free slots
        free_slots = []
        current_time = time_min

        while current_time < time_max:
            # Skip to next working day/hour if outside working hours
            if current_time.hour < working_hours_start:
                current_time = current_time.replace(
                    hour=working_hours_start,
                    minute=0,
                    second=0
                )
            elif current_time.hour >= working_hours_end:
                # Move to next day
                current_time = (current_time + timedelta(days=1)).replace(
                    hour=working_hours_start,
                    minute=0,
                    second=0
                )
                continue

            # Skip weekends
            if current_time.weekday() >= 5:  # Saturday=5, Sunday=6
                # Move to Monday
                days_to_add = 7 - current_time.weekday() + 1
                current_time = (current_time + timedelta(days=days_to_add)).replace(
                    hour=working_hours_start,
                    minute=0,
                    second=0
                )
                continue

            # Check if this time slot is free
            slot_end = current_time + timedelta(minutes=duration_minutes)

            # Make sure slot doesn't extend past working hours
            if slot_end.hour > working_hours_end or (
                slot_end.hour == working_hours_end and slot_end.minute > 0
            ):
                # Move to next day
                current_time = (current_time + timedelta(days=1)).replace(
                    hour=working_hours_start,
                    minute=0,
                    second=0
                )
                continue

            # Check if slot conflicts with any busy period
            is_free = True
            for busy in busy_periods:
                if (current_time < busy['end'] and slot_end > busy['start']):
                    # Conflict found, move past this busy period
                    current_time = busy['end']
                    is_free = False
                    break

            if is_free:
                free_slots.append({
                    'start': current_time,
                    'end': slot_end
                })
                # Move to next potential slot (15 min increments)
                current_time = current_time + timedelta(minutes=15)

            # Limit results
            if len(free_slots) >= 20:
                break

        logger.info(f"Found {len(free_slots)} free time slots")
        return free_slots

    def update_event(
        self,
        event_id: str,
        calendar_id: str = 'primary',
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing event.

        Args:
            event_id: Event ID to update
            calendar_id: Calendar ID (default: 'primary')
            **kwargs: Fields to update (summary, start, end, description, etc.)

        Returns:
            Updated event dictionary or None if failed
        """
        if not self.service:
            logger.error("Service not initialized. Call authenticate() first.")
            return None

        try:
            # Get current event
            event = self.get_event(event_id, calendar_id)
            if not event:
                return None

            # Update fields
            for key, value in kwargs.items():
                event[key] = value

            # Update event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Updated event: {updated_event.get('summary')}")
            return updated_event

        except HttpError as e:
            logger.error(f"HTTP error updating event: {e}")
            return None
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return None

    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """
        Delete an event.

        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.error("Service not initialized. Call authenticate() first.")
            return False

        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"Deleted event: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"HTTP error deleting event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False

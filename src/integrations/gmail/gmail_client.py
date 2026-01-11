#!/usr/bin/env python3
"""
Gmail API Client - Wrapper for Gmail API operations.

Handles authentication, token management, and Gmail API calls.
Shares OAuth credentials with Calendar integration if available.

CHANGELOG (recent first, max 5 entries):
01/08/2026 - Implemented BatchHttpRequest for N+1 optimization (5x speedup) (Claude)
01/08/2026 - Added timing instrumentation for performance profiling (Claude)
"""

import os
import pickle
import base64
import logging
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

logger = logging.getLogger(__name__)


# =============================================================================
# TIMING INSTRUMENTATION (for profiling)
# =============================================================================

class TimingContext:
    """
    Context manager that logs timing to stderr for benchmark capture.

    Timing markers are in format: [TIMING] phase_name=XX.XXms
    These are parsed by the benchmark runner to capture server-side timing.
    """

    def __init__(self, phase_name: str):
        self.phase = phase_name
        self.start: float = 0

    def __enter__(self) -> "TimingContext":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed_ms = (time.perf_counter() - self.start) * 1000
        print(f"[TIMING] {self.phase}={elapsed_ms:.2f}ms", file=sys.stderr)


def _timing(phase: str) -> TimingContext:
    """Convenience function to create a timing context."""
    return TimingContext(phase)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailClient:
    """Gmail API client for email operations."""

    def __init__(self, credentials_dir: str):
        """
        Initialize Gmail client.

        Args:
            credentials_dir: Path to directory containing credentials.json and token.pickle
        """
        self.credentials_dir = Path(credentials_dir)
        self.credentials_file = self.credentials_dir / "credentials.json"
        self.token_file = self.credentials_dir / "gmail_token.pickle"
        self.service = None

        # Ensure directory exists
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        self._authenticate()

    def _authenticate(self):
        """
        Authenticate with Gmail API using OAuth2.

        Shares credentials with Calendar integration if available.
        Creates token.pickle for persistent authentication.
        """
        creds = None

        # Try to load existing token
        if self.token_file.exists():
            logger.info(f"Loading existing token from {self.token_file}")
            with _timing("oauth_load"):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired token")
                with _timing("oauth_refresh"):
                    creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        f"Please download credentials.json from Google Cloud Console:\n"
                        f"1. Go to https://console.cloud.google.com/apis/credentials\n"
                        f"2. Create OAuth 2.0 Client ID (Desktop app)\n"
                        f"3. Download and save as {self.credentials_file}"
                    )

                logger.info("Starting OAuth flow")
                with _timing("oauth_flow"):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

            # Save credentials for future use
            logger.info(f"Saving token to {self.token_file}")
            with _timing("oauth_save"):
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)

        # Build Gmail service
        with _timing("api_discovery"):
            self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")

    def list_emails(
        self,
        max_results: int = 10,
        unread_only: bool = False,
        label: Optional[str] = None,
        sender: Optional[str] = None,
        after_date: Optional[str] = None,
        before_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List emails with optional filters.

        Args:
            max_results: Maximum number of emails to return (default: 10)
            unread_only: Only return unread emails
            label: Filter by Gmail label (e.g., "INBOX", "SENT")
            sender: Filter by sender email address
            after_date: Filter emails after date (format: YYYY/MM/DD)
            before_date: Filter emails before date (format: YYYY/MM/DD)

        Returns:
            List of email dictionaries with metadata
        """
        try:
            # Build query
            query_parts = []
            if unread_only:
                query_parts.append("is:unread")
            if sender:
                query_parts.append(f"from:{sender}")
            if after_date:
                query_parts.append(f"after:{after_date}")
            if before_date:
                query_parts.append(f"before:{before_date}")

            query = " ".join(query_parts) if query_parts else None

            # List messages (first API call)
            with _timing("api_list"):
                results = self.service.users().messages().list(
                    userId='me',
                    maxResults=max_results,
                    labelIds=[label] if label else None,
                    q=query
                ).execute()

            messages = results.get('messages', [])

            if not messages:
                return []

            # Batch fetch all messages (single HTTP request instead of N+1!)
            message_ids = [msg['id'] for msg in messages]
            return self._batch_get_emails(message_ids)

        except HttpError as error:
            logger.error(f"Error listing emails: {error}")
            raise

    def get_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full email content by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with email details or None if not found
        """
        with _timing("api_get"):
            return self._get_email_internal(message_id)

    def _get_email_internal(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Internal method for getting email - no timing wrapper."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')

            # Extract body
            body = self._get_email_body(message['payload'])

            # Check if unread
            is_unread = 'UNREAD' in message.get('labelIds', [])

            return {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'subject': subject,
                'from': from_email,
                'to': to_email,
                'date': date,
                'snippet': message.get('snippet', ''),
                'body': body,
                'is_unread': is_unread,
                'labels': message.get('labelIds', [])
            }

        except HttpError as error:
            logger.error(f"Error getting email {message_id}: {error}")
            return None

    def _get_email_body(self, payload: Dict) -> str:
        """
        Extract email body from payload.

        Args:
            payload: Gmail message payload

        Returns:
            Email body text (decoded)
        """
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    # Fallback to HTML if no plain text
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in payload and 'data' in payload['body']:
            # Simple message
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        return ""

    def _batch_get_emails(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Batch fetch multiple emails in a single HTTP request.

        Uses Google's BatchHttpRequest to fetch up to 100 emails in parallel,
        eliminating the N+1 query pattern that dominated performance.

        Args:
            message_ids: List of Gmail message IDs to fetch

        Returns:
            List of email dictionaries (in order of message_ids)
        """
        if not message_ids:
            return []

        # Results dictionary keyed by message_id to preserve order
        results: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        def callback(request_id: str, response: Dict, exception: Exception) -> None:
            """Callback for each batch request."""
            if exception is not None:
                logger.warning(f"Batch request failed for {request_id}: {exception}")
                errors.append(request_id)
            else:
                # Parse the response into our email format
                email_data = self._parse_message_response(request_id, response)
                if email_data:
                    results[request_id] = email_data

        # Create batch request
        with _timing("api_batch_get"):
            batch = self.service.new_batch_http_request(callback=callback)

            # Add all get requests to the batch
            for msg_id in message_ids:
                batch.add(
                    self.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ),
                    request_id=msg_id
                )

            # Execute the batch (single HTTP round-trip!)
            batch.execute()

        # Log batch stats
        print(f"[TIMING] api_batch_count={len(message_ids)}", file=sys.stderr)
        print(f"[TIMING] api_batch_errors={len(errors)}", file=sys.stderr)

        # Return results in original order
        return [results[msg_id] for msg_id in message_ids if msg_id in results]

    def _parse_message_response(self, message_id: str, message: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse a Gmail API message response into our standard format.

        Args:
            message_id: The message ID
            message: Raw Gmail API response

        Returns:
            Parsed email dictionary or None if parsing fails
        """
        try:
            # Extract headers
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')

            # Extract body
            body = self._get_email_body(message['payload'])

            # Check if unread
            is_unread = 'UNREAD' in message.get('labelIds', [])

            return {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'subject': subject,
                'from': from_email,
                'to': to_email,
                'date': date,
                'snippet': message.get('snippet', ''),
                'body': body,
                'is_unread': is_unread,
                'labels': message.get('labelIds', [])
            }
        except Exception as e:
            logger.error(f"Error parsing message {message_id}: {e}")
            return None

    def search_emails(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search emails by query string.

        Args:
            query: Gmail search query (e.g., "subject:meeting", "has:attachment")
            max_results: Maximum results to return

        Returns:
            List of matching emails
        """
        try:
            # Search messages (first API call)
            with _timing("api_search"):
                results = self.service.users().messages().list(
                    userId='me',
                    maxResults=max_results,
                    q=query
                ).execute()

            messages = results.get('messages', [])

            if not messages:
                return []

            # Batch fetch all messages (single HTTP request instead of N+1!)
            message_ids = [msg['id'] for msg in messages]
            return self._batch_get_emails(message_ids)

        except HttpError as error:
            logger.error(f"Error searching emails: {error}")
            raise

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)

        Returns:
            Dictionary with success status and message ID
        """
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Email sent successfully to {to} (ID: {sent_message['id']})")

            return {
                'success': True,
                'message_id': sent_message['id'],
                'thread_id': sent_message.get('threadId')
            }

        except HttpError as error:
            logger.error(f"Error sending email to {to}: {error}")
            return {
                'success': False,
                'error': str(error)
            }

    def get_unread_count(self) -> int:
        """
        Get count of unread emails.

        Returns:
            Number of unread emails
        """
        try:
            with _timing("api_unread_count"):
                results = self.service.users().messages().list(
                    userId='me',
                    labelIds=['UNREAD']
                ).execute()

            return results.get('resultSizeEstimate', 0)

        except HttpError as error:
            logger.error(f"Error getting unread count: {error}")
            return 0

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read.

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            logger.info(f"Marked message {message_id} as read")
            return True

        except HttpError as error:
            logger.error(f"Error marking message as read: {error}")
            return False

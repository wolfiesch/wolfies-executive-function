#!/usr/bin/env python3
"""
Gmail API Client - Wrapper for Gmail API operations.

Handles authentication, token management, and Gmail API calls.
Shares OAuth credentials with Calendar integration if available.
"""

import os
import pickle
import base64
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

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
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired token")
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
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            logger.info(f"Saving token to {self.token_file}")
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        # Build Gmail service
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

            # List messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=[label] if label else None,
                q=query
            ).execute()

            messages = results.get('messages', [])

            if not messages:
                return []

            # Get full details for each message
            emails = []
            for msg in messages:
                email_data = self.get_email(msg['id'])
                if email_data:
                    emails.append(email_data)

            return emails

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
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()

            messages = results.get('messages', [])

            if not messages:
                return []

            # Get full details for each message
            emails = []
            for msg in messages:
                email_data = self.get_email(msg['id'])
                if email_data:
                    emails.append(email_data)

            return emails

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

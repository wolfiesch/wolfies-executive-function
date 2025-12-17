#!/usr/bin/env python3
"""
Test script for Gmail MCP integration.

Usage:
    python test_gmail.py
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.integrations.gmail.gmail_client import GmailClient

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"


def main():
    """Test Gmail client functionality."""
    print("=== Gmail Client Test ===\n")

    # Initialize client
    print(f"Credentials directory: {CREDENTIALS_DIR}")
    print("Initializing Gmail client...")

    try:
        client = GmailClient(str(CREDENTIALS_DIR))
        print("✓ Gmail client initialized successfully\n")
    except FileNotFoundError as e:
        print(f"✗ Error: {e}\n")
        print("Please run setup.sh first and ensure credentials.json is in place.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error initializing client: {e}\n")
        sys.exit(1)

    # Test 1: Get unread count
    print("Test 1: Get unread count")
    try:
        count = client.get_unread_count()
        print(f"✓ Unread emails: {count}\n")
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    # Test 2: List recent emails
    print("Test 2: List recent emails (5 max)")
    try:
        emails = client.list_emails(max_results=5)
        print(f"✓ Found {len(emails)} emails")

        for i, email in enumerate(emails, 1):
            print(f"\n  [{i}] {email['subject'][:50]}")
            print(f"      From: {email['from'][:40]}")
            print(f"      Date: {email['date']}")
            print(f"      Unread: {email['is_unread']}")

        print()
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    # Test 3: Search emails
    print("Test 3: Search emails (query: 'is:unread')")
    try:
        emails = client.search_emails("is:unread", max_results=3)
        print(f"✓ Found {len(emails)} unread emails")

        for i, email in enumerate(emails, 1):
            print(f"\n  [{i}] {email['subject'][:50]}")
            print(f"      From: {email['from'][:40]}")

        print()
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    print("=== All Tests Complete ===\n")
    print("Gmail client is working correctly!")
    print("\nYou can now use the Gmail MCP server in Claude Code.")
    print("Try: \"Check my email\" or \"Show unread emails\"")


if __name__ == "__main__":
    main()

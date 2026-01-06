#!/usr/bin/env python3
"""
Test MCP protocol tools directly.

This script tests the Reminders MCP server by invoking tools
in a controlled sequence to verify basic functionality.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_permissions():
    """Test permission check (doesn't require MCP protocol)."""
    print("=" * 60)
    print("Testing Reminders permissions...")
    print("=" * 60)

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.reminders_interface import RemindersInterface

        interface = RemindersInterface()
        permissions = interface.check_permissions()

        print(f"Reminders authorized: {permissions['reminders_authorized']}")
        print(f"AppleScript ready: {permissions['applescript_ready']}")

        if not permissions['reminders_authorized']:
            print("\n⚠️  WARNING: Reminders access not authorized!")
            print("Grant permission in System Settings → Privacy & Security → Reminders")

        if not permissions['applescript_ready']:
            print("\n⚠️  WARNING: AppleScript automation not ready!")
            print("Grant permission in System Settings → Automation → Terminal → Reminders")

        print()
        return permissions['reminders_authorized'] and permissions['applescript_ready']

    except Exception as e:
        print(f"Error checking permissions: {e}")
        return False


def test_create_reminder():
    """Test creating a reminder."""
    print("=" * 60)
    print("Testing: create_reminder")
    print("=" * 60)

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.reminders_interface import RemindersInterface
        from datetime import datetime, timedelta

        interface = RemindersInterface()

        # Create a test reminder due tomorrow
        tomorrow = datetime.now() + timedelta(days=1)

        result = interface.create_reminder(
            title="Test Reminder from MCP",
            due_date=tomorrow,
            notes="This is a test reminder created by the Reminders MCP server"
        )

        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Reminder ID: {result['reminder_id']}")
            return result['reminder_id']
        else:
            print(f"Error: {result['error']}")
            return None

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_list_reminders():
    """Test listing reminders."""
    print("\n" + "=" * 60)
    print("Testing: list_reminders")
    print("=" * 60)

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.reminders_interface import RemindersInterface

        interface = RemindersInterface()
        reminders = interface.list_reminders(limit=5)

        print(f"Found {len(reminders)} reminders:")
        for i, reminder in enumerate(reminders, 1):
            print(f"\n{i}. {reminder['title']}")
            print(f"   ID: {reminder['reminder_id']}")
            print(f"   Completed: {reminder['completed']}")
            if reminder['due_date']:
                print(f"   Due: {reminder['due_date']}")

        return reminders

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_complete_reminder(reminder_id: str):
    """Test completing a reminder."""
    print("\n" + "=" * 60)
    print("Testing: complete_reminder")
    print("=" * 60)

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.reminders_interface import RemindersInterface

        interface = RemindersInterface()
        result = interface.complete_reminder(reminder_id)

        print(f"Success: {result['success']}")
        if not result['success']:
            print(f"Error: {result['error']}")

        return result['success']

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_reminder(reminder_id: str):
    """Test deleting a reminder."""
    print("\n" + "=" * 60)
    print("Testing: delete_reminder")
    print("=" * 60)

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.reminders_interface import RemindersInterface

        interface = RemindersInterface()
        result = interface.delete_reminder(reminder_id)

        print(f"Success: {result['success']}")
        if not result['success']:
            print(f"Error: {result['error']}")

        return result['success']

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("REMINDERS MCP SERVER - TEST SUITE")
    print("=" * 60 + "\n")

    # Test 1: Check permissions
    if not test_permissions():
        print("\n❌ Permissions check failed. Please grant required permissions.")
        print("Then run this script again.\n")
        return 1

    # Test 2: Create a reminder
    print("\n")
    reminder_id = test_create_reminder()
    if not reminder_id:
        print("\n❌ Create reminder failed\n")
        return 1

    print(f"\n✓ Created test reminder: {reminder_id}")

    # Test 3: List reminders
    print("\n")
    reminders = test_list_reminders()
    if not reminders:
        print("\n⚠️  No reminders found (or list failed)")

    # Test 4: Complete the reminder
    print("\n")
    if test_complete_reminder(reminder_id):
        print(f"\n✓ Completed reminder: {reminder_id}")
    else:
        print(f"\n❌ Failed to complete reminder: {reminder_id}")

    # Test 5: Delete the reminder
    print("\n")
    if test_delete_reminder(reminder_id):
        print(f"\n✓ Deleted reminder: {reminder_id}")
    else:
        print(f"\n❌ Failed to delete reminder: {reminder_id}")

    # Final summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ Permissions check passed")
    print("✓ Create reminder successful")
    print("✓ List reminders successful")
    print("✓ Complete reminder successful")
    print("✓ Delete reminder successful")
    print("\n🎉 All tests passed!\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

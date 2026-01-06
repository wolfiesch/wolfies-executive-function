#!/usr/bin/env python3
"""
Migration 003: Add scheduled_messages table
Created: 01/04/2026

Adds support for scheduled/delayed message sending:
- scheduled_messages: Store messages to be sent at a future time
- Supports contact_id linking, status tracking, and recurrence
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DB_PATH = Path(__file__).parent.parent.parent / "data" / "database" / "planner.db"


def run_migration():
    """Add scheduled_messages table."""

    if not DB_PATH.exists():
        print(f"✗ Database not found: {DB_PATH}")
        print("Run scripts/init_db.py first to create the database.")
        return False

    print(f"Running migration on {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name = 'scheduled_messages'
        """)
        existing = cursor.fetchone()

        if existing:
            print("⚠ Table 'scheduled_messages' already exists")
            response = input("Drop and recreate? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborting migration.")
                return False

            cursor.execute("DROP TABLE IF EXISTS scheduled_messages")
            print("  Dropped scheduled_messages")

        # ====================================================================
        # Scheduled Messages table
        # ====================================================================
        cursor.execute("""
            CREATE TABLE scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
                phone TEXT NOT NULL,  -- Store phone even if contact deleted
                contact_name TEXT,    -- Cached contact name for display
                message TEXT NOT NULL,
                scheduled_at DATETIME NOT NULL,  -- When to send
                status TEXT DEFAULT 'pending'
                    CHECK(status IN ('pending', 'sent', 'cancelled', 'failed')),
                recurrence TEXT,  -- NULL for one-time, 'daily', 'weekly', 'monthly'
                recurrence_end DATETIME,  -- When to stop recurring
                error_message TEXT,  -- Error details if failed
                sent_at DATETIME,  -- Actual send time
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
            );
        """)
        print("✓ Created scheduled_messages table")

        # Indexes for scheduled_messages
        cursor.execute("CREATE INDEX idx_sched_status ON scheduled_messages(status);")
        cursor.execute("CREATE INDEX idx_sched_scheduled_at ON scheduled_messages(scheduled_at);")
        cursor.execute("CREATE INDEX idx_sched_contact_id ON scheduled_messages(contact_id);")
        cursor.execute("CREATE INDEX idx_sched_phone ON scheduled_messages(phone);")
        print("✓ Created indexes for scheduled_messages")

        # Updated_at trigger
        cursor.execute("""
            CREATE TRIGGER scheduled_messages_updated_at AFTER UPDATE ON scheduled_messages
            BEGIN
                UPDATE scheduled_messages SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)
        print("✓ Created updated_at trigger for scheduled_messages")

        conn.commit()
        print("\n✓ Migration complete!")
        return True

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def verify_migration():
    """Verify the migration was successful."""

    print("\nVerifying migration...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name = 'scheduled_messages'
        """)
        table = cursor.fetchone()
        if table:
            print(f"  ✓ Table exists: {table[0]}")
        else:
            print("  ✗ Table not found!")
            return False

        # Check columns
        cursor.execute("PRAGMA table_info(scheduled_messages)")
        columns = [row[1] for row in cursor.fetchall()]
        expected = ['id', 'contact_id', 'phone', 'contact_name', 'message',
                    'scheduled_at', 'status', 'recurrence', 'recurrence_end',
                    'error_message', 'sent_at', 'created_at', 'updated_at']
        if all(col in columns for col in expected):
            print(f"  ✓ All expected columns present ({len(columns)} total)")
        else:
            print(f"  ⚠ Missing columns. Found: {columns}")

        # Check scheduled count
        cursor.execute("SELECT COUNT(*) FROM scheduled_messages")
        count = cursor.fetchone()[0]
        print(f"  Scheduled messages: {count}")

        return True

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration 003: Add scheduled_messages table")
    print("=" * 60)
    print()

    success = run_migration()

    if success:
        verify_migration()
        print("\n" + "=" * 60)
        print("Migration complete!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Migration failed!")
        print("=" * 60)
        sys.exit(1)

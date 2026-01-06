#!/usr/bin/env python3
"""
Migration 002: Add contacts and message interactions tables
Created: 01/04/2026

Adds support for:
- contacts: Unified contact storage (replaces contacts.json)
- message_interactions: Log of sent/received messages for CRM
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DB_PATH = Path(__file__).parent.parent.parent / "data" / "database" / "planner.db"
CONTACTS_JSON = Path(__file__).parent.parent.parent / "Texting" / "config" / "contacts.json"


def run_migration():
    """Add contacts and message_interactions tables."""

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

        # Check if tables already exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('contacts', 'message_interactions')
        """)
        existing = [row[0] for row in cursor.fetchall()]

        if existing:
            print(f"⚠ Tables already exist: {existing}")
            response = input("Drop and recreate? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborting migration.")
                return False

            for table in existing:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  Dropped {table}")

        # ====================================================================
        # Contacts table
        # ====================================================================
        cursor.execute("""
            CREATE TABLE contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                relationship_type TEXT DEFAULT 'other'
                    CHECK(relationship_type IN ('friend', 'family', 'colleague', 'professional', 'personal', 'other')),
                last_interaction DATETIME,
                interaction_count INTEGER DEFAULT 0,
                notes TEXT,
                metadata TEXT,  -- JSON for additional fields
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
            );
        """)
        print("✓ Created contacts table")

        # Indexes for contacts
        cursor.execute("CREATE INDEX idx_contacts_name ON contacts(name);")
        cursor.execute("CREATE INDEX idx_contacts_phone ON contacts(phone);")
        cursor.execute("CREATE INDEX idx_contacts_relationship ON contacts(relationship_type);")
        cursor.execute("CREATE INDEX idx_contacts_last_interaction ON contacts(last_interaction);")
        print("✓ Created indexes for contacts")

        # Updated_at trigger for contacts
        cursor.execute("""
            CREATE TRIGGER contacts_updated_at AFTER UPDATE ON contacts
            BEGIN
                UPDATE contacts SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)
        print("✓ Created updated_at trigger for contacts")

        # ====================================================================
        # Message Interactions table
        # ====================================================================
        cursor.execute("""
            CREATE TABLE message_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
                phone TEXT NOT NULL,  -- Store phone even if contact deleted
                direction TEXT NOT NULL CHECK(direction IN ('sent', 'received')),
                message_preview TEXT,  -- First ~100 chars of message
                channel TEXT DEFAULT 'imessage' CHECK(channel IN ('imessage', 'sms', 'whatsapp', 'email')),
                timestamp DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                metadata TEXT,  -- JSON for additional data
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
            );
        """)
        print("✓ Created message_interactions table")

        # Indexes for message_interactions
        cursor.execute("CREATE INDEX idx_msg_contact_id ON message_interactions(contact_id);")
        cursor.execute("CREATE INDEX idx_msg_phone ON message_interactions(phone);")
        cursor.execute("CREATE INDEX idx_msg_direction ON message_interactions(direction);")
        cursor.execute("CREATE INDEX idx_msg_timestamp ON message_interactions(timestamp);")
        cursor.execute("CREATE INDEX idx_msg_channel ON message_interactions(channel);")
        print("✓ Created indexes for message_interactions")

        conn.commit()
        print("\n✓ Migration complete!")

        # Migrate existing contacts from JSON
        if CONTACTS_JSON.exists():
            migrate_contacts_from_json(conn, cursor)

        return True

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def migrate_contacts_from_json(conn: sqlite3.Connection, cursor: sqlite3.Cursor):
    """Migrate existing contacts from contacts.json to SQLite."""

    print(f"\nMigrating contacts from {CONTACTS_JSON}...")

    try:
        with open(CONTACTS_JSON) as f:
            data = json.load(f)

        contacts = data.get("contacts", [])
        if not contacts:
            print("  No contacts found in JSON")
            return

        migrated = 0
        skipped = 0

        for contact in contacts:
            name = contact.get("name", "").strip()
            phone = contact.get("phone", "").strip()

            if not name or not phone:
                skipped += 1
                continue

            # Check if phone already exists
            cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))
            if cursor.fetchone():
                skipped += 1
                continue

            cursor.execute("""
                INSERT INTO contacts (name, phone, relationship_type, notes)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                phone,
                contact.get("relationship_type", "other"),
                contact.get("notes", "")
            ))
            migrated += 1

        conn.commit()
        print(f"  ✓ Migrated {migrated} contacts")
        if skipped:
            print(f"  ⚠ Skipped {skipped} (empty or duplicate)")

    except Exception as e:
        print(f"  ✗ Error migrating contacts: {e}")


def verify_migration():
    """Verify the migration was successful."""

    print("\nVerifying migration...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('contacts', 'message_interactions')
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables: {', '.join(tables)}")

        # Check contact count
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        print(f"  Contacts: {contact_count}")

        # Check interaction count
        cursor.execute("SELECT COUNT(*) FROM message_interactions")
        interaction_count = cursor.fetchone()[0]
        print(f"  Interactions: {interaction_count}")

        return True

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration 002: Add contacts and message_interactions tables")
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

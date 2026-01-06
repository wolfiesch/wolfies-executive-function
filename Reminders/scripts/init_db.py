#!/usr/bin/env python3
"""
Initialize reminder_interactions table in Life Planner database.

Creates the database schema for logging reminder interactions (created, completed, deleted).
"""

import sqlite3
from pathlib import Path
import sys

# Schema for reminder_interactions table
SCHEMA = """
CREATE TABLE IF NOT EXISTS reminder_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
    action TEXT NOT NULL CHECK(action IN ('created', 'completed', 'deleted', 'updated')),
    reminder_id TEXT NOT NULL,
    title TEXT NOT NULL,
    due_date DATETIME,
    completion_date DATETIME,
    metadata TEXT,  -- JSON for additional fields (notes, list_name, etc.)
    created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_reminder_interactions_timestamp
    ON reminder_interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_reminder_interactions_action
    ON reminder_interactions(action);
CREATE INDEX IF NOT EXISTS idx_reminder_interactions_reminder_id
    ON reminder_interactions(reminder_id);
"""

def init_database(db_path: str):
    """Initialize reminder_interactions table in life planner database."""
    db_path = Path(db_path).resolve()

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print(f"Please ensure the Life Planner database exists first.")
        return False

    try:
        conn = sqlite3.connect(db_path)
        conn.executescript(SCHEMA)
        conn.commit()

        # Verify table created
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='reminder_interactions'
        """)

        if cursor.fetchone():
            print(f"✓ Successfully initialized reminder_interactions table in {db_path}")

            # Show table schema
            cursor.execute("PRAGMA table_info(reminder_interactions)")
            columns = cursor.fetchall()
            print("\nTable schema:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")

            conn.close()
            return True
        else:
            print(f"Error: Table creation failed")
            conn.close()
            return False

    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    # Default path relative to project root
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "database" / "planner.db"

    # Allow custom path via command line
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])

    print(f"Initializing database at: {db_path}")
    success = init_database(db_path)
    sys.exit(0 if success else 1)

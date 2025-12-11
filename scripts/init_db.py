#!/usr/bin/env python3
"""
Database initialization script for AI Life Planner
Creates SQLite database with core schemas for MVP version
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "data" / "database" / "planner.db"


def init_database():
    """Initialize the database with core schemas"""

    # Ensure database directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Check if database already exists
    if DB_PATH.exists():
        response = input(f"Database already exists at {DB_PATH}. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborting database initialization.")
            return False
        DB_PATH.unlink()

    print(f"Creating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")

        # ====================================================================
        # PARA Framework: Projects, Areas, Resources, Archives
        # ====================================================================
        cursor.execute("""
            CREATE TABLE para_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                para_type TEXT NOT NULL CHECK(para_type IN ('project', 'area', 'resource', 'archive')),
                description TEXT,
                parent_id INTEGER,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                FOREIGN KEY (parent_id) REFERENCES para_categories(id) ON DELETE CASCADE
            );
        """)

        cursor.execute("CREATE INDEX idx_para_type ON para_categories(para_type);")
        cursor.execute("CREATE INDEX idx_para_parent ON para_categories(parent_id);")

        cursor.execute("""
            CREATE TRIGGER para_categories_updated_at AFTER UPDATE ON para_categories
            BEGIN
                UPDATE para_categories SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)

        # ====================================================================
        # Projects
        # ====================================================================
        cursor.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT CHECK(status IN ('active', 'on_hold', 'completed', 'cancelled')) DEFAULT 'active',
                para_category_id INTEGER,
                start_date DATE,
                target_end_date DATE,
                actual_end_date DATE,
                archived BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                metadata TEXT,
                FOREIGN KEY (para_category_id) REFERENCES para_categories(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("CREATE INDEX idx_projects_para ON projects(para_category_id);")
        cursor.execute("CREATE INDEX idx_projects_status ON projects(status);")

        cursor.execute("""
            CREATE TRIGGER projects_updated_at AFTER UPDATE ON projects
            BEGIN
                UPDATE projects SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)

        # ====================================================================
        # Tasks
        # ====================================================================
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'waiting', 'done', 'cancelled')),
                priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
                para_category_id INTEGER,
                project_id INTEGER,
                parent_task_id INTEGER,
                estimated_minutes INTEGER CHECK(estimated_minutes > 0),
                actual_minutes INTEGER CHECK(actual_minutes >= 0),
                due_date DATETIME,
                scheduled_start DATETIME,
                scheduled_end DATETIME,
                completed_at DATETIME,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                tags TEXT,
                context TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
                FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (para_category_id) REFERENCES para_categories(id) ON DELETE SET NULL,
                CHECK (scheduled_start IS NULL OR scheduled_end IS NULL OR scheduled_start < scheduled_end)
            );
        """)

        # Indexes for tasks
        cursor.execute("CREATE INDEX idx_tasks_status ON tasks(status) WHERE status != 'done';")
        cursor.execute("CREATE INDEX idx_tasks_due_date ON tasks(due_date) WHERE due_date IS NOT NULL;")
        cursor.execute("CREATE INDEX idx_tasks_priority ON tasks(priority);")
        cursor.execute("CREATE INDEX idx_tasks_project_id ON tasks(project_id);")
        cursor.execute("CREATE INDEX idx_tasks_parent_id ON tasks(parent_task_id);")
        cursor.execute("CREATE INDEX idx_tasks_scheduled ON tasks(scheduled_start, scheduled_end);")
        cursor.execute("CREATE INDEX idx_tasks_para ON tasks(para_category_id);")

        cursor.execute("""
            CREATE TRIGGER tasks_updated_at AFTER UPDATE ON tasks
            BEGIN
                UPDATE tasks SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)

        # ====================================================================
        # Notes (for PKM - Personal Knowledge Management)
        # ====================================================================
        cursor.execute("""
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                note_type TEXT NOT NULL DEFAULT 'note' CHECK(note_type IN ('note', 'journal', 'meeting', 'reference')),
                para_category_id INTEGER,
                tags TEXT,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                word_count INTEGER DEFAULT 0 CHECK(word_count >= 0),
                metadata TEXT,
                FOREIGN KEY (para_category_id) REFERENCES para_categories(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("CREATE INDEX idx_notes_type ON notes(note_type);")
        cursor.execute("CREATE INDEX idx_notes_para ON notes(para_category_id);")
        cursor.execute("CREATE INDEX idx_notes_created ON notes(created_at);")

        cursor.execute("""
            CREATE TRIGGER notes_updated_at AFTER UPDATE ON notes
            BEGIN
                UPDATE notes SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)

        # ====================================================================
        # Note Links (for bi-directional linking)
        # ====================================================================
        cursor.execute("""
            CREATE TABLE note_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_note_id INTEGER NOT NULL,
                target_note_id INTEGER NOT NULL,
                link_type TEXT NOT NULL DEFAULT 'reference' CHECK(link_type IN ('reference', 'related', 'parent', 'child')),
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                FOREIGN KEY (source_note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_note_id) REFERENCES notes(id) ON DELETE CASCADE,
                UNIQUE(source_note_id, target_note_id, link_type)
            );
        """)

        cursor.execute("CREATE INDEX idx_note_links_source ON note_links(source_note_id);")
        cursor.execute("CREATE INDEX idx_note_links_target ON note_links(target_note_id);")

        # ====================================================================
        # Calendar Events (basic version for MVP)
        # ====================================================================
        cursor.execute("""
            CREATE TABLE calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                all_day BOOLEAN DEFAULT 0,
                calendar_source TEXT NOT NULL DEFAULT 'internal',
                external_id TEXT,
                status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'tentative', 'cancelled')),
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
                metadata TEXT,
                CHECK (start_time < end_time),
                UNIQUE(calendar_source, external_id)
            );
        """)

        cursor.execute("CREATE INDEX idx_events_start_time ON calendar_events(start_time);")
        cursor.execute("CREATE INDEX idx_events_end_time ON calendar_events(end_time);")
        cursor.execute("CREATE INDEX idx_events_source ON calendar_events(calendar_source);")
        cursor.execute("CREATE INDEX idx_events_status ON calendar_events(status) WHERE status != 'cancelled';")

        cursor.execute("""
            CREATE TRIGGER calendar_events_updated_at AFTER UPDATE ON calendar_events
            BEGIN
                UPDATE calendar_events SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = NEW.id;
            END;
        """)

        # ====================================================================
        # Insert default PARA categories
        # ====================================================================
        default_para = [
            ('Personal', 'area', 'Personal life and self-development'),
            ('Professional', 'area', 'Work and career'),
            ('Health', 'area', 'Physical and mental health'),
            ('Relationships', 'area', 'Family, friends, and social connections'),
            ('Finance', 'area', 'Money management and investments'),
            ('Learning', 'area', 'Education and skill development'),
        ]

        cursor.executemany(
            "INSERT INTO para_categories (name, para_type, description) VALUES (?, ?, ?)",
            default_para
        )

        conn.commit()
        print("✓ Database schema created successfully!")
        print(f"✓ Database location: {DB_PATH}")
        print(f"✓ Default PARA categories created: {len(default_para)}")

        # Display table summary
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        print(f"\n✓ Tables created: {', '.join(t[0] for t in tables)}")

        return True

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("AI Life Planner - Database Initialization")
    print("=" * 60)
    print()

    success = init_database()

    if success:
        print("\n" + "=" * 60)
        print("Database initialization complete!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Database initialization failed!")
        print("=" * 60)
        sys.exit(1)

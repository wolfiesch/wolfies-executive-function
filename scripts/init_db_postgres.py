#!/usr/bin/env python3
"""
PostgreSQL database initialization script for AI Life Planner
Creates database schema compatible with Neon PostgreSQL
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


def get_database_url():
    """Get database URL from environment variable"""
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("Error: DATABASE_URL environment variable not set")
        print("Set it to your Neon PostgreSQL connection string")
        sys.exit(1)
    return url


def init_database():
    """Initialize the PostgreSQL database with core schemas"""

    database_url = get_database_url()
    print(f"Connecting to PostgreSQL...")

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # ====================================================================
        # PARA Framework: Projects, Areas, Resources, Archives
        # ====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS para_categories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                para_type TEXT NOT NULL CHECK(para_type IN ('project', 'area', 'resource', 'archive')),
                description TEXT,
                parent_id INTEGER REFERENCES para_categories(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_para_type ON para_categories(para_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_para_parent ON para_categories(parent_id);")

        # ====================================================================
        # Projects
        # ====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT CHECK(status IN ('active', 'on_hold', 'completed', 'cancelled')) DEFAULT 'active',
                para_category_id INTEGER REFERENCES para_categories(id) ON DELETE SET NULL,
                start_date DATE,
                target_end_date DATE,
                actual_end_date DATE,
                archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_para ON projects(para_category_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);")

        # ====================================================================
        # Tasks
        # ====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'waiting', 'done', 'cancelled')),
                priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
                para_category_id INTEGER REFERENCES para_categories(id) ON DELETE SET NULL,
                project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                estimated_minutes INTEGER CHECK(estimated_minutes > 0),
                actual_minutes INTEGER CHECK(actual_minutes >= 0),
                due_date TIMESTAMP,
                scheduled_start TIMESTAMP,
                scheduled_end TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags JSONB DEFAULT '[]'::jsonb,
                context TEXT,
                CHECK (scheduled_start IS NULL OR scheduled_end IS NULL OR scheduled_start < scheduled_end)
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status) WHERE status != 'done';")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date) WHERE due_date IS NOT NULL;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_task_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks(scheduled_start, scheduled_end);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_para ON tasks(para_category_id);")

        # ====================================================================
        # Notes (for PKM - Personal Knowledge Management)
        # ====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                note_type TEXT NOT NULL DEFAULT 'note' CHECK(note_type IN ('note', 'journal', 'meeting', 'reference')),
                para_category_id INTEGER REFERENCES para_categories(id) ON DELETE SET NULL,
                tags JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                word_count INTEGER DEFAULT 0 CHECK(word_count >= 0),
                metadata JSONB
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(note_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_para ON notes(para_category_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);")

        # ====================================================================
        # Note Links (for bi-directional linking)
        # ====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_links (
                id SERIAL PRIMARY KEY,
                source_note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                target_note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                link_type TEXT NOT NULL DEFAULT 'reference' CHECK(link_type IN ('reference', 'related', 'parent', 'child')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_note_id, target_note_id, link_type)
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_links_source ON note_links(source_note_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_links_target ON note_links(target_note_id);")

        # ====================================================================
        # Calendar Events
        # ====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                all_day BOOLEAN DEFAULT FALSE,
                calendar_source TEXT NOT NULL DEFAULT 'internal',
                external_id TEXT,
                status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'tentative', 'cancelled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB,
                CHECK (start_time < end_time),
                UNIQUE(calendar_source, external_id)
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start_time ON calendar_events(start_time);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_end_time ON calendar_events(end_time);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON calendar_events(calendar_source);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON calendar_events(status) WHERE status != 'cancelled';")

        # ====================================================================
        # Create update timestamp function and triggers
        # ====================================================================
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        for table in ['para_categories', 'projects', 'tasks', 'notes', 'calendar_events']:
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)

        # ====================================================================
        # Insert default PARA categories if they don't exist
        # ====================================================================
        default_para = [
            ('Personal', 'area', 'Personal life and self-development'),
            ('Professional', 'area', 'Work and career'),
            ('Health', 'area', 'Physical and mental health'),
            ('Relationships', 'area', 'Family, friends, and social connections'),
            ('Finance', 'area', 'Money management and investments'),
            ('Learning', 'area', 'Education and skill development'),
        ]

        for name, para_type, description in default_para:
            cursor.execute("""
                INSERT INTO para_categories (name, para_type, description)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (name, para_type, description))

        conn.commit()
        print("✓ PostgreSQL database schema created successfully!")

        # Display table summary
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"✓ Tables: {', '.join(t[0] for t in tables)}")

        return True

    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("AI Life Planner - PostgreSQL Database Initialization")
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

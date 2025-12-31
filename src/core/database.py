"""
Database utilities and connection management
Supports both SQLite (local development) and PostgreSQL (production with Neon)

Usage:
    # SQLite (default for local dev, uses USE_SQLITE=1 env var)
    db = get_database()

    # PostgreSQL (production, uses DATABASE_URL env var)
    db = get_database()  # Automatically uses PostgreSQL if DATABASE_URL is set
"""

import os
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import contextmanager

# Try to import psycopg2 for PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseBase(ABC):
    """Abstract base class for database operations"""

    @abstractmethod
    def get_connection(self):
        """Get a database connection"""
        pass

    @abstractmethod
    def execute(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts"""
        pass

    @abstractmethod
    def execute_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return single result"""
        pass

    @abstractmethod
    def execute_write(self, query: str, params: Tuple = ()) -> int:
        """Execute an INSERT, UPDATE, or DELETE query"""
        pass

    def row_to_dict(self, row: Any) -> Optional[Dict[str, Any]]:
        """Convert row to dictionary"""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(row)

    def rows_to_dicts(self, rows: List[Any]) -> List[Dict[str, Any]]:
        """Convert list of rows to list of dictionaries"""
        return [self.row_to_dict(row) for row in rows if row is not None]


class SQLiteDatabase(DatabaseBase):
    """SQLite database implementation for local development"""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "database" / "planner.db"

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. "
                "Run 'python scripts/init_db.py' to create it."
            )

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def execute_write(self, query: str, params: Tuple = ()) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        result = self.execute_one(query, (table_name,))
        return result is not None

    def get_table_names(self) -> List[str]:
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        rows = self.execute(query)
        return [row['name'] for row in rows]

    def count(self, table_name: str, where_clause: str = "", params: Tuple = ()) -> int:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        result = self.execute_one(query, params)
        return result['count'] if result else 0

    @contextmanager
    def transaction(self):
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise


class PostgreSQLDatabase(DatabaseBase):
    """PostgreSQL database implementation for production (Neon)"""

    def __init__(self, database_url: str):
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "psycopg2 not installed. Run: pip install psycopg2-binary"
            )
        self.database_url = database_url
        self.db_path = database_url  # For compatibility with existing code

    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
        finally:
            conn.close()

    def _convert_query(self, query: str) -> str:
        """Convert SQLite-style ? placeholders to PostgreSQL %s"""
        return query.replace('?', '%s')

    def _convert_query_syntax(self, query: str) -> str:
        """Convert SQLite syntax to PostgreSQL syntax"""
        import re

        # Convert json_extract(metadata, '$.is_goal') = 1 -> (metadata->>'is_goal')::boolean = true
        pattern = r"json_extract\((\w+),\s*'\$\.(\w+)'\)\s*=\s*(\d+)"

        def json_replacer(match):
            column = match.group(1)
            field = match.group(2)
            value = match.group(3)
            if value == '1':
                return f"({column}->>'{field}')::boolean = true"
            elif value == '0':
                return f"({column}->>'{field}')::boolean = false"
            else:
                return f"({column}->>'{field}')::int = {value}"

        query = re.sub(pattern, json_replacer, query)

        # Pattern: json_extract(column, '$.field')
        pattern2 = r"json_extract\((\w+),\s*'\$\.(\w+)'\)"

        def json_replacer2(match):
            column = match.group(1)
            field = match.group(2)
            return f"({column}->>'{field}')"

        query = re.sub(pattern2, json_replacer2, query)

        # Convert boolean comparisons: column = 0/1 -> column = false/true
        # Only for known boolean columns
        boolean_columns = ['archived', 'all_day', 'is_pinned']
        for col in boolean_columns:
            query = re.sub(rf'\b{col}\s*=\s*0\b', f'{col} = false', query)
            query = re.sub(rf'\b{col}\s*=\s*1\b', f'{col} = true', query)

        return query

    def execute(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        query = self._convert_query(query)
        query = self._convert_query_syntax(query)

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

    def execute_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        query = self._convert_query(query)
        query = self._convert_query_syntax(query)

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None

    def execute_write(self, query: str, params: Tuple = ()) -> int:
        query = self._convert_query(query)
        query = self._convert_query_syntax(query)

        # Add RETURNING id for INSERT statements to get the inserted ID
        is_insert = query.strip().upper().startswith('INSERT')
        if is_insert and 'RETURNING' not in query.upper():
            query = query.rstrip(';') + ' RETURNING id'

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                if is_insert:
                    result = cursor.fetchone()
                    return result[0] if result else 0
                return cursor.rowcount

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        query = self._convert_query(query)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        query = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s;
        """
        result = self.execute_one(query, (table_name,))
        return result is not None

    def get_table_names(self) -> List[str]:
        query = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name;
        """
        rows = self.execute(query)
        return [row['table_name'] for row in rows]

    def count(self, table_name: str, where_clause: str = "", params: Tuple = ()) -> int:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            where_clause = self._convert_query(where_clause)
            query += f" WHERE {where_clause}"
        result = self.execute_one(query, params)
        return result['count'] if result else 0

    @contextmanager
    def transaction(self):
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise


# Type alias for backwards compatibility
Database = Union[SQLiteDatabase, PostgreSQLDatabase]


def get_database() -> Union[SQLiteDatabase, PostgreSQLDatabase]:
    """
    Factory function to get the appropriate database instance.

    Uses PostgreSQL if DATABASE_URL is set, otherwise falls back to SQLite.
    Set USE_SQLITE=1 to force SQLite even if DATABASE_URL is set.
    """
    use_sqlite = os.environ.get('USE_SQLITE', '').lower() in ('1', 'true', 'yes')
    database_url = os.environ.get('DATABASE_URL')

    if database_url and not use_sqlite:
        return PostgreSQLDatabase(database_url)
    else:
        return SQLiteDatabase()


# Backwards compatibility - Database class that auto-detects
class AutoDatabase:
    """Backwards-compatible Database class that auto-detects the backend"""

    def __new__(cls, db_path: Optional[Path] = None):
        use_sqlite = os.environ.get('USE_SQLITE', '').lower() in ('1', 'true', 'yes')
        database_url = os.environ.get('DATABASE_URL')

        if database_url and not use_sqlite:
            return PostgreSQLDatabase(database_url)
        else:
            return SQLiteDatabase(db_path)

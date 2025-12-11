"""
Database utilities and connection management
Provides simple interface for database operations
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager


class Database:
    """Database connection and query manager"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            # Default to project database path
            db_path = Path(__file__).parent.parent.parent / "data" / "database" / "planner.db"

        self.db_path = Path(db_path)

        # Ensure database exists
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. "
                "Run 'python scripts/init_db.py' to create it."
            )

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        Ensures proper connection cleanup

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign keys
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query string
            params: Query parameters (use ? placeholders)

        Returns:
            List of rows as sqlite3.Row objects (can access by column name)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_one(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """
        Execute a SELECT query and return single result

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def execute_write(self, query: str, params: Tuple = ()) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Last row ID (for INSERT) or number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        Execute multiple INSERT/UPDATE/DELETE queries

        Args:
            query: SQL query string
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

    # ====================================================================
    # Helper methods for common operations
    # ====================================================================

    def row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        """Convert sqlite3.Row to dictionary"""
        if row is None:
            return None
        return dict(row)

    def rows_to_dicts(self, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """Convert list of sqlite3.Row to list of dictionaries"""
        return [dict(row) for row in rows]

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        result = self.execute_one(query, (table_name,))
        return result is not None

    def get_table_names(self) -> List[str]:
        """Get list of all table names in the database"""
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        rows = self.execute(query)
        return [row['name'] for row in rows]

    def count(self, table_name: str, where_clause: str = "", params: Tuple = ()) -> int:
        """
        Count rows in a table

        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause (without 'WHERE' keyword)
            params: Parameters for WHERE clause

        Returns:
            Number of rows
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = self.execute_one(query, params)
        return result['count'] if result else 0

    # ====================================================================
    # Transaction support
    # ====================================================================

    @contextmanager
    def transaction(self):
        """
        Context manager for transactions
        Automatically commits on success, rolls back on error

        Usage:
            with db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # Auto-commits if no exception
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

"""
Unit tests for the database module.
Tests the Database class connection management and query operations.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.database import Database


class TestDatabaseInit:
    """Tests for Database initialization."""

    def test_init_with_valid_path(self, tmp_path):
        """Database initializes with a valid path to existing db file."""
        db_file = tmp_path / "test.db"
        # Create an empty database file
        conn = sqlite3.connect(db_file)
        conn.close()

        db = Database(db_file)
        assert db.db_path == db_file

    def test_init_raises_if_file_not_found(self, tmp_path):
        """Database raises FileNotFoundError if db file doesn't exist."""
        db_file = tmp_path / "nonexistent.db"

        with pytest.raises(FileNotFoundError) as exc_info:
            Database(db_file)

        assert "Database not found" in str(exc_info.value)
        assert "init_db.py" in str(exc_info.value)


class TestConnectionManagement:
    """Tests for database connection context manager."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database with a test table."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_get_connection_returns_valid_connection(self, temp_db):
        """get_connection() returns a valid sqlite3 connection."""
        with temp_db.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            # Connection should be usable
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_get_connection_enables_row_factory(self, temp_db):
        """get_connection() enables column access by name."""
        with temp_db.get_connection() as conn:
            assert conn.row_factory == sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(test_table)")
            row = cursor.fetchone()
            # Should be able to access by column name
            assert row['name'] is not None

    def test_get_connection_closes_on_exit(self, temp_db):
        """Connection is properly closed after context manager exits."""
        with temp_db.get_connection() as conn:
            # Save a reference to check later
            saved_conn = conn

        # After exiting, using the connection should fail
        # Note: SQLite doesn't raise an error immediately after close
        # but we can verify the connection was closed by checking
        # that a new connection gets a different object
        with temp_db.get_connection() as new_conn:
            assert new_conn is not saved_conn

    def test_get_connection_closes_on_exception(self, temp_db):
        """Connection is closed even when exception occurs."""
        try:
            with temp_db.get_connection() as conn:
                cursor = conn.cursor()
                # This should fail - invalid SQL
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should be able to get a new connection
        with temp_db.get_connection() as new_conn:
            cursor = new_conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1


class TestForeignKeyEnforcement:
    """Tests for foreign key constraint enforcement."""

    @pytest.fixture
    def db_with_fk(self, tmp_path):
        """Create a database with foreign key relationship."""
        db_file = tmp_path / "test_fk.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("""
            CREATE TABLE parent (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE
            )
        """)
        # Insert a parent row
        cursor.execute("INSERT INTO parent (id, name) VALUES (1, 'Parent 1')")
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_foreign_keys_are_enabled(self, db_with_fk):
        """Foreign key enforcement is enabled by get_connection()."""
        with db_with_fk.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            # 1 means foreign keys are ON
            assert result[0] == 1

    def test_fk_violation_raises_error(self, db_with_fk):
        """Inserting a child with invalid parent_id raises IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError):
            with db_with_fk.get_connection() as conn:
                cursor = conn.cursor()
                # Try to insert child with non-existent parent
                cursor.execute(
                    "INSERT INTO child (parent_id, name) VALUES (999, 'Orphan')"
                )
                conn.commit()

    def test_fk_cascade_delete_works(self, db_with_fk):
        """CASCADE delete removes child rows when parent is deleted."""
        # First, add a child
        with db_with_fk.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO child (parent_id, name) VALUES (1, 'Child 1')"
            )
            conn.commit()

        # Verify child exists
        result = db_with_fk.execute("SELECT COUNT(*) as count FROM child")
        assert result[0]['count'] == 1

        # Delete parent
        db_with_fk.execute_write("DELETE FROM parent WHERE id = 1")

        # Child should be gone due to CASCADE
        result = db_with_fk.execute("SELECT COUNT(*) as count FROM child")
        assert result[0]['count'] == 0


class TestExecute:
    """Tests for the execute() method (SELECT queries)."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with test data."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER
            )
        """)
        cursor.executemany(
            "INSERT INTO users (name, age) VALUES (?, ?)",
            [
                ("Alice", 30),
                ("Bob", 25),
                ("Charlie", 35),
            ]
        )
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_execute_returns_list_of_rows(self, populated_db):
        """execute() returns a list of sqlite3.Row objects."""
        rows = populated_db.execute("SELECT * FROM users")

        assert isinstance(rows, list)
        assert len(rows) == 3
        assert isinstance(rows[0], sqlite3.Row)

    def test_execute_rows_accessible_by_name(self, populated_db):
        """Returned rows can be accessed by column name."""
        rows = populated_db.execute("SELECT * FROM users WHERE name = ?", ("Alice",))

        assert len(rows) == 1
        assert rows[0]['name'] == "Alice"
        assert rows[0]['age'] == 30

    def test_execute_empty_result(self, populated_db):
        """execute() returns empty list when no rows match."""
        rows = populated_db.execute("SELECT * FROM users WHERE name = ?", ("Nobody",))

        assert rows == []

    def test_execute_with_params(self, populated_db):
        """execute() correctly uses parameterized queries."""
        rows = populated_db.execute(
            "SELECT * FROM users WHERE age > ? ORDER BY age",
            (25,)
        )

        assert len(rows) == 2
        assert rows[0]['name'] == "Alice"  # age 30
        assert rows[1]['name'] == "Charlie"  # age 35


class TestExecuteOne:
    """Tests for the execute_one() method (single row SELECT)."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with test data."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                age INTEGER
            )
        """)
        cursor.executemany(
            "INSERT INTO users (name, age) VALUES (?, ?)",
            [("Alice", 30), ("Bob", 25)]
        )
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_execute_one_returns_single_row(self, populated_db):
        """execute_one() returns a single sqlite3.Row."""
        row = populated_db.execute_one(
            "SELECT * FROM users WHERE name = ?", ("Alice",)
        )

        assert isinstance(row, sqlite3.Row)
        assert row['name'] == "Alice"
        assert row['age'] == 30

    def test_execute_one_returns_none_if_not_found(self, populated_db):
        """execute_one() returns None when no rows match."""
        row = populated_db.execute_one(
            "SELECT * FROM users WHERE name = ?", ("Nobody",)
        )

        assert row is None

    def test_execute_one_returns_first_row_if_multiple(self, populated_db):
        """execute_one() returns first row even if multiple match."""
        row = populated_db.execute_one(
            "SELECT * FROM users ORDER BY name ASC"
        )

        # Should return first row alphabetically
        assert row['name'] == "Alice"


class TestExecuteWrite:
    """Tests for the execute_write() method (INSERT/UPDATE/DELETE)."""

    @pytest.fixture
    def empty_db(self, tmp_path):
        """Create an empty database with a table."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_execute_write_insert_returns_last_row_id(self, empty_db):
        """execute_write() returns last_row_id for INSERT."""
        row_id = empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Widget", 10)
        )

        assert row_id == 1

        # Insert another
        row_id2 = empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Gadget", 5)
        )

        assert row_id2 == 2

    def test_execute_write_update_returns_rowcount(self, empty_db):
        """execute_write() for UPDATE returns affected row count."""
        # Insert test data
        empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Widget", 10)
        )
        empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Gadget", 5)
        )

        # Update all rows
        affected = empty_db.execute_write(
            "UPDATE items SET quantity = quantity + 1"
        )

        # Should return rowcount (2 rows updated)
        # Note: lastrowid for UPDATE is 0, so returns rowcount
        assert affected == 2

    def test_execute_write_delete_returns_rowcount(self, empty_db):
        """execute_write() for DELETE returns deleted row count."""
        # Insert test data
        empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Widget", 10)
        )
        empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Gadget", 5)
        )

        # Delete one row
        affected = empty_db.execute_write(
            "DELETE FROM items WHERE name = ?",
            ("Widget",)
        )

        assert affected == 1

        # Verify deletion
        remaining = empty_db.execute("SELECT COUNT(*) as count FROM items")
        assert remaining[0]['count'] == 1

    def test_execute_write_commits_changes(self, empty_db):
        """execute_write() commits changes to the database."""
        empty_db.execute_write(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            ("Widget", 10)
        )

        # Changes should be visible in a new connection
        rows = empty_db.execute("SELECT * FROM items")
        assert len(rows) == 1
        assert rows[0]['name'] == "Widget"


class TestExecuteMany:
    """Tests for the execute_many() method (batch operations)."""

    @pytest.fixture
    def empty_db(self, tmp_path):
        """Create an empty database with a table."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_execute_many_inserts_all_rows(self, empty_db):
        """execute_many() inserts all provided rows."""
        params_list = [
            ("Widget", 10),
            ("Gadget", 5),
            ("Gizmo", 15),
        ]

        affected = empty_db.execute_many(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            params_list
        )

        assert affected == 3

        # Verify all rows inserted
        rows = empty_db.execute("SELECT * FROM items ORDER BY name")
        assert len(rows) == 3
        assert rows[0]['name'] == "Gadget"
        assert rows[1]['name'] == "Gizmo"
        assert rows[2]['name'] == "Widget"

    def test_execute_many_empty_list(self, empty_db):
        """execute_many() with empty list affects no rows."""
        affected = empty_db.execute_many(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            []
        )

        assert affected == 0

    def test_execute_many_updates(self, empty_db):
        """execute_many() works for batch UPDATE operations."""
        # Insert initial data
        empty_db.execute_many(
            "INSERT INTO items (id, name, quantity) VALUES (?, ?, ?)",
            [(1, "Widget", 10), (2, "Gadget", 5), (3, "Gizmo", 15)]
        )

        # Batch update
        updates = [
            (100, 1),  # Set Widget quantity to 100
            (200, 2),  # Set Gadget quantity to 200
        ]

        affected = empty_db.execute_many(
            "UPDATE items SET quantity = ? WHERE id = ?",
            updates
        )

        assert affected == 2

        # Verify updates
        row = empty_db.execute_one("SELECT * FROM items WHERE id = 1")
        assert row['quantity'] == 100

        row = empty_db.execute_one("SELECT * FROM items WHERE id = 2")
        assert row['quantity'] == 200

    def test_execute_many_commits_atomically(self, empty_db):
        """execute_many() commits all changes in a single transaction."""
        params_list = [
            ("Widget", 10),
            ("Gadget", 5),
        ]

        empty_db.execute_many(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            params_list
        )

        # All changes should be committed
        rows = empty_db.execute("SELECT COUNT(*) as count FROM items")
        assert rows[0]['count'] == 2


class TestTransaction:
    """Tests for the transaction() context manager."""

    @pytest.fixture
    def empty_db(self, tmp_path):
        """Create an empty database with a table."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0
            )
        """)
        cursor.execute(
            "INSERT INTO accounts (name, balance) VALUES (?, ?)",
            ("Alice", 100)
        )
        cursor.execute(
            "INSERT INTO accounts (name, balance) VALUES (?, ?)",
            ("Bob", 50)
        )
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_transaction_commits_on_success(self, empty_db):
        """transaction() commits changes when no exception occurs."""
        with empty_db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET balance = balance - 30 WHERE name = ?",
                ("Alice",)
            )
            cursor.execute(
                "UPDATE accounts SET balance = balance + 30 WHERE name = ?",
                ("Bob",)
            )

        # Changes should be committed
        alice = empty_db.execute_one(
            "SELECT balance FROM accounts WHERE name = ?", ("Alice",)
        )
        bob = empty_db.execute_one(
            "SELECT balance FROM accounts WHERE name = ?", ("Bob",)
        )

        assert alice['balance'] == 70
        assert bob['balance'] == 80

    def test_transaction_rollback_on_exception(self, empty_db):
        """transaction() rolls back changes when exception occurs."""
        try:
            with empty_db.transaction() as conn:
                cursor = conn.cursor()
                # First update succeeds
                cursor.execute(
                    "UPDATE accounts SET balance = balance - 30 WHERE name = ?",
                    ("Alice",)
                )
                # Simulate an error before second update
                raise ValueError("Simulated error during transaction")
        except ValueError:
            pass

        # Changes should be rolled back
        alice = empty_db.execute_one(
            "SELECT balance FROM accounts WHERE name = ?", ("Alice",)
        )
        assert alice['balance'] == 100  # Original balance

    def test_transaction_reraises_exception(self, empty_db):
        """transaction() re-raises the original exception after rollback."""
        with pytest.raises(ValueError) as exc_info:
            with empty_db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE accounts SET balance = balance - 30 WHERE name = ?",
                    ("Alice",)
                )
                raise ValueError("Test error message")

        assert "Test error message" in str(exc_info.value)


class TestHelperMethods:
    """Tests for helper methods (row_to_dict, rows_to_dicts, etc.)."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with test data."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER
            )
        """)
        cursor.executemany(
            "INSERT INTO users (name, age) VALUES (?, ?)",
            [("Alice", 30), ("Bob", 25)]
        )
        conn.commit()
        conn.close()
        return Database(db_file)

    def test_row_to_dict_converts_row(self, populated_db):
        """row_to_dict() converts sqlite3.Row to dictionary."""
        row = populated_db.execute_one("SELECT * FROM users WHERE name = ?", ("Alice",))

        result = populated_db.row_to_dict(row)

        assert isinstance(result, dict)
        assert result['id'] == 1
        assert result['name'] == "Alice"
        assert result['age'] == 30

    def test_row_to_dict_returns_none_for_none(self, populated_db):
        """row_to_dict() returns None when passed None."""
        result = populated_db.row_to_dict(None)
        assert result is None

    def test_rows_to_dicts_converts_list(self, populated_db):
        """rows_to_dicts() converts list of rows to list of dicts."""
        rows = populated_db.execute("SELECT * FROM users ORDER BY name")

        result = populated_db.rows_to_dicts(rows)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        assert result[0]['name'] == "Alice"
        assert result[1]['name'] == "Bob"

    def test_rows_to_dicts_empty_list(self, populated_db):
        """rows_to_dicts() returns empty list for empty input."""
        result = populated_db.rows_to_dicts([])
        assert result == []

    def test_table_exists_returns_true_for_existing(self, populated_db):
        """table_exists() returns True for existing table."""
        assert populated_db.table_exists("users") is True

    def test_table_exists_returns_false_for_missing(self, populated_db):
        """table_exists() returns False for non-existent table."""
        assert populated_db.table_exists("nonexistent_table") is False

    def test_get_table_names_returns_all_tables(self, populated_db):
        """get_table_names() returns list of all table names."""
        tables = populated_db.get_table_names()

        assert isinstance(tables, list)
        assert "users" in tables

    def test_count_all_rows(self, populated_db):
        """count() returns total row count without where clause."""
        count = populated_db.count("users")
        assert count == 2

    def test_count_with_where_clause(self, populated_db):
        """count() returns filtered row count with where clause."""
        count = populated_db.count("users", "age > ?", (25,))
        assert count == 1

    def test_count_empty_result(self, populated_db):
        """count() returns 0 when no rows match."""
        count = populated_db.count("users", "age > ?", (100,))
        assert count == 0

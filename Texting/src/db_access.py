"""Security-scoped bookmark management for chat.db access.

This module provides FDA-free access to the Messages database by using
macOS security-scoped bookmarks. Users select the file once via a file
picker, and the bookmark persists across sessions.

CHANGELOG:
- 01/09/2026 - Initial implementation with NSOpenPanel + security-scoped bookmarks (Claude)
"""

import base64
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BOOKMARK_FILE = PROJECT_ROOT / "config" / "db_access.json"
DEFAULT_DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"


class DatabaseAccessError(Exception):
    """Error accessing the Messages database."""
    pass


class DatabaseAccess:
    """Manages security-scoped bookmark access to chat.db.

    Usage:
        db = DatabaseAccess()
        if db.has_access():
            with db.scoped_access() as db_path:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                # ... use connection
        else:
            db.request_access()  # Shows file picker
    """

    def __init__(self):
        self._bookmark_data: Optional[bytes] = None
        self._db_path: Optional[Path] = None
        self._active_url = None
        self._scope_active = False
        self._load_bookmark()

    def _load_bookmark(self) -> None:
        """Load stored bookmark from config file."""
        if not BOOKMARK_FILE.exists():
            logger.debug("No bookmark file found at %s", BOOKMARK_FILE)
            return

        try:
            with open(BOOKMARK_FILE, 'r') as f:
                data = json.load(f)

            if 'bookmark' in data:
                self._bookmark_data = base64.b64decode(data['bookmark'])
                self._db_path = Path(data.get('path', ''))
                logger.debug("Loaded bookmark for %s", self._db_path)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to load bookmark: %s", e)
            self._bookmark_data = None
            self._db_path = None

    def _save_bookmark(self, bookmark_data: bytes, path: Path) -> None:
        """Save bookmark to config file."""
        BOOKMARK_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'bookmark': base64.b64encode(bookmark_data).decode('ascii'),
            'path': str(path),
            'version': 1
        }

        with open(BOOKMARK_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info("Saved bookmark for %s", path)

    def has_access(self) -> bool:
        """Check if we have a valid stored bookmark.

        Returns True if bookmark exists and can be resolved (not stale).
        """
        if not self._bookmark_data:
            return False

        # Try to resolve bookmark to check if it's still valid
        try:
            from Foundation import NSURL, NSURLBookmarkResolutionWithSecurityScope

            resolved_url, is_stale, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
                self._bookmark_data,
                NSURLBookmarkResolutionWithSecurityScope,
                None,
                None,
                None
            )

            if error:
                logger.warning("Bookmark resolution error: %s", error)
                return False

            if is_stale:
                logger.warning("Bookmark is stale, will need to re-select file")
                return False

            return resolved_url is not None

        except ImportError:
            # PyObjC not available, fall back to path check
            return self._db_path is not None and self._db_path.exists()
        except Exception as e:
            logger.warning("Error checking bookmark: %s", e)
            return False

    def get_db_path(self) -> Optional[Path]:
        """Get the database path (requires active security scope for full access)."""
        return self._db_path

    def request_access(self) -> bool:
        """Show file picker and create security-scoped bookmark.

        Returns True if access was granted, False if cancelled.
        """
        from src.file_picker import select_database_file, create_security_scoped_bookmark

        # Show file picker
        selected_path = select_database_file()
        if not selected_path:
            logger.info("File picker cancelled")
            return False

        # Validate it's a valid Messages database
        if not self._validate_database(selected_path):
            logger.error("Selected file is not a valid Messages database")
            return False

        # Create security-scoped bookmark
        bookmark_data = create_security_scoped_bookmark(selected_path)
        if not bookmark_data:
            logger.warning("Failed to create security-scoped bookmark, using path directly")
            # Fall back to just storing the path
            self._db_path = selected_path
            self._save_bookmark(b'', selected_path)
            return True

        # Save bookmark
        self._bookmark_data = bookmark_data
        self._db_path = selected_path
        self._save_bookmark(bookmark_data, selected_path)

        return True

    def _validate_database(self, path: Path) -> bool:
        """Validate that the file is a valid Messages database."""
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Check for expected tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {'message', 'handle', 'chat'}
            if not required_tables.issubset(tables):
                logger.warning("Database missing required tables. Found: %s", tables)
                conn.close()
                return False

            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error("Database validation failed: %s", e)
            return False

    def start_access(self) -> bool:
        """Start security-scoped resource access.

        Must be called before accessing the database file.
        Returns True if access started successfully.
        """
        if self._scope_active:
            return True

        if not self._bookmark_data:
            # No bookmark, assume direct access (FDA mode)
            return True

        try:
            from Foundation import NSURL, NSURLBookmarkResolutionWithSecurityScope

            resolved_url, is_stale, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
                self._bookmark_data,
                NSURLBookmarkResolutionWithSecurityScope,
                None,
                None,
                None
            )

            if error or not resolved_url:
                logger.error("Failed to resolve bookmark: %s", error)
                return False

            if is_stale:
                logger.warning("Bookmark is stale")
                return False

            # Start accessing the security-scoped resource
            success = resolved_url.startAccessingSecurityScopedResource()
            if success:
                self._active_url = resolved_url
                self._scope_active = True
                logger.debug("Started security-scoped access to %s", self._db_path)

            return success

        except ImportError:
            # PyObjC not available, assume direct access
            return True
        except Exception as e:
            logger.error("Error starting access: %s", e)
            return False

    def stop_access(self) -> None:
        """Stop security-scoped resource access.

        Should be called after done accessing the database.
        """
        if not self._scope_active or not self._active_url:
            return

        try:
            self._active_url.stopAccessingSecurityScopedResource()
            self._scope_active = False
            self._active_url = None
            logger.debug("Stopped security-scoped access")
        except Exception as e:
            logger.warning("Error stopping access: %s", e)

    @contextmanager
    def scoped_access(self):
        """Context manager for security-scoped access.

        Usage:
            with db_access.scoped_access() as db_path:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                # ... use connection
        """
        if not self.start_access():
            raise DatabaseAccessError("Failed to start security-scoped access")

        try:
            yield self._db_path
        finally:
            self.stop_access()

    def clear_bookmark(self) -> None:
        """Clear stored bookmark (for reconfiguration)."""
        if BOOKMARK_FILE.exists():
            BOOKMARK_FILE.unlink()
        self._bookmark_data = None
        self._db_path = None
        self._active_url = None
        self._scope_active = False
        logger.info("Cleared stored bookmark")


def is_headless_environment() -> bool:
    """Detect if running in headless/SSH environment where GUI is unavailable."""
    import os

    # Check for SSH session
    if os.environ.get('SSH_CLIENT') or os.environ.get('SSH_TTY'):
        return True

    # Check for common CI environments
    ci_vars = ['CI', 'CONTINUOUS_INTEGRATION', 'GITHUB_ACTIONS', 'JENKINS_URL']
    if any(os.environ.get(var) for var in ci_vars):
        return True

    # macOS-specific: check if we can connect to WindowServer
    try:
        from AppKit import NSApp
        # If we can import AppKit, we're probably in a GUI environment
        return False
    except ImportError:
        return True
    except Exception:
        # Other errors might indicate no GUI
        return True

"""Native macOS file picker for database selection.

Uses NSOpenPanel for a native macOS file picker experience and
creates security-scoped bookmarks for persistent access.

CHANGELOG:
- 01/09/2026 - Initial implementation with NSOpenPanel + security-scoped bookmarks (Claude)
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def select_database_file(
    title: str = "Select Messages Database",
    message: str = "Navigate to ~/Library/Messages/chat.db",
    initial_dir: Optional[Path] = None
) -> Optional[Path]:
    """Show native macOS file picker to select a database file.

    Args:
        title: Window title for the file picker
        message: Instructional message shown in the picker
        initial_dir: Directory to start in (defaults to ~/Library/Messages)

    Returns:
        Selected file path, or None if cancelled.
    """
    try:
        from AppKit import NSOpenPanel, NSModalResponseOK
        from Foundation import NSURL
    except ImportError as e:
        logger.error("PyObjC not available: %s", e)
        logger.info("Install with: pip install pyobjc-framework-Cocoa")
        return _fallback_file_picker()

    # Set default initial directory
    if initial_dir is None:
        initial_dir = Path.home() / "Library" / "Messages"

    try:
        # Create and configure the panel
        panel = NSOpenPanel.openPanel()
        panel.setTitle_(title)
        panel.setMessage_(message)
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setAllowedFileTypes_(["db", "sqlite", "sqlite3"])

        # Try to set initial directory
        if initial_dir.exists():
            panel.setDirectoryURL_(NSURL.fileURLWithPath_(str(initial_dir)))

        # Allow navigation to hidden directories (Library is sometimes hidden)
        panel.setShowsHiddenFiles_(True)

        # Run modal dialog (blocks until user responds)
        result = panel.runModal()

        if result == NSModalResponseOK:
            url = panel.URL()
            if url:
                selected_path = Path(url.path())
                logger.info("User selected: %s", selected_path)
                return selected_path

        logger.info("File picker cancelled by user")
        return None

    except Exception as e:
        logger.error("Error showing file picker: %s", e)
        return _fallback_file_picker()


def _fallback_file_picker() -> Optional[Path]:
    """Fallback file picker using tkinter if PyObjC fails."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create hidden root window
        root = tk.Tk()
        root.withdraw()

        # Set initial directory
        initial_dir = Path.home() / "Library" / "Messages"
        if not initial_dir.exists():
            initial_dir = Path.home()

        # Show file dialog
        file_path = filedialog.askopenfilename(
            title="Select Messages Database",
            initialdir=str(initial_dir),
            filetypes=[
                ("Database files", "*.db *.sqlite *.sqlite3"),
                ("All files", "*.*")
            ]
        )

        root.destroy()

        if file_path:
            return Path(file_path)
        return None

    except Exception as e:
        logger.error("Fallback file picker also failed: %s", e)
        return None


def create_security_scoped_bookmark(file_path: Path) -> Optional[bytes]:
    """Create a security-scoped bookmark for the given file.

    Security-scoped bookmarks allow persistent access to files outside
    the app's sandbox, surviving across app restarts.

    Args:
        file_path: Path to the file to create a bookmark for

    Returns:
        Bookmark data as bytes, or None if creation failed.
    """
    try:
        from Foundation import NSURL, NSURLBookmarkCreationWithSecurityScope
    except ImportError as e:
        logger.warning("Foundation framework not available: %s", e)
        return None

    try:
        # Create NSURL from path
        file_url = NSURL.fileURLWithPath_(str(file_path))

        # Create security-scoped bookmark
        bookmark_data, error = file_url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
            NSURLBookmarkCreationWithSecurityScope,
            None,  # No additional resource values needed
            None,  # No relative URL
            None   # Error output
        )

        if error:
            logger.error("Failed to create bookmark: %s", error)
            return None

        if bookmark_data:
            logger.info("Created security-scoped bookmark for %s", file_path)
            return bytes(bookmark_data)

        return None

    except Exception as e:
        logger.error("Error creating bookmark: %s", e)
        return None


def resolve_security_scoped_bookmark(bookmark_data: bytes) -> tuple[Optional[Path], bool]:
    """Resolve a security-scoped bookmark to a file path.

    Args:
        bookmark_data: The bookmark data to resolve

    Returns:
        Tuple of (resolved_path, is_stale). is_stale indicates if the
        bookmark needs to be recreated.
    """
    try:
        from Foundation import NSURL, NSURLBookmarkResolutionWithSecurityScope
    except ImportError:
        return None, True

    try:
        resolved_url, is_stale, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
            bookmark_data,
            NSURLBookmarkResolutionWithSecurityScope,
            None,
            None,
            None
        )

        if error:
            logger.error("Bookmark resolution error: %s", error)
            return None, True

        if resolved_url:
            return Path(resolved_url.path()), bool(is_stale)

        return None, True

    except Exception as e:
        logger.error("Error resolving bookmark: %s", e)
        return None, True


def prompt_for_database_access() -> Optional[Path]:
    """High-level function to prompt user for database access.

    Shows helpful instructions before opening the file picker.

    Returns:
        Selected database path, or None if cancelled.
    """
    print("\n" + "=" * 60)
    print("Messages Database Access Setup")
    print("=" * 60)
    print()
    print("To read your iMessages, we need access to the Messages database.")
    print()
    print("A file picker will open. Please navigate to:")
    print("  ~/Library/Messages/chat.db")
    print()
    print("Tip: Press Cmd+Shift+G to enter path directly")
    print()
    print("This grants one-time access. The access is saved for future use.")
    print("=" * 60 + "\n")

    # Prompt user to continue
    try:
        response = input("Press Enter to open file picker (or 'q' to cancel): ")
        if response.lower() == 'q':
            return None
    except (EOFError, KeyboardInterrupt):
        return None

    return select_database_file()

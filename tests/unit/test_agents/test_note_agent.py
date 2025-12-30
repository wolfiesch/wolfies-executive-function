"""
Unit tests for the NoteAgent.
Tests note type detection, tag extraction, intent handling, file path generation,
and error handling with database integration.
"""

import pytest
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import tempfile
import shutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.note_agent import NoteAgent
from src.agents.base_agent import AgentResponse
from src.core.database import Database


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary in-memory database with the notes table schema."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create notes table matching production schema
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
            metadata TEXT
        )
    """)

    # Create note_links table matching production schema
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
        )
    """)

    conn.commit()
    conn.close()

    return Database(db_file)


@pytest.fixture
def temp_notes_dir(tmp_path):
    """Create a temporary directory for markdown files."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    # Create subdirectories for note types
    for subdir in ["notes", "journals", "meetings", "references", "archive"]:
        (notes_dir / subdir).mkdir()
    return notes_dir


@pytest.fixture
def mock_config(temp_notes_dir):
    """Create a mock config object that returns the temp notes directory."""
    config = MagicMock()
    config.get_notes_directory.return_value = temp_notes_dir
    return config


@pytest.fixture
def note_agent(temp_db, mock_config):
    """Create a NoteAgent instance with test database and config."""
    agent = NoteAgent(temp_db, mock_config)
    agent.initialize()
    return agent


@pytest.fixture
def populated_db(temp_db, temp_notes_dir):
    """Populate the test database with sample notes and create corresponding files."""
    notes = [
        ("Python Decorators", "notes/2025-01-01_python-decorators.md", "note", '["python", "learning"]', 150),
        ("Journal - 2025-01-01", "journals/2025-01-01_journal-2025-01-01.md", "journal", '["journal"]', 200),
        ("Meeting with Team", "meetings/2025-01-01_meeting-with-team.md", "meeting", '["work", "team"]', 100),
        ("API Documentation", "references/2025-01-01_api-documentation.md", "reference", '["api", "docs"]', 500),
        ("Quick Note", "notes/2025-01-02_quick-note.md", "note", None, 25),
    ]

    for title, file_path, note_type, tags, word_count in notes:
        temp_db.execute_write(
            """INSERT INTO notes
               (title, file_path, note_type, tags, word_count)
               VALUES (?, ?, ?, ?, ?)""",
            (title, file_path, note_type, tags, word_count)
        )

        # Create actual markdown files
        full_path = temp_notes_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"---\ntitle: {title}\ntype: {note_type}\n---\n\n# {title}\n\nSample content for {title}."
        full_path.write_text(content, encoding="utf-8")

    return temp_db


@pytest.fixture
def note_agent_with_data(populated_db, mock_config):
    """Create a NoteAgent with pre-populated test data."""
    agent = NoteAgent(populated_db, mock_config)
    agent.initialize()
    return agent


# =============================================================================
# Test Agent Initialization and Basic Properties
# =============================================================================

class TestNoteAgentInit:
    """Tests for NoteAgent initialization."""

    def test_agent_initializes_correctly(self, note_agent):
        """NoteAgent initializes with correct name and properties."""
        assert note_agent.name == "note"
        assert note_agent._initialized is True

    def test_get_supported_intents(self, note_agent):
        """get_supported_intents returns all expected intents."""
        intents = note_agent.get_supported_intents()

        expected = [
            "create_note", "get_note", "list_notes",
            "search_notes", "update_note", "delete_note",
            "add_journal_entry", "link_notes", "get_linked_notes"
        ]

        for intent in expected:
            assert intent in intents

    def test_can_handle_supported_intents(self, note_agent):
        """can_handle returns True for supported intents."""
        assert note_agent.can_handle("create_note", {}) is True
        assert note_agent.can_handle("get_note", {}) is True
        assert note_agent.can_handle("list_notes", {}) is True
        assert note_agent.can_handle("search_notes", {}) is True
        assert note_agent.can_handle("update_note", {}) is True
        assert note_agent.can_handle("delete_note", {}) is True
        assert note_agent.can_handle("add_journal_entry", {}) is True
        assert note_agent.can_handle("link_notes", {}) is True
        assert note_agent.can_handle("get_linked_notes", {}) is True

    def test_can_handle_unsupported_intents(self, note_agent):
        """can_handle returns False for unsupported intents."""
        assert note_agent.can_handle("add_task", {}) is False
        assert note_agent.can_handle("schedule_meeting", {}) is False
        assert note_agent.can_handle("unknown_intent", {}) is False

    def test_notes_directory_created(self, note_agent, temp_notes_dir):
        """Notes directory structure is created on initialization."""
        assert temp_notes_dir.exists()
        assert (temp_notes_dir / "notes").exists()
        assert (temp_notes_dir / "journals").exists()
        assert (temp_notes_dir / "meetings").exists()
        assert (temp_notes_dir / "references").exists()


# =============================================================================
# Test Note Type Detection from Natural Language
# =============================================================================

class TestNoteTypeDetection:
    """Tests for note type detection from natural language."""

    def test_detect_journal_from_journal_keyword(self, note_agent):
        """Detects journal type from 'journal' keyword."""
        result = note_agent._parse_note_from_text("Journal: Today was productive")
        assert result["note_type"] == "journal"

    def test_detect_journal_from_diary_keyword(self, note_agent):
        """Detects journal type from 'diary' keyword."""
        result = note_agent._parse_note_from_text("diary entry about my day")
        assert result["note_type"] == "journal"

    def test_detect_journal_from_today_keyword(self, note_agent):
        """Detects journal type from 'today' keyword."""
        result = note_agent._parse_note_from_text("today I learned about Python")
        assert result["note_type"] == "journal"

    def test_detect_journal_from_reflection_keyword(self, note_agent):
        """Detects journal type from 'reflection' keyword."""
        result = note_agent._parse_note_from_text("reflection on my goals")
        assert result["note_type"] == "journal"

    def test_detect_meeting_from_meeting_keyword(self, note_agent):
        """Detects meeting type from 'meeting' keyword."""
        result = note_agent._parse_note_from_text("meeting notes for project sync")
        assert result["note_type"] == "meeting"

    def test_detect_meeting_from_notes_from_keyword(self, note_agent):
        """Detects meeting type from 'notes from' keyword."""
        result = note_agent._parse_note_from_text("notes from call with client")
        assert result["note_type"] == "meeting"

    def test_detect_meeting_from_call_with_keyword(self, note_agent):
        """Detects meeting type from 'call with' keyword."""
        result = note_agent._parse_note_from_text("call with John about project")
        assert result["note_type"] == "meeting"

    def test_detect_reference_from_reference_keyword(self, note_agent):
        """Detects reference type from 'reference' keyword."""
        result = note_agent._parse_note_from_text("reference for API endpoints")
        assert result["note_type"] == "reference"

    def test_detect_reference_from_how_to_keyword(self, note_agent):
        """Detects reference type from 'how to' keyword."""
        result = note_agent._parse_note_from_text("how to configure Docker")
        assert result["note_type"] == "reference"

    def test_detect_reference_from_tutorial_keyword(self, note_agent):
        """Detects reference type from 'tutorial' keyword."""
        result = note_agent._parse_note_from_text("tutorial on React hooks")
        assert result["note_type"] == "reference"

    def test_detect_reference_from_guide_keyword(self, note_agent):
        """Detects reference type from 'guide' keyword."""
        result = note_agent._parse_note_from_text("guide to Python packaging")
        assert result["note_type"] == "reference"

    def test_detect_reference_from_documentation_keyword(self, note_agent):
        """Detects reference type from 'documentation' keyword."""
        result = note_agent._parse_note_from_text("documentation for REST API")
        assert result["note_type"] == "reference"

    def test_default_to_note_type(self, note_agent):
        """Defaults to 'note' type when no keywords match."""
        result = note_agent._parse_note_from_text("Random thoughts about coding")
        assert result["note_type"] == "note"

    def test_default_to_note_for_simple_text(self, note_agent):
        """Defaults to 'note' for simple text without keywords."""
        result = note_agent._parse_note_from_text("Python decorators explained")
        assert result["note_type"] == "note"


# =============================================================================
# Test Tag Extraction
# =============================================================================

class TestTagExtraction:
    """Tests for tag extraction from natural language."""

    def test_extract_single_hashtag(self, note_agent):
        """Extracts single hashtag as tag."""
        result = note_agent._parse_note_from_text("Note about Python #programming")
        assert "programming" in result["tags"]

    def test_extract_multiple_hashtags(self, note_agent):
        """Extracts multiple hashtags as tags."""
        result = note_agent._parse_note_from_text("Learning notes #python #tutorial #coding")
        assert "python" in result["tags"]
        assert "tutorial" in result["tags"]
        assert "coding" in result["tags"]

    def test_hashtags_removed_from_title(self, note_agent):
        """Hashtags are removed from the resulting title."""
        result = note_agent._parse_note_from_text("Python basics #learning #python")
        assert "#" not in result["title"]
        assert "learning" not in result["title"]
        assert "python basics" in result["title"].lower()

    def test_no_hashtags_returns_empty_list(self, note_agent):
        """Returns empty list when no hashtags present."""
        result = note_agent._parse_note_from_text("Simple note without tags")
        assert result["tags"] == []

    def test_handle_hashtag_at_end(self, note_agent):
        """Handles hashtags at the end of text."""
        result = note_agent._parse_note_from_text("Important concept #critical")
        assert "critical" in result["tags"]
        assert "important concept" in result["title"].lower()


# =============================================================================
# Test Intent Handling - create_note
# =============================================================================

class TestCreateNoteIntent:
    """Tests for the create_note intent handler."""

    def test_create_note_with_title_only(self, note_agent):
        """Creates note with just title."""
        response = note_agent.process("create_note", {"title": "Simple note"})

        assert response.success is True
        assert "note_id" in response.data
        assert response.data["note"]["title"] == "Simple note"

    def test_create_note_with_content(self, note_agent):
        """Creates note with title and content."""
        context = {
            "title": "Detailed note",
            "content": "This is the note content with some details."
        }
        response = note_agent.process("create_note", context)

        assert response.success is True
        assert response.data["note"]["word_count"] > 0

    def test_create_note_with_note_type(self, note_agent):
        """Creates note with specified note type."""
        context = {
            "title": "Meeting recap",
            "note_type": "meeting"
        }
        response = note_agent.process("create_note", context)

        assert response.success is True
        assert response.data["note"]["note_type"] == "meeting"

    def test_create_note_with_tags(self, note_agent):
        """Creates note with tags."""
        context = {
            "title": "Tagged note",
            "tags": ["work", "important"]
        }
        response = note_agent.process("create_note", context)

        assert response.success is True
        tags = json.loads(response.data["note"]["tags"])
        assert "work" in tags
        assert "important" in tags

    def test_create_note_with_natural_language(self, note_agent):
        """Creates note from natural language text."""
        context = {
            "text": "Meeting notes with client about project #work #client"
        }
        response = note_agent.process("create_note", context)

        assert response.success is True
        note = response.data["note"]
        assert note["note_type"] == "meeting"
        tags = json.loads(note["tags"])
        assert "work" in tags
        assert "client" in tags

    def test_create_note_returns_file_path(self, note_agent):
        """create_note response includes the file path."""
        response = note_agent.process("create_note", {"title": "File path test"})

        assert response.success is True
        assert "file_path" in response.data
        assert response.data["file_path"].endswith(".md")

    def test_create_note_creates_markdown_file(self, note_agent, temp_notes_dir):
        """Creates actual markdown file on disk."""
        response = note_agent.process("create_note", {
            "title": "Markdown file test",
            "content": "Content for the file"
        })

        assert response.success is True
        file_path = Path(response.data["file_path"])
        assert file_path.exists()
        content = file_path.read_text()
        assert "Markdown file test" in content
        assert "Content for the file" in content

    def test_create_note_returns_suggestions(self, note_agent):
        """create_note response includes helpful suggestions."""
        response = note_agent.process("create_note", {"title": "New note"})

        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_create_note_missing_title_fails(self, note_agent):
        """create_note fails when title is missing."""
        response = note_agent.process("create_note", {})

        assert response.success is False
        assert "title" in response.message.lower()

    def test_create_note_empty_title_from_text_fails(self, note_agent):
        """create_note fails when text parsing results in empty title."""
        response = note_agent.process("create_note", {"text": ""})

        assert response.success is False

    def test_create_note_invalid_note_type_defaults_to_note(self, note_agent):
        """Invalid note type defaults to 'note'."""
        context = {
            "title": "Test note",
            "note_type": "invalid_type"
        }
        response = note_agent.process("create_note", context)

        assert response.success is True
        assert response.data["note"]["note_type"] == "note"


# =============================================================================
# Test Intent Handling - get_note
# =============================================================================

class TestGetNoteIntent:
    """Tests for the get_note intent handler."""

    def test_get_note_by_id(self, note_agent_with_data):
        """Retrieves note by ID."""
        response = note_agent_with_data.process("get_note", {"note_id": 1})

        assert response.success is True
        assert response.data["note"]["id"] == 1
        assert response.data["note"]["title"] == "Python Decorators"

    def test_get_note_by_title(self, note_agent_with_data):
        """Retrieves note by exact title match."""
        response = note_agent_with_data.process(
            "get_note", {"title": "Python Decorators"}
        )

        assert response.success is True
        assert response.data["note"]["title"] == "Python Decorators"

    def test_get_note_by_partial_title(self, note_agent_with_data):
        """Retrieves note by partial title match."""
        response = note_agent_with_data.process(
            "get_note", {"title": "Decorators"}
        )

        assert response.success is True
        assert "Decorators" in response.data["note"]["title"]

    def test_get_note_includes_content_by_default(self, note_agent_with_data):
        """get_note includes file content by default."""
        response = note_agent_with_data.process("get_note", {"note_id": 1})

        assert response.success is True
        assert "content" in response.data["note"]
        assert response.data["note"]["content"] is not None

    def test_get_note_excludes_content_when_requested(self, note_agent_with_data):
        """get_note excludes content when include_content is False."""
        response = note_agent_with_data.process(
            "get_note", {"note_id": 1, "include_content": False}
        )

        assert response.success is True
        assert "content" not in response.data["note"] or response.data["note"].get("content") is None

    def test_get_note_missing_params_fails(self, note_agent_with_data):
        """get_note fails when no identifier provided."""
        response = note_agent_with_data.process("get_note", {})

        assert response.success is False
        assert "id" in response.message.lower() or "title" in response.message.lower()

    def test_get_note_invalid_id(self, note_agent_with_data):
        """get_note returns error for non-existent ID."""
        response = note_agent_with_data.process("get_note", {"note_id": 9999})

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handling - list_notes
# =============================================================================

class TestListNotesIntent:
    """Tests for the list_notes intent handler."""

    def test_list_notes_returns_all(self, note_agent_with_data):
        """list_notes returns all notes by default."""
        response = note_agent_with_data.process("list_notes", {})

        assert response.success is True
        assert response.data["count"] >= 5

    def test_list_notes_filter_by_type(self, note_agent_with_data):
        """Filters notes by note type."""
        response = note_agent_with_data.process(
            "list_notes", {"note_type": "journal"}
        )

        assert response.success is True
        for note in response.data["notes"]:
            assert note["note_type"] == "journal"

    def test_list_notes_filter_by_tags(self, note_agent_with_data):
        """Filters notes by tags."""
        response = note_agent_with_data.process(
            "list_notes", {"tags": ["python"]}
        )

        assert response.success is True
        assert len(response.data["notes"]) >= 1

    def test_list_notes_with_limit(self, note_agent_with_data):
        """Respects limit parameter."""
        response = note_agent_with_data.process(
            "list_notes", {"limit": 2}
        )

        assert response.success is True
        assert len(response.data["notes"]) <= 2

    def test_list_notes_sort_by_created(self, note_agent_with_data):
        """Sorts notes by created_at."""
        response = note_agent_with_data.process(
            "list_notes", {"sort_by": "created_at", "sort_order": "desc"}
        )

        assert response.success is True
        assert response.data["count"] >= 1

    def test_list_notes_sort_by_title(self, note_agent_with_data):
        """Sorts notes by title."""
        response = note_agent_with_data.process(
            "list_notes", {"sort_by": "title", "sort_order": "asc"}
        )

        assert response.success is True
        notes = response.data["notes"]
        if len(notes) >= 2:
            assert notes[0]["title"] <= notes[1]["title"]

    def test_list_notes_empty_result(self, note_agent):
        """Returns empty list when no notes exist."""
        response = note_agent.process("list_notes", {})

        assert response.success is True
        assert response.data["notes"] == []
        assert response.data["count"] == 0

    def test_list_notes_returns_count(self, note_agent_with_data):
        """Response includes note count."""
        response = note_agent_with_data.process("list_notes", {})

        assert "count" in response.data
        assert response.data["count"] == len(response.data["notes"])


# =============================================================================
# Test Intent Handling - search_notes
# =============================================================================

class TestSearchNotesIntent:
    """Tests for the search_notes intent handler."""

    def test_search_notes_by_title(self, note_agent_with_data):
        """Finds notes matching title text."""
        response = note_agent_with_data.process(
            "search_notes", {"query": "Python"}
        )

        assert response.success is True
        assert len(response.data["notes"]) >= 1
        assert any("Python" in n["title"] for n in response.data["notes"])

    def test_search_notes_case_insensitive(self, note_agent_with_data):
        """Search is case insensitive."""
        response = note_agent_with_data.process(
            "search_notes", {"query": "PYTHON"}
        )

        assert response.success is True
        assert len(response.data["notes"]) >= 1

    def test_search_notes_partial_match(self, note_agent_with_data):
        """Search works with partial matches."""
        response = note_agent_with_data.process(
            "search_notes", {"query": "Deco"}
        )

        assert response.success is True
        assert len(response.data["notes"]) >= 1

    def test_search_notes_in_content(self, note_agent_with_data):
        """Searches in file content when enabled."""
        response = note_agent_with_data.process(
            "search_notes", {"query": "Sample content", "search_content": True}
        )

        assert response.success is True
        # Should find notes that have "Sample content" in their files

    def test_search_notes_no_results(self, note_agent_with_data):
        """Returns empty result for no matches."""
        response = note_agent_with_data.process(
            "search_notes", {"query": "xyznonexistent"}
        )

        assert response.success is True
        assert response.data["notes"] == []

    def test_search_notes_missing_query(self, note_agent_with_data):
        """Returns error when query is missing."""
        response = note_agent_with_data.process("search_notes", {})

        assert response.success is False
        assert "query" in response.message.lower()

    def test_search_notes_with_limit(self, note_agent_with_data):
        """Respects limit parameter."""
        response = note_agent_with_data.process(
            "search_notes", {"query": "note", "limit": 2}
        )

        assert response.success is True
        assert len(response.data["notes"]) <= 2


# =============================================================================
# Test Intent Handling - update_note
# =============================================================================

class TestUpdateNoteIntent:
    """Tests for the update_note intent handler."""

    def test_update_note_title(self, note_agent_with_data):
        """Updates note title."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 1, "title": "Updated Title"}
        )

        assert response.success is True
        assert response.data["note"]["title"] == "Updated Title"

    def test_update_note_type(self, note_agent_with_data):
        """Updates note type."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 1, "note_type": "reference"}
        )

        assert response.success is True
        assert response.data["note"]["note_type"] == "reference"

    def test_update_note_tags(self, note_agent_with_data):
        """Updates note tags."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 1, "tags": ["updated", "new-tag"]}
        )

        assert response.success is True
        tags = json.loads(response.data["note"]["tags"])
        assert "updated" in tags
        assert "new-tag" in tags

    def test_update_note_content(self, note_agent_with_data):
        """Updates note content in file."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 1, "content": "New updated content here."}
        )

        assert response.success is True
        assert response.data["note"]["word_count"] > 0

    def test_update_note_multiple_fields(self, note_agent_with_data):
        """Updates multiple fields at once."""
        response = note_agent_with_data.process(
            "update_note", {
                "note_id": 1,
                "title": "Multi-update title",
                "note_type": "meeting",
                "tags": ["multi", "update"]
            }
        )

        assert response.success is True
        note = response.data["note"]
        assert note["title"] == "Multi-update title"
        assert note["note_type"] == "meeting"

    def test_update_note_missing_id(self, note_agent_with_data):
        """Returns error when note_id is missing."""
        response = note_agent_with_data.process(
            "update_note", {"title": "No ID"}
        )

        assert response.success is False
        assert "note_id" in response.message.lower()

    def test_update_note_no_fields(self, note_agent_with_data):
        """Returns error when no update fields provided."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 1}
        )

        assert response.success is False
        assert "no fields" in response.message.lower()

    def test_update_note_invalid_id(self, note_agent_with_data):
        """Returns error for non-existent note."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 9999, "title": "Never exists"}
        )

        assert response.success is False
        assert "not found" in response.message.lower()

    def test_update_note_invalid_type_ignored(self, note_agent_with_data):
        """Invalid note type is ignored."""
        response = note_agent_with_data.process(
            "update_note", {"note_id": 1, "note_type": "invalid_type", "title": "Valid update"}
        )

        assert response.success is True
        # The invalid note_type should be ignored, only title updated


# =============================================================================
# Test Intent Handling - delete_note
# =============================================================================

class TestDeleteNoteIntent:
    """Tests for the delete_note intent handler."""

    def test_delete_note_soft_delete(self, note_agent_with_data):
        """Soft delete moves note to archive."""
        response = note_agent_with_data.process(
            "delete_note", {"note_id": 5}
        )

        assert response.success is True
        assert "archived" in response.message.lower() or response.data["note_id"] == 5

    def test_delete_note_hard_delete(self, note_agent_with_data, temp_notes_dir):
        """Hard delete removes note completely."""
        # First create a note we can delete
        create_response = note_agent_with_data.process(
            "create_note", {"title": "To be deleted", "content": "Delete me"}
        )
        note_id = create_response.data["note_id"]

        response = note_agent_with_data.process(
            "delete_note", {"note_id": note_id, "hard_delete": True}
        )

        assert response.success is True
        assert "permanently deleted" in response.message.lower()

        # Verify note is gone from database
        get_response = note_agent_with_data.process("get_note", {"note_id": note_id})
        assert get_response.success is False

    def test_delete_note_missing_id(self, note_agent_with_data):
        """Returns error when note_id is missing."""
        response = note_agent_with_data.process("delete_note", {})

        assert response.success is False
        assert "note_id" in response.message.lower()

    def test_delete_note_invalid_id(self, note_agent_with_data):
        """Returns error for non-existent note."""
        response = note_agent_with_data.process(
            "delete_note", {"note_id": 9999}
        )

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handling - add_journal_entry
# =============================================================================

class TestAddJournalEntryIntent:
    """Tests for the add_journal_entry intent handler."""

    def test_add_journal_entry_creates_journal(self, note_agent):
        """Creates journal entry with correct type."""
        response = note_agent.process(
            "add_journal_entry", {"content": "Today I learned about testing."}
        )

        assert response.success is True
        assert response.data["note"]["note_type"] == "journal"

    def test_add_journal_entry_auto_generates_title(self, note_agent):
        """Auto-generates title with date."""
        response = note_agent.process(
            "add_journal_entry", {"content": "My journal entry content."}
        )

        assert response.success is True
        assert "Journal" in response.data["note"]["title"]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in response.data["note"]["title"]

    def test_add_journal_entry_with_mood(self, note_agent):
        """Creates journal entry with mood tag."""
        response = note_agent.process(
            "add_journal_entry", {"content": "Great day!", "mood": "happy"}
        )

        assert response.success is True
        tags = json.loads(response.data["note"]["tags"])
        assert any("mood:" in tag for tag in tags)

    def test_add_journal_entry_with_additional_tags(self, note_agent):
        """Creates journal entry with additional tags."""
        response = note_agent.process(
            "add_journal_entry", {
                "content": "Productive day coding.",
                "tags": ["work", "coding"]
            }
        )

        assert response.success is True
        tags = json.loads(response.data["note"]["tags"])
        assert "work" in tags
        assert "coding" in tags
        assert "journal" in tags

    def test_add_journal_entry_missing_content_fails(self, note_agent):
        """Returns error when content is missing."""
        response = note_agent.process("add_journal_entry", {})

        assert response.success is False
        assert "content" in response.message.lower()


# =============================================================================
# Test Intent Handling - link_notes
# =============================================================================

class TestLinkNotesIntent:
    """Tests for the link_notes intent handler."""

    def test_link_notes_creates_link(self, note_agent_with_data):
        """Creates link between two notes."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 2,
                "link_type": "related"
            }
        )

        assert response.success is True
        assert response.data["source_note_id"] == 1
        assert response.data["target_note_id"] == 2
        assert response.data["link_type"] == "related"

    def test_link_notes_default_type(self, note_agent_with_data):
        """Uses 'related' as default link type."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 3
            }
        )

        assert response.success is True
        assert response.data["link_type"] == "related"

    def test_link_notes_parent_child(self, note_agent_with_data):
        """Creates parent-child link."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 4,
                "link_type": "parent"
            }
        )

        assert response.success is True
        assert response.data["link_type"] == "parent"

    def test_link_notes_reference_type(self, note_agent_with_data):
        """Creates reference link."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 5,
                "link_type": "reference"
            }
        )

        assert response.success is True
        assert response.data["link_type"] == "reference"

    def test_link_notes_invalid_type(self, note_agent_with_data):
        """Returns error for invalid link type."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 2,
                "link_type": "invalid_type"
            }
        )

        assert response.success is False
        assert "invalid link type" in response.message.lower()

    def test_link_notes_missing_source(self, note_agent_with_data):
        """Returns error when source_note_id is missing."""
        response = note_agent_with_data.process(
            "link_notes", {"target_note_id": 2}
        )

        assert response.success is False

    def test_link_notes_missing_target(self, note_agent_with_data):
        """Returns error when target_note_id is missing."""
        response = note_agent_with_data.process(
            "link_notes", {"source_note_id": 1}
        )

        assert response.success is False

    def test_link_notes_nonexistent_source(self, note_agent_with_data):
        """Returns error when source note doesn't exist."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 9999,
                "target_note_id": 2
            }
        )

        assert response.success is False
        assert "source note" in response.message.lower() and "not found" in response.message.lower()

    def test_link_notes_nonexistent_target(self, note_agent_with_data):
        """Returns error when target note doesn't exist."""
        response = note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 9999
            }
        )

        assert response.success is False
        assert "target note" in response.message.lower() and "not found" in response.message.lower()


# =============================================================================
# Test Intent Handling - get_linked_notes
# =============================================================================

class TestGetLinkedNotesIntent:
    """Tests for the get_linked_notes intent handler."""

    def test_get_linked_notes_returns_links(self, note_agent_with_data):
        """Returns linked notes for a note."""
        # First create some links
        note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 2,
                "link_type": "related"
            }
        )

        response = note_agent_with_data.process(
            "get_linked_notes", {"note_id": 1}
        )

        assert response.success is True
        assert "linked_notes" in response.data
        assert response.data["count"] >= 1

    def test_get_linked_notes_filter_by_type(self, note_agent_with_data):
        """Filters linked notes by link type."""
        # Create different link types
        note_agent_with_data.process(
            "link_notes", {"source_note_id": 1, "target_note_id": 2, "link_type": "related"}
        )
        note_agent_with_data.process(
            "link_notes", {"source_note_id": 1, "target_note_id": 3, "link_type": "reference"}
        )

        response = note_agent_with_data.process(
            "get_linked_notes", {"note_id": 1, "link_type": "related"}
        )

        assert response.success is True
        # Should only return related links

    def test_get_linked_notes_empty_result(self, note_agent_with_data):
        """Returns empty list when no links exist."""
        response = note_agent_with_data.process(
            "get_linked_notes", {"note_id": 5}
        )

        assert response.success is True
        assert response.data["linked_notes"] == []
        assert response.data["count"] == 0

    def test_get_linked_notes_missing_id(self, note_agent_with_data):
        """Returns error when note_id is missing."""
        response = note_agent_with_data.process("get_linked_notes", {})

        assert response.success is False
        assert "note_id" in response.message.lower()

    def test_get_linked_notes_invalid_id(self, note_agent_with_data):
        """Returns error for non-existent note."""
        response = note_agent_with_data.process(
            "get_linked_notes", {"note_id": 9999}
        )

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test File Path Generation
# =============================================================================

class TestFilePathGeneration:
    """Tests for file path generation."""

    def test_generates_valid_path(self, note_agent):
        """Generates a valid file path."""
        path = note_agent._generate_file_path("Test Note", "note")

        assert path.endswith(".md")
        assert "/" in path
        assert "notes/" in path

    def test_path_includes_date_prefix(self, note_agent):
        """Path includes date prefix."""
        path = note_agent._generate_file_path("My Note", "note")

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in path

    def test_path_maps_to_correct_directory(self, note_agent):
        """Maps note_type to correct directory."""
        note_path = note_agent._generate_file_path("Note", "note")
        journal_path = note_agent._generate_file_path("Journal", "journal")
        meeting_path = note_agent._generate_file_path("Meeting", "meeting")
        reference_path = note_agent._generate_file_path("Reference", "reference")

        assert note_path.startswith("notes/")
        assert journal_path.startswith("journals/")
        assert meeting_path.startswith("meetings/")
        assert reference_path.startswith("references/")

    def test_handles_special_characters(self, note_agent):
        """Handles special characters in title."""
        path = note_agent._generate_file_path("Note: With! Special? Characters*", "note")

        assert path.endswith(".md")
        assert ":" not in path.split("/")[-1]
        assert "!" not in path.split("/")[-1]
        assert "?" not in path.split("/")[-1]
        assert "*" not in path.split("/")[-1]

    def test_creates_unique_paths_for_duplicates(self, note_agent, temp_notes_dir):
        """Creates unique paths when filename already exists."""
        # Create first file
        path1 = note_agent._generate_file_path("Duplicate Test", "note")
        (temp_notes_dir / path1).write_text("First file")

        # Generate second path
        path2 = note_agent._generate_file_path("Duplicate Test", "note")

        assert path1 != path2
        assert "_1" in path2 or path2 != path1


# =============================================================================
# Test Slugify Helper
# =============================================================================

class TestSlugify:
    """Tests for the slugify helper function."""

    def test_slugify_basic(self, note_agent):
        """Slugifies basic text."""
        slug = note_agent._slugify("Hello World")
        assert slug == "hello-world"

    def test_slugify_special_chars(self, note_agent):
        """Removes special characters."""
        slug = note_agent._slugify("Test: Note! With? Chars*")
        assert ":" not in slug
        assert "!" not in slug
        assert "?" not in slug
        assert "*" not in slug

    def test_slugify_max_length(self, note_agent):
        """Respects maximum length."""
        long_text = "This is a very long title that should be truncated"
        slug = note_agent._slugify(long_text, max_length=20)
        assert len(slug) <= 20

    def test_slugify_empty_returns_untitled(self, note_agent):
        """Empty text returns 'untitled'."""
        slug = note_agent._slugify("")
        assert slug == "untitled"

    def test_slugify_only_special_chars_returns_untitled(self, note_agent):
        """Text with only special chars returns 'untitled'."""
        slug = note_agent._slugify("!@#$%^&*()")
        assert slug == "untitled"


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in NoteAgent."""

    def test_unknown_intent_returns_error(self, note_agent):
        """Unknown intent returns error response."""
        response = note_agent.process("unknown_intent", {})

        assert response.success is False
        assert "unknown intent" in response.message.lower()

    def test_database_error_handled(self, mock_config):
        """Database errors are caught and returned as error response."""
        mock_db = MagicMock()
        mock_db.execute_write.side_effect = Exception("Database connection failed")

        agent = NoteAgent(mock_db, mock_config)
        response = agent.process("create_note", {"title": "Test note"})

        assert response.success is False
        assert "failed" in response.message.lower()

    def test_validation_error_for_missing_required_params(self, note_agent):
        """Validation catches missing required parameters."""
        response = note_agent.process("search_notes", {})

        assert response.success is False
        assert "query" in response.message.lower()

    def test_file_not_found_handled_gracefully(self, note_agent_with_data, temp_notes_dir):
        """Handles missing file gracefully when reading content."""
        # Delete the file but keep database record
        file_path = temp_notes_dir / "notes/2025-01-01_python-decorators.md"
        if file_path.exists():
            file_path.unlink()

        response = note_agent_with_data.process("get_note", {"note_id": 1})

        assert response.success is True
        assert "content_warning" in response.data["note"] or response.data["note"].get("content") is None


# =============================================================================
# Test Database Integration
# =============================================================================

class TestDatabaseIntegration:
    """Tests for database integration in NoteAgent."""

    def test_note_persisted_correctly(self, note_agent):
        """Note is correctly persisted to database."""
        context = {
            "title": "Persistent note",
            "content": "This should be saved",
            "note_type": "reference",
            "tags": ["test", "integration"]
        }

        response = note_agent.process("create_note", context)
        note_id = response.data["note_id"]

        # Fetch directly from database
        note = note_agent._get_note_by_id(note_id)

        assert note["title"] == "Persistent note"
        assert note["note_type"] == "reference"
        tags = json.loads(note["tags"])
        assert "test" in tags
        assert "integration" in tags

    def test_note_update_persisted(self, note_agent_with_data):
        """Note update is correctly persisted."""
        note_agent_with_data.process(
            "update_note", {"note_id": 1, "title": "Updated title"}
        )

        note = note_agent_with_data._get_note_by_id(1)
        assert note["title"] == "Updated title"

    def test_note_link_persisted(self, note_agent_with_data):
        """Note link is correctly persisted."""
        note_agent_with_data.process(
            "link_notes", {
                "source_note_id": 1,
                "target_note_id": 2,
                "link_type": "related"
            }
        )

        # Verify link exists by getting linked notes
        response = note_agent_with_data.process(
            "get_linked_notes", {"note_id": 1}
        )
        assert response.data["count"] >= 1


# =============================================================================
# Test AgentResponse Structure
# =============================================================================

class TestAgentResponseStructure:
    """Tests for AgentResponse data structure."""

    def test_success_response_structure(self, note_agent):
        """Successful response has expected structure."""
        response = note_agent.process("create_note", {"title": "Test"})

        assert hasattr(response, "success")
        assert hasattr(response, "message")
        assert hasattr(response, "data")
        assert hasattr(response, "suggestions")

    def test_error_response_structure(self, note_agent):
        """Error response has expected structure."""
        response = note_agent.process("create_note", {})

        assert response.success is False
        assert response.message is not None
        assert len(response.message) > 0

    def test_response_to_dict(self, note_agent):
        """Response can be converted to dictionary."""
        response = note_agent.process("create_note", {"title": "Test"})

        result = response.to_dict()
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "data" in result


# =============================================================================
# Test Markdown Frontmatter Generation
# =============================================================================

class TestMarkdownFrontmatter:
    """Tests for markdown frontmatter generation."""

    def test_frontmatter_includes_title(self, note_agent):
        """Frontmatter includes title."""
        content = note_agent._create_markdown_with_frontmatter(
            title="Test Title",
            content="Content here",
            tags=["tag1"],
            note_type="note",
            metadata=None
        )

        assert "title: Test Title" in content

    def test_frontmatter_includes_type(self, note_agent):
        """Frontmatter includes note type."""
        content = note_agent._create_markdown_with_frontmatter(
            title="Test",
            content="Content",
            tags=[],
            note_type="journal",
            metadata=None
        )

        assert "type: journal" in content

    def test_frontmatter_includes_tags(self, note_agent):
        """Frontmatter includes tags."""
        content = note_agent._create_markdown_with_frontmatter(
            title="Test",
            content="Content",
            tags=["tag1", "tag2"],
            note_type="note",
            metadata=None
        )

        assert "tags:" in content
        assert "tag1" in content
        assert "tag2" in content

    def test_frontmatter_includes_timestamps(self, note_agent):
        """Frontmatter includes created and modified timestamps."""
        content = note_agent._create_markdown_with_frontmatter(
            title="Test",
            content="Content",
            tags=[],
            note_type="note",
            metadata=None
        )

        assert "created:" in content
        assert "modified:" in content

    def test_content_follows_frontmatter(self, note_agent):
        """Content appears after frontmatter."""
        content = note_agent._create_markdown_with_frontmatter(
            title="Test",
            content="My content here",
            tags=[],
            note_type="note",
            metadata=None
        )

        # Content should be after the closing ---
        parts = content.split("---")
        assert len(parts) >= 3
        assert "My content here" in parts[-1]

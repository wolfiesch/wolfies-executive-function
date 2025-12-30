"""
Note Agent for AI Life Planner
Handles all note-related operations: create, search, list, update, link notes.

This agent integrates with the Database and Note model to provide
natural language note management capabilities, including:
- Note creation with automatic file path generation
- Journal entries with mood tracking
- Full-text search across note content
- Bidirectional linking between notes (PKM feature)

Note Storage Strategy:
- Metadata stored in SQLite (notes table)
- Content stored in markdown files (data/notes/{category}/{filename}.md)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
import re

from .base_agent import BaseAgent, AgentResponse
from ..core.models import Note


class NoteAgent(BaseAgent):
    """
    Specialized agent for note and knowledge management.

    Handles intents:
    - create_note: Create a new note with NL parsing
    - get_note: Retrieve note by ID or title
    - list_notes: List notes with filters
    - search_notes: Full-text search in notes
    - update_note: Modify existing note
    - delete_note: Soft delete/archive a note
    - add_journal_entry: Quick journal entry creation
    - link_notes: Create bidirectional links between notes

    Integrates with the Database layer for metadata persistence,
    file system for content storage, and the Note model for data representation.
    """

    # Supported intents for this agent
    INTENTS = [
        "create_note",
        "get_note",
        "list_notes",
        "search_notes",
        "update_note",
        "delete_note",
        "add_journal_entry",
        "link_notes",
        "get_linked_notes",
    ]

    # Note type keywords for NL parsing
    NOTE_TYPE_KEYWORDS = {
        "journal": ["journal", "diary", "today", "reflection", "daily"],
        "meeting": ["meeting", "notes from", "call with", "discussion"],
        "reference": ["reference", "how to", "tutorial", "guide", "documentation"],
        "note": []  # Default fallback
    }

    # Valid link types for note connections
    LINK_TYPES = ["reference", "related", "parent", "child"]

    def __init__(self, db, config):
        """Initialize the Note Agent."""
        super().__init__(db, config, "note")
        self._notes_dir: Optional[Path] = None

    def initialize(self) -> bool:
        """
        Initialize the Note Agent and ensure notes directory exists.

        Creates the notes directory structure if it doesn't exist.
        """
        try:
            self._notes_dir = self.config.get_notes_directory()
            self._notes_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories for note types
            for note_type in ["notes", "journals", "meetings", "references"]:
                (self._notes_dir / note_type).mkdir(exist_ok=True)

            self._initialized = True
            self.logger.info(f"Note agent initialized, notes dir: {self._notes_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize note agent: {e}")
            return False

    @property
    def notes_dir(self) -> Path:
        """Get notes directory, initializing if needed."""
        if self._notes_dir is None:
            self._notes_dir = self.config.get_notes_directory()
        return self._notes_dir

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents."""
        return self.INTENTS

    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given intent."""
        return intent in self.INTENTS

    def process(self, intent: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process a note-related intent.

        Routes to the appropriate handler based on intent type.

        Args:
            intent: One of the supported note intents
            context: Request context with parameters

        Returns:
            AgentResponse with operation result
        """
        self.log_action(f"processing_{intent}", {"context_keys": list(context.keys())})

        handlers = {
            "create_note": self._handle_create_note,
            "get_note": self._handle_get_note,
            "list_notes": self._handle_list_notes,
            "search_notes": self._handle_search_notes,
            "update_note": self._handle_update_note,
            "delete_note": self._handle_delete_note,
            "add_journal_entry": self._handle_add_journal_entry,
            "link_notes": self._handle_link_notes,
            "get_linked_notes": self._handle_get_linked_notes,
        }

        handler = handlers.get(intent)
        if not handler:
            return AgentResponse.error(f"Unknown intent: {intent}")

        try:
            return handler(context)
        except Exception as e:
            self.logger.error(f"Error processing {intent}: {e}", exc_info=True)
            return AgentResponse.error(f"Failed to process {intent}: {str(e)}")

    # =========================================================================
    # Intent Handlers
    # =========================================================================

    def _handle_create_note(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Handle note creation.

        Supports two modes:
        1. Structured: title, content, note_type provided directly
        2. Natural language: text field parsed for note details

        Context params:
            text (str): Natural language note description
            OR
            title (str): Note title
            content (str): Note content (markdown)
            note_type (str, optional): 'note', 'journal', 'meeting', 'reference'
            para_category_id (int, optional): Associated PARA category
            tags (list, optional): Note tags
        """
        # Check if we have natural language input
        if "text" in context and context["text"]:
            parsed = self._parse_note_from_text(context["text"])
            # Merge parsed values with any explicit overrides from context
            for key, value in parsed.items():
                if key not in context or context[key] is None:
                    context[key] = value

        # Validate required fields
        if not context.get("title"):
            return AgentResponse.error("Note title is required")

        content = context.get("content", "")
        note_type = context.get("note_type", "note")
        tags = context.get("tags", [])

        # Validate note_type
        if note_type not in ["note", "journal", "meeting", "reference"]:
            note_type = "note"

        # Generate file path
        file_path = self._generate_file_path(context["title"], note_type)

        # Calculate word count
        word_count = len(content.split()) if content else 0

        # Build note data
        note_data = {
            "title": context["title"],
            "file_path": file_path,
            "note_type": note_type,
            "para_category_id": context.get("para_category_id"),
            "tags": json.dumps(tags) if tags else None,
            "word_count": word_count,
            "metadata": json.dumps(context.get("metadata", {})) if context.get("metadata") else None,
        }

        try:
            # Write content to file first
            full_path = self.notes_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Create markdown file with frontmatter
            markdown_content = self._create_markdown_with_frontmatter(
                title=context["title"],
                content=content,
                tags=tags,
                note_type=note_type,
                metadata=context.get("metadata")
            )
            full_path.write_text(markdown_content, encoding="utf-8")

            # Insert metadata into database
            note_id = self._insert_note(note_data)
            created_note = self._get_note_by_id(note_id)

            return AgentResponse.ok(
                message=f"Note created: '{context['title']}'",
                data={
                    "note_id": note_id,
                    "note": created_note,
                    "file_path": str(full_path)
                },
                suggestions=[
                    "List all notes: 'show my notes'",
                    f"Link to another note: 'link note {note_id} to ...'",
                    "Search notes: 'search notes for ...'"
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to create note: {e}")
            return AgentResponse.error(f"Failed to create note: {str(e)}")

    def _handle_get_note(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Get a single note by ID or title search.

        Context params:
            note_id (int): Note ID to retrieve
            OR
            title (str): Title to search for
            include_content (bool): Whether to include file content (default True)
        """
        include_content = context.get("include_content", True)

        if "note_id" in context:
            note = self._get_note_by_id(context["note_id"])
        elif "title" in context:
            note = self._get_note_by_title(context["title"])
        else:
            return AgentResponse.error("Note ID or title is required")

        if not note:
            return AgentResponse.error("Note not found")

        # Optionally include file content
        if include_content:
            try:
                full_path = self.notes_dir / note["file_path"]
                if full_path.exists():
                    note["content"] = full_path.read_text(encoding="utf-8")
                else:
                    note["content"] = None
                    note["content_warning"] = "File not found"
            except Exception as e:
                note["content"] = None
                note["content_error"] = str(e)

        return AgentResponse.ok(
            message=f"Note: {note['title']}",
            data={"note": note}
        )

    def _handle_list_notes(self, context: Dict[str, Any]) -> AgentResponse:
        """
        List notes with optional filters.

        Context params:
            note_type (str): Filter by note type
            para_category_id (int): Filter by PARA category
            tags (list): Filter by tags (any match)
            created_after (str): Notes created after date
            created_before (str): Notes created before date
            sort_by (str): Sort field ('created_at', 'updated_at', 'title')
            sort_order (str): 'asc' or 'desc'
            limit (int): Max notes to return (default 20)
        """
        filters = {}

        if "note_type" in context:
            filters["note_type"] = context["note_type"]
        if "para_category_id" in context:
            filters["para_category_id"] = context["para_category_id"]
        if "tags" in context:
            filters["tags"] = context["tags"]
        if "created_after" in context:
            filters["created_after"] = context["created_after"]
        if "created_before" in context:
            filters["created_before"] = context["created_before"]

        sort_by = context.get("sort_by", "created_at")
        sort_order = context.get("sort_order", "desc")
        limit = context.get("limit", 20)

        notes = self._fetch_notes(filters, sort_by, sort_order, limit)

        if not notes:
            return AgentResponse.ok(
                message="No notes found matching the criteria",
                data={"notes": [], "count": 0}
            )

        return AgentResponse.ok(
            message=f"Found {len(notes)} note(s)",
            data={
                "notes": notes,
                "count": len(notes),
                "filters_applied": filters
            }
        )

    def _handle_search_notes(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Search notes by text in title, content, and tags.

        Context params:
            query (str): Search query
            search_content (bool): Search in file content (default True)
            limit (int): Max results (default 20)
        """
        validation = self.validate_required_params(context, ["query"])
        if validation:
            return validation

        query = context["query"]
        search_content = context.get("search_content", True)
        limit = context.get("limit", 20)

        # First search in database (title, tags)
        notes = self._search_notes_in_db(query, limit)

        # Optionally search in file content
        if search_content:
            content_matches = self._search_notes_in_files(query, limit)
            # Merge results, avoiding duplicates
            existing_ids = {n["id"] for n in notes}
            for match in content_matches:
                if match["id"] not in existing_ids:
                    notes.append(match)
                    if len(notes) >= limit:
                        break

        return AgentResponse.ok(
            message=f"Found {len(notes)} note(s) matching '{query}'",
            data={
                "notes": notes[:limit],
                "count": len(notes),
                "query": query
            }
        )

    def _handle_update_note(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Update note properties and/or content.

        Context params:
            note_id (int): Note to update
            title (str, optional): New title
            content (str, optional): New content
            note_type (str, optional): New note type
            tags (list, optional): New tags
            para_category_id (int, optional): New PARA category
        """
        validation = self.validate_required_params(context, ["note_id"])
        if validation:
            return validation

        note_id = context["note_id"]
        existing_note = self._get_note_by_id(note_id)
        if not existing_note:
            return AgentResponse.error(f"Note {note_id} not found")

        # Build update data
        update_fields = {}
        if "title" in context:
            update_fields["title"] = context["title"]
        if "note_type" in context:
            if context["note_type"] in ["note", "journal", "meeting", "reference"]:
                update_fields["note_type"] = context["note_type"]
        if "tags" in context:
            update_fields["tags"] = json.dumps(context["tags"])
        if "para_category_id" in context:
            update_fields["para_category_id"] = context["para_category_id"]

        # Handle content update
        if "content" in context:
            try:
                full_path = self.notes_dir / existing_note["file_path"]
                new_content = self._create_markdown_with_frontmatter(
                    title=context.get("title", existing_note["title"]),
                    content=context["content"],
                    tags=context.get("tags") or self._parse_tags_from_db(existing_note.get("tags")),
                    note_type=context.get("note_type", existing_note["note_type"]),
                    metadata=None
                )
                full_path.write_text(new_content, encoding="utf-8")
                update_fields["word_count"] = len(context["content"].split())
            except Exception as e:
                return AgentResponse.error(f"Failed to update note content: {str(e)}")

        if not update_fields and "content" not in context:
            return AgentResponse.error("No fields to update provided")

        try:
            if update_fields:
                self._update_note(note_id, update_fields)
            updated_note = self._get_note_by_id(note_id)
            return AgentResponse.ok(
                message=f"Note {note_id} updated",
                data={"note": updated_note}
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to update note: {str(e)}")

    def _handle_delete_note(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Delete a note (soft delete by moving to archive).

        Context params:
            note_id (int): Note to delete
            hard_delete (bool): If True, permanently delete (default False)
        """
        validation = self.validate_required_params(context, ["note_id"])
        if validation:
            return validation

        note_id = context["note_id"]
        hard_delete = context.get("hard_delete", False)

        existing_note = self._get_note_by_id(note_id)
        if not existing_note:
            return AgentResponse.error(f"Note {note_id} not found")

        try:
            if hard_delete:
                # Delete file and database record
                full_path = self.notes_dir / existing_note["file_path"]
                if full_path.exists():
                    full_path.unlink()
                self._delete_note_from_db(note_id)
                message = f"Note {note_id} permanently deleted"
            else:
                # Soft delete: move to archive
                archive_path = self._archive_note(existing_note)
                self._update_note(note_id, {
                    "file_path": archive_path,
                    "note_type": "reference"  # Archived notes become references
                })
                message = f"Note {note_id} archived"

            return AgentResponse.ok(
                message=message,
                data={"note_id": note_id}
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to delete note: {str(e)}")

    def _handle_add_journal_entry(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Quick journal entry creation.

        Specialized version of create_note that:
        - Auto-sets note_type to 'journal'
        - Auto-generates title with date
        - Supports mood tracking

        Context params:
            content (str): Journal entry content
            mood (str, optional): Mood indicator
            tags (list, optional): Additional tags
        """
        if not context.get("content"):
            return AgentResponse.error("Journal entry content is required")

        # Generate title with date
        now = datetime.now(timezone.utc)
        title = now.strftime("Journal - %Y-%m-%d")

        # Check if there's already a journal for today
        existing = self._get_journal_for_date(now.date())
        if existing:
            # Append to existing journal
            return self._append_to_journal(existing, context["content"], context.get("mood"))

        # Build tags
        tags = context.get("tags", [])
        if "journal" not in tags:
            tags.append("journal")
        if context.get("mood"):
            tags.append(f"mood:{context['mood']}")

        # Create new journal entry
        journal_context = {
            "title": title,
            "content": context["content"],
            "note_type": "journal",
            "tags": tags,
            "metadata": {
                "mood": context.get("mood"),
                "time": now.strftime("%H:%M")
            }
        }

        return self._handle_create_note(journal_context)

    def _handle_link_notes(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Create bidirectional links between notes.

        Context params:
            source_note_id (int): Source note ID
            target_note_id (int): Target note ID
            link_type (str): 'reference', 'related', 'parent', 'child'
        """
        validation = self.validate_required_params(
            context, ["source_note_id", "target_note_id"]
        )
        if validation:
            return validation

        source_id = context["source_note_id"]
        target_id = context["target_note_id"]
        link_type = context.get("link_type", "related")

        if link_type not in self.LINK_TYPES:
            return AgentResponse.error(
                f"Invalid link type. Must be one of: {', '.join(self.LINK_TYPES)}"
            )

        # Verify both notes exist
        source_note = self._get_note_by_id(source_id)
        target_note = self._get_note_by_id(target_id)

        if not source_note:
            return AgentResponse.error(f"Source note {source_id} not found")
        if not target_note:
            return AgentResponse.error(f"Target note {target_id} not found")

        try:
            # Create the link
            self._create_note_link(source_id, target_id, link_type)

            # For bidirectional linking, create reverse link with complementary type
            reverse_type = self._get_reverse_link_type(link_type)
            if reverse_type:
                try:
                    self._create_note_link(target_id, source_id, reverse_type)
                except Exception:
                    # Reverse link might already exist, which is fine
                    pass

            return AgentResponse.ok(
                message=f"Linked '{source_note['title']}' to '{target_note['title']}'",
                data={
                    "source_note_id": source_id,
                    "target_note_id": target_id,
                    "link_type": link_type
                }
            )
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                return AgentResponse.error("Link already exists between these notes")
            return AgentResponse.error(f"Failed to create link: {str(e)}")

    def _handle_get_linked_notes(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Get all notes linked to a specific note.

        Context params:
            note_id (int): Note to get links for
            link_type (str, optional): Filter by link type
        """
        validation = self.validate_required_params(context, ["note_id"])
        if validation:
            return validation

        note_id = context["note_id"]
        link_type = context.get("link_type")

        note = self._get_note_by_id(note_id)
        if not note:
            return AgentResponse.error(f"Note {note_id} not found")

        linked_notes = self._get_linked_notes(note_id, link_type)

        return AgentResponse.ok(
            message=f"Found {len(linked_notes)} linked note(s)",
            data={
                "note": note,
                "linked_notes": linked_notes,
                "count": len(linked_notes)
            }
        )

    # =========================================================================
    # Natural Language Parsing
    # =========================================================================

    def _parse_note_from_text(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text to extract note properties.

        Extracts:
        - Title (main note description)
        - Note type (from keywords)
        - Tags (from hashtags)

        Examples:
        - "Note about Python decorators" -> title extraction
        - "Journal: Today was productive..." -> note_type detection
        - "#learning #python" -> tag extraction

        Args:
            text: Natural language note description

        Returns:
            Dictionary with parsed note properties
        """
        result = {
            "title": text,
            "note_type": "note",
            "tags": [],
            "content": ""
        }

        working_text = text.lower()

        # Detect note type from keywords
        for note_type, keywords in self.NOTE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in working_text:
                    result["note_type"] = note_type
                    break
            if result["note_type"] != "note":
                break

        # Extract hashtags as tags
        tags = re.findall(r'#(\w+)', text)
        if tags:
            result["tags"] = tags
            result["title"] = re.sub(r'#\w+', '', result["title"]).strip()

        # Handle "Note about X" pattern
        about_match = re.search(r'(?:note|notes?)\s+(?:about|on|for)\s+(.+?)(?:\s*#|$)', text, re.IGNORECASE)
        if about_match:
            result["title"] = about_match.group(1).strip()

        # Handle "Journal: content" pattern
        journal_match = re.search(r'^journal[:\s]+(.+)$', text, re.IGNORECASE)
        if journal_match:
            result["note_type"] = "journal"
            result["content"] = journal_match.group(1).strip()
            result["title"] = datetime.now(timezone.utc).strftime("Journal - %Y-%m-%d")

        # Handle "Meeting notes: X" pattern
        meeting_match = re.search(r'^meeting\s+(?:notes?)?[:\s]+(.+)$', text, re.IGNORECASE)
        if meeting_match:
            result["note_type"] = "meeting"
            content = meeting_match.group(1).strip()
            # Try to extract meeting title
            title_match = re.search(r'^(?:with\s+)?([^-\n]+)', content)
            if title_match:
                result["title"] = f"Meeting: {title_match.group(1).strip()}"

        # Clean up title
        result["title"] = re.sub(r'\s+', ' ', result["title"]).strip(' ,-:#')

        return result

    # =========================================================================
    # File Operations
    # =========================================================================

    def _generate_file_path(self, title: str, note_type: str) -> str:
        """
        Generate a unique file path for a note.

        Format: {note_type}s/{date}_{slugified_title}.md

        Args:
            title: Note title
            note_type: Type of note

        Returns:
            Relative file path from notes directory
        """
        # Map note_type to directory
        type_dirs = {
            "note": "notes",
            "journal": "journals",
            "meeting": "meetings",
            "reference": "references"
        }
        directory = type_dirs.get(note_type, "notes")

        # Generate date prefix
        date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Slugify title
        slug = self._slugify(title)

        # Ensure uniqueness
        base_path = f"{directory}/{date_prefix}_{slug}.md"
        full_path = self.notes_dir / base_path

        counter = 1
        while full_path.exists():
            base_path = f"{directory}/{date_prefix}_{slug}_{counter}.md"
            full_path = self.notes_dir / base_path
            counter += 1

        return base_path

    def _slugify(self, text: str, max_length: int = 50) -> str:
        """
        Convert text to URL/file-safe slug.

        Args:
            text: Text to slugify
            max_length: Maximum slug length

        Returns:
            Slugified string
        """
        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Truncate to max length
        if len(slug) > max_length:
            slug = slug[:max_length].rsplit('-', 1)[0]
        return slug or "untitled"

    def _create_markdown_with_frontmatter(
        self,
        title: str,
        content: str,
        tags: List[str],
        note_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create markdown content with YAML frontmatter.

        Args:
            title: Note title
            content: Note content
            tags: Note tags
            note_type: Type of note
            metadata: Additional metadata

        Returns:
            Complete markdown string with frontmatter
        """
        now = datetime.now(timezone.utc).isoformat()

        frontmatter_lines = [
            "---",
            f"title: {title}",
            f"type: {note_type}",
            f"created: {now}",
            f"modified: {now}",
        ]

        if tags:
            frontmatter_lines.append(f"tags: [{', '.join(tags)}]")

        if metadata:
            for key, value in metadata.items():
                if value is not None:
                    frontmatter_lines.append(f"{key}: {value}")

        frontmatter_lines.append("---")
        frontmatter_lines.append("")  # Blank line after frontmatter
        frontmatter_lines.append(f"# {title}")
        frontmatter_lines.append("")

        if content:
            frontmatter_lines.append(content)

        return "\n".join(frontmatter_lines)

    def _archive_note(self, note: Dict[str, Any]) -> str:
        """
        Move a note to the archive directory.

        Args:
            note: Note dict with file_path

        Returns:
            New file path (relative)
        """
        old_path = self.notes_dir / note["file_path"]
        archive_dir = self.notes_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Generate archive path with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        new_filename = f"archived_{timestamp}_{old_path.name}"
        new_path = archive_dir / new_filename

        if old_path.exists():
            old_path.rename(new_path)

        return f"archive/{new_filename}"

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _insert_note(self, note_data: Dict[str, Any]) -> int:
        """Insert a new note and return its ID."""
        query = """
            INSERT INTO notes (
                title, file_path, note_type, para_category_id,
                tags, word_count, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            note_data["title"],
            note_data["file_path"],
            note_data.get("note_type", "note"),
            note_data.get("para_category_id"),
            note_data.get("tags"),
            note_data.get("word_count", 0),
            note_data.get("metadata"),
        )
        return self.db.execute_write(query, params)

    def _get_note_by_id(self, note_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single note by ID."""
        query = "SELECT * FROM notes WHERE id = ?"
        row = self.db.execute_one(query, (note_id,))
        return self.db.row_to_dict(row)

    def _get_note_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Fetch a note by exact or partial title match."""
        # Try exact match first
        query = "SELECT * FROM notes WHERE title = ?"
        row = self.db.execute_one(query, (title,))
        if row:
            return self.db.row_to_dict(row)

        # Fall back to partial match
        query = "SELECT * FROM notes WHERE title LIKE ? ORDER BY created_at DESC LIMIT 1"
        row = self.db.execute_one(query, (f"%{title}%",))
        return self.db.row_to_dict(row)

    def _get_journal_for_date(self, date) -> Optional[Dict[str, Any]]:
        """Get journal entry for a specific date."""
        date_str = date.strftime("%Y-%m-%d")
        query = """
            SELECT * FROM notes
            WHERE note_type = 'journal'
            AND date(created_at) = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        row = self.db.execute_one(query, (date_str,))
        return self.db.row_to_dict(row)

    def _append_to_journal(
        self, journal: Dict[str, Any], content: str, mood: Optional[str]
    ) -> AgentResponse:
        """Append content to an existing journal entry."""
        try:
            full_path = self.notes_dir / journal["file_path"]
            existing_content = full_path.read_text(encoding="utf-8") if full_path.exists() else ""

            # Add timestamp and new entry
            now = datetime.now(timezone.utc)
            new_entry = f"\n\n---\n\n**{now.strftime('%H:%M')}**"
            if mood:
                new_entry += f" (mood: {mood})"
            new_entry += f"\n\n{content}"

            full_path.write_text(existing_content + new_entry, encoding="utf-8")

            # Update word count
            total_words = len((existing_content + new_entry).split())
            self._update_note(journal["id"], {"word_count": total_words})

            return AgentResponse.ok(
                message=f"Added entry to today's journal",
                data={
                    "note_id": journal["id"],
                    "note": self._get_note_by_id(journal["id"])
                }
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to append to journal: {str(e)}")

    def _update_note(self, note_id: int, fields: Dict[str, Any]) -> bool:
        """Update specified note fields."""
        if not fields:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        query = f"UPDATE notes SET {set_clause} WHERE id = ?"
        params = tuple(fields.values()) + (note_id,)

        result = self.db.execute_write(query, params)
        return result > 0

    def _delete_note_from_db(self, note_id: int) -> bool:
        """Permanently delete a note from the database."""
        # First delete any links
        self.db.execute_write(
            "DELETE FROM note_links WHERE source_note_id = ? OR target_note_id = ?",
            (note_id, note_id)
        )
        # Then delete the note
        result = self.db.execute_write("DELETE FROM notes WHERE id = ?", (note_id,))
        return result > 0

    def _fetch_notes(
        self,
        filters: Dict[str, Any],
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetch notes with filters and sorting."""
        conditions = []
        params = []

        if "note_type" in filters:
            conditions.append("note_type = ?")
            params.append(filters["note_type"])

        if "para_category_id" in filters:
            conditions.append("para_category_id = ?")
            params.append(filters["para_category_id"])

        if "tags" in filters:
            # Match any of the provided tags
            tag_conditions = []
            for tag in filters["tags"]:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")

        if "created_after" in filters:
            conditions.append("created_at >= ?")
            params.append(filters["created_after"])

        if "created_before" in filters:
            conditions.append("created_at <= ?")
            params.append(filters["created_before"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Validate sort field
        valid_sort_fields = ["created_at", "updated_at", "title", "word_count"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"

        query = f"""
            SELECT * FROM notes
            WHERE {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT ?
        """
        params.append(limit)

        rows = self.db.execute(query, tuple(params))
        return self.db.rows_to_dicts(rows)

    def _search_notes_in_db(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search notes by title and tags in database."""
        search_term = f"%{query}%"

        sql = """
            SELECT * FROM notes
            WHERE title LIKE ? OR tags LIKE ?
            ORDER BY
                CASE
                    WHEN title LIKE ? THEN 1
                    WHEN title LIKE ? THEN 2
                    ELSE 3
                END,
                created_at DESC
            LIMIT ?
        """
        params = (search_term, search_term, query, f"{query}%", limit)

        rows = self.db.execute(sql, params)
        return self.db.rows_to_dicts(rows)

    def _search_notes_in_files(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search notes by content in files."""
        results = []
        query_lower = query.lower()

        try:
            for md_file in self.notes_dir.rglob("*.md"):
                if len(results) >= limit:
                    break
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        # Get note from database by file path
                        relative_path = md_file.relative_to(self.notes_dir)
                        sql = "SELECT * FROM notes WHERE file_path = ?"
                        row = self.db.execute_one(sql, (str(relative_path),))
                        if row:
                            note = self.db.row_to_dict(row)
                            # Add snippet with match context
                            note["match_snippet"] = self._extract_snippet(content, query)
                            results.append(note)
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f"Error searching files: {e}")

        return results

    def _extract_snippet(self, content: str, query: str, context_chars: int = 100) -> str:
        """Extract a snippet of content around the search query match."""
        query_lower = query.lower()
        content_lower = content.lower()

        pos = content_lower.find(query_lower)
        if pos == -1:
            return ""

        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(query) + context_chars)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    # =========================================================================
    # Note Links Operations
    # =========================================================================

    def _create_note_link(
        self, source_id: int, target_id: int, link_type: str
    ) -> int:
        """Create a link between two notes."""
        query = """
            INSERT INTO note_links (source_note_id, target_note_id, link_type)
            VALUES (?, ?, ?)
        """
        return self.db.execute_write(query, (source_id, target_id, link_type))

    def _get_reverse_link_type(self, link_type: str) -> Optional[str]:
        """Get the reverse link type for bidirectional linking."""
        reverse_map = {
            "parent": "child",
            "child": "parent",
            "related": "related",
            "reference": "reference"
        }
        return reverse_map.get(link_type)

    def _get_linked_notes(
        self, note_id: int, link_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all notes linked to/from a specific note."""
        params = [note_id, note_id]

        type_filter = ""
        if link_type:
            type_filter = "AND nl.link_type = ?"
            params.append(link_type)

        query = f"""
            SELECT DISTINCT n.*, nl.link_type,
                   CASE WHEN nl.source_note_id = ? THEN 'outgoing' ELSE 'incoming' END as link_direction
            FROM notes n
            JOIN note_links nl ON (n.id = nl.target_note_id AND nl.source_note_id = ?)
                               OR (n.id = nl.source_note_id AND nl.target_note_id = ?)
            WHERE n.id != ?
            {type_filter}
            ORDER BY n.title
        """
        params = [note_id, note_id, note_id, note_id]
        if link_type:
            params.append(link_type)

        rows = self.db.execute(query, tuple(params))
        return self.db.rows_to_dicts(rows)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_tags_from_db(self, tags_json: Optional[str]) -> List[str]:
        """Parse tags from JSON string stored in database."""
        if not tags_json:
            return []
        try:
            return json.loads(tags_json)
        except (json.JSONDecodeError, TypeError):
            return []

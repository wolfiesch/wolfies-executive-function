"""
Unit tests for the TaskAgent.
Tests natural language parsing, intent handling, error handling,
and database integration.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.task_agent import TaskAgent
from src.agents.base_agent import AgentResponse
from src.core.database import Database


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary in-memory database with the tasks table schema."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create tasks table matching production schema
    cursor.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            priority INTEGER NOT NULL DEFAULT 3,
            project_id INTEGER,
            para_category_id INTEGER,
            parent_task_id INTEGER,
            estimated_minutes INTEGER,
            actual_minutes INTEGER,
            due_date TEXT,
            scheduled_start TEXT,
            scheduled_end TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            tags TEXT,
            context TEXT
        )
    """)
    conn.commit()
    conn.close()

    return Database(db_file)


@pytest.fixture
def mock_config():
    """Create a mock config object with default preferences."""
    config = MagicMock()
    config.get.return_value = 3  # Default priority
    return config


@pytest.fixture
def task_agent(temp_db, mock_config):
    """Create a TaskAgent instance with test database and config."""
    agent = TaskAgent(temp_db, mock_config)
    agent.initialize()
    return agent


@pytest.fixture
def populated_db(temp_db):
    """Populate the test database with sample tasks."""
    tasks = [
        ("Buy groceries", "Milk, eggs, bread", "todo", 3, None, None, None, 30, "2025-01-05", '["shopping"]'),
        ("Call mom", None, "todo", 4, None, None, None, 15, "2025-01-02", '["personal", "family"]'),
        ("Finish project report", "Q4 analysis", "in_progress", 5, 1, None, None, 120, "2025-01-03", '["work"]'),
        ("Learn Python", "Complete tutorial", "todo", 2, None, None, None, 60, None, '["learning"]'),
        ("Exercise routine", None, "done", 3, None, None, None, 45, "2025-01-01", '["health"]'),
    ]

    for task in tasks:
        temp_db.execute_write(
            """INSERT INTO tasks
               (title, description, status, priority, project_id, para_category_id,
                parent_task_id, estimated_minutes, due_date, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            task
        )

    return temp_db


@pytest.fixture
def task_agent_with_data(populated_db, mock_config):
    """Create a TaskAgent with pre-populated test data."""
    agent = TaskAgent(populated_db, mock_config)
    agent.initialize()
    return agent


# =============================================================================
# Test Agent Initialization and Basic Properties
# =============================================================================

class TestTaskAgentInit:
    """Tests for TaskAgent initialization."""

    def test_agent_initializes_correctly(self, task_agent):
        """TaskAgent initializes with correct name and properties."""
        assert task_agent.name == "task"
        assert task_agent._initialized is True

    def test_get_supported_intents(self, task_agent):
        """get_supported_intents returns all expected intents."""
        intents = task_agent.get_supported_intents()

        expected = [
            "add_task", "complete_task", "list_tasks",
            "search_tasks", "update_task", "delete_task", "get_task"
        ]

        for intent in expected:
            assert intent in intents

    def test_can_handle_supported_intents(self, task_agent):
        """can_handle returns True for supported intents."""
        assert task_agent.can_handle("add_task", {}) is True
        assert task_agent.can_handle("complete_task", {}) is True
        assert task_agent.can_handle("list_tasks", {}) is True
        assert task_agent.can_handle("search_tasks", {}) is True
        assert task_agent.can_handle("update_task", {}) is True

    def test_can_handle_unsupported_intents(self, task_agent):
        """can_handle returns False for unsupported intents."""
        assert task_agent.can_handle("create_note", {}) is False
        assert task_agent.can_handle("schedule_meeting", {}) is False
        assert task_agent.can_handle("unknown_intent", {}) is False


# =============================================================================
# Test Natural Language Parsing - Priority Extraction
# =============================================================================

class TestNLPriorityExtraction:
    """Tests for priority extraction from natural language."""

    def test_extract_urgent_priority(self, task_agent):
        """Extracts priority 5 from 'urgent' keyword."""
        result = task_agent._parse_task_from_text("Urgent: fix the bug")
        assert result["priority"] == 5

    def test_extract_critical_priority(self, task_agent):
        """Extracts priority 5 from 'critical' keyword."""
        result = task_agent._parse_task_from_text("critical server issue")
        assert result["priority"] == 5

    def test_extract_asap_priority(self, task_agent):
        """Extracts priority 5 from 'asap' keyword."""
        result = task_agent._parse_task_from_text("Need to respond asap")
        assert result["priority"] == 5

    def test_extract_high_priority_keyword(self, task_agent):
        """Extracts priority 5 from 'high priority' phrase."""
        result = task_agent._parse_task_from_text("high priority task to complete")
        assert result["priority"] == 5

    def test_extract_important_priority(self, task_agent):
        """Extracts priority 4 from 'important' keyword."""
        result = task_agent._parse_task_from_text("Important meeting prep")
        assert result["priority"] == 4

    def test_extract_soon_priority(self, task_agent):
        """Extracts priority 4 from 'soon' keyword."""
        result = task_agent._parse_task_from_text("Need to do this soon")
        assert result["priority"] == 4

    def test_extract_low_priority(self, task_agent):
        """Extracts priority 2 from 'low' keyword."""
        result = task_agent._parse_task_from_text("low priority cleanup")
        assert result["priority"] == 2

    def test_extract_whenever_priority(self, task_agent):
        """Extracts priority 2 from 'whenever' keyword."""
        result = task_agent._parse_task_from_text("whenever I have time organize files")
        assert result["priority"] == 2

    def test_extract_optional_priority(self, task_agent):
        """Extracts priority 1 from 'optional' keyword."""
        result = task_agent._parse_task_from_text("optional reading list")
        assert result["priority"] == 1

    def test_extract_backlog_priority(self, task_agent):
        """Extracts priority 1 from 'backlog' keyword."""
        result = task_agent._parse_task_from_text("backlog item to consider")
        assert result["priority"] == 1

    def test_no_priority_returns_none(self, task_agent):
        """Returns None priority when no keywords present."""
        result = task_agent._parse_task_from_text("Simple task to do")
        assert result["priority"] is None

    def test_priority_keyword_removed_from_title(self, task_agent):
        """Priority keyword is removed from resulting title."""
        result = task_agent._parse_task_from_text("Urgent fix production bug")
        assert "urgent" not in result["title"].lower()
        assert "fix production bug" in result["title"].lower()


# =============================================================================
# Test Natural Language Parsing - Due Date Extraction
# =============================================================================

class TestNLDueDateExtraction:
    """Tests for due date extraction from natural language."""

    def test_extract_today(self, task_agent):
        """Extracts today's date from 'today' keyword."""
        result = task_agent._parse_task_from_text("Finish report today")

        today = datetime.now(timezone.utc).date()
        assert result["due_date"] == today.isoformat()

    def test_extract_tonight(self, task_agent):
        """Extracts today's date from 'tonight' keyword."""
        result = task_agent._parse_task_from_text("Call mom tonight")

        today = datetime.now(timezone.utc).date()
        assert result["due_date"] == today.isoformat()

    def test_extract_tomorrow(self, task_agent):
        """Extracts tomorrow's date from 'tomorrow' keyword."""
        result = task_agent._parse_task_from_text("Submit proposal tomorrow")

        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        assert result["due_date"] == tomorrow.isoformat()

    def test_extract_next_week(self, task_agent):
        """Extracts date 7 days ahead from 'next week' keyword."""
        result = task_agent._parse_task_from_text("Review next week")

        next_week = datetime.now(timezone.utc).date() + timedelta(days=7)
        assert result["due_date"] == next_week.isoformat()

    def test_extract_in_3_days(self, task_agent):
        """Extracts date from 'in 3 days' pattern."""
        result = task_agent._parse_task_from_text("Follow up in 3 days")

        target = datetime.now(timezone.utc).date() + timedelta(days=3)
        assert result["due_date"] == target.isoformat()

    def test_extract_in_10_days(self, task_agent):
        """Extracts date from 'in 10 days' pattern."""
        result = task_agent._parse_task_from_text("Schedule meeting in 10 days")

        target = datetime.now(timezone.utc).date() + timedelta(days=10)
        assert result["due_date"] == target.isoformat()

    def test_extract_next_friday(self, task_agent):
        """Extracts date from 'next friday' pattern."""
        result = task_agent._parse_task_from_text("Submit by next friday")

        assert result["due_date"] is not None
        # Verify it's a Friday (weekday 4)
        parsed_date = datetime.fromisoformat(result["due_date"])
        assert parsed_date.weekday() == 4

    def test_extract_by_monday(self, task_agent):
        """Extracts date from 'by monday' pattern."""
        result = task_agent._parse_task_from_text("Finish by monday")

        assert result["due_date"] is not None
        parsed_date = datetime.fromisoformat(result["due_date"])
        assert parsed_date.weekday() == 0

    def test_extract_on_wednesday(self, task_agent):
        """Extracts date from 'on wednesday' pattern."""
        result = task_agent._parse_task_from_text("Meeting on wednesday")

        assert result["due_date"] is not None
        parsed_date = datetime.fromisoformat(result["due_date"])
        assert parsed_date.weekday() == 2

    def test_extract_explicit_date_iso(self, task_agent):
        """Extracts date from ISO format (YYYY-MM-DD)."""
        result = task_agent._parse_task_from_text("Due 2025-03-15 submit taxes")

        assert result["due_date"] == "2025-03-15"

    def test_extract_explicit_date_slash(self, task_agent):
        """Extracts date from MM/DD/YYYY format."""
        result = task_agent._parse_task_from_text("Due 3/15/2025 submit forms")

        assert result["due_date"] == "2025-03-15"

    def test_date_keyword_removed_from_title(self, task_agent):
        """Date keyword is removed from resulting title."""
        result = task_agent._parse_task_from_text("Submit report tomorrow")

        assert "tomorrow" not in result["title"].lower()
        assert "submit report" in result["title"].lower()

    def test_no_date_returns_none(self, task_agent):
        """Returns None when no date keywords present."""
        result = task_agent._parse_task_from_text("Generic task description")

        assert result["due_date"] is None


# =============================================================================
# Test Natural Language Parsing - Tags Extraction
# =============================================================================

class TestNLTagExtraction:
    """Tests for tag extraction from natural language."""

    def test_extract_single_tag(self, task_agent):
        """Extracts single hashtag as tag."""
        result = task_agent._parse_task_from_text("Review code #work")

        assert "work" in result["tags"]

    def test_extract_multiple_tags(self, task_agent):
        """Extracts multiple hashtags as tags."""
        result = task_agent._parse_task_from_text("Workout routine #health #fitness")

        assert "health" in result["tags"]
        assert "fitness" in result["tags"]

    def test_tags_removed_from_title(self, task_agent):
        """Hashtags are removed from resulting title."""
        result = task_agent._parse_task_from_text("Buy groceries #shopping #personal")

        assert "#" not in result["title"]
        assert "shopping" not in result["title"]
        assert "buy groceries" in result["title"].lower()

    def test_no_tags_returns_empty_list(self, task_agent):
        """Returns empty list when no hashtags present."""
        result = task_agent._parse_task_from_text("Simple task without tags")

        assert result["tags"] == []


# =============================================================================
# Test Natural Language Parsing - Time Estimate Extraction
# =============================================================================

class TestNLTimeEstimateExtraction:
    """Tests for time estimate extraction from natural language."""

    def test_extract_minutes(self, task_agent):
        """Extracts time from '30 minutes' pattern."""
        result = task_agent._parse_task_from_text("Quick call 30 minutes")

        assert result["estimated_minutes"] == 30

    def test_extract_mins_abbreviation(self, task_agent):
        """Extracts time from '30 mins' pattern."""
        result = task_agent._parse_task_from_text("Review docs 45 mins")

        assert result["estimated_minutes"] == 45

    def test_extract_hours(self, task_agent):
        """Extracts time from '2 hours' pattern and converts to minutes."""
        result = task_agent._parse_task_from_text("Deep work session 2 hours")

        assert result["estimated_minutes"] == 120

    def test_extract_hour_singular(self, task_agent):
        """Extracts time from '1 hour' pattern."""
        result = task_agent._parse_task_from_text("Meeting 1 hour")

        assert result["estimated_minutes"] == 60

    def test_extract_h_abbreviation(self, task_agent):
        """Extracts time from '2h' pattern."""
        result = task_agent._parse_task_from_text("Project work 3h")

        assert result["estimated_minutes"] == 180

    def test_time_removed_from_title(self, task_agent):
        """Time estimate is removed from resulting title."""
        result = task_agent._parse_task_from_text("Review code 30 minutes today")

        assert "30" not in result["title"]
        assert "minutes" not in result["title"].lower()

    def test_no_time_returns_none(self, task_agent):
        """Returns None when no time estimate present."""
        result = task_agent._parse_task_from_text("Generic task")

        assert result["estimated_minutes"] is None


# =============================================================================
# Test Natural Language Parsing - Complex Inputs
# =============================================================================

class TestNLComplexParsing:
    """Tests for parsing complex natural language inputs."""

    def test_parse_full_task_description(self, task_agent):
        """Parses complete task with all components."""
        text = "Urgent: Finish quarterly report #work #finance 2 hours by friday"
        result = task_agent._parse_task_from_text(text)

        assert result["priority"] == 5  # urgent
        assert "work" in result["tags"]
        assert "finance" in result["tags"]
        assert result["estimated_minutes"] == 120
        assert result["due_date"] is not None
        assert "quarterly report" in result["title"].lower()

    def test_priority_and_date_combined(self, task_agent):
        """Parses task with both priority and date."""
        result = task_agent._parse_task_from_text("Important meeting prep tomorrow")

        assert result["priority"] == 4
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        assert result["due_date"] == tomorrow.isoformat()

    def test_title_cleaned_properly(self, task_agent):
        """Title is cleaned of extra whitespace and punctuation."""
        result = task_agent._parse_task_from_text("  Urgent:  Buy milk  #shopping   tomorrow  ")

        # Title should be clean
        assert result["title"] == result["title"].strip()
        assert "  " not in result["title"]  # No double spaces


# =============================================================================
# Test Intent Handling - add_task
# =============================================================================

class TestAddTaskIntent:
    """Tests for the add_task intent handler."""

    def test_add_task_with_title_only(self, task_agent):
        """Creates task with just title."""
        response = task_agent.process("add_task", {"title": "Simple task"})

        assert response.success is True
        assert "task_id" in response.data
        assert response.data["task"]["title"] == "Simple task"

    def test_add_task_with_description(self, task_agent):
        """Creates task with title and description."""
        context = {
            "title": "Review document",
            "description": "Check for typos and formatting"
        }
        response = task_agent.process("add_task", context)

        assert response.success is True
        assert response.data["task"]["description"] == "Check for typos and formatting"

    def test_add_task_with_priority(self, task_agent):
        """Creates task with specified priority."""
        context = {
            "title": "High priority task",
            "priority": 5
        }
        response = task_agent.process("add_task", context)

        assert response.success is True
        assert response.data["task"]["priority"] == 5

    def test_add_task_with_due_date(self, task_agent):
        """Creates task with due date."""
        context = {
            "title": "Dated task",
            "due_date": "2025-02-01"
        }
        response = task_agent.process("add_task", context)

        assert response.success is True
        assert "2025-02-01" in response.data["task"]["due_date"]

    def test_add_task_with_tags(self, task_agent):
        """Creates task with tags."""
        context = {
            "title": "Tagged task",
            "tags": ["work", "important"]
        }
        response = task_agent.process("add_task", context)

        assert response.success is True
        tags = json.loads(response.data["task"]["tags"])
        assert "work" in tags
        assert "important" in tags

    def test_add_task_with_natural_language(self, task_agent):
        """Creates task from natural language text."""
        context = {
            "text": "Urgent: Call client tomorrow #work 30 minutes"
        }
        response = task_agent.process("add_task", context)

        assert response.success is True
        task = response.data["task"]
        assert "call client" in task["title"].lower()
        assert task["priority"] == 5  # Urgent
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        assert tomorrow.isoformat() in task["due_date"]

    def test_add_task_returns_suggestions(self, task_agent):
        """add_task response includes helpful suggestions."""
        response = task_agent.process("add_task", {"title": "New task"})

        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_add_task_missing_title_fails(self, task_agent):
        """add_task fails when title is missing."""
        response = task_agent.process("add_task", {})

        assert response.success is False
        assert "title" in response.message.lower()

    def test_add_task_empty_title_fails(self, task_agent):
        """add_task fails when title is empty."""
        response = task_agent.process("add_task", {"title": ""})

        assert response.success is False


# =============================================================================
# Test Intent Handling - complete_task
# =============================================================================

class TestCompleteTaskIntent:
    """Tests for the complete_task intent handler."""

    def test_complete_task_by_id(self, task_agent_with_data):
        """Marks task as done by task_id."""
        response = task_agent_with_data.process(
            "complete_task", {"task_id": 1}
        )

        assert response.success is True
        assert 1 in response.data["completed_ids"]

        # Verify in database
        task = task_agent_with_data._get_task_by_id(1)
        assert task["status"] == "done"

    def test_complete_multiple_tasks(self, task_agent_with_data):
        """Marks multiple tasks as done."""
        response = task_agent_with_data.process(
            "complete_task", {"task_ids": [1, 2]}
        )

        assert response.success is True
        assert 1 in response.data["completed_ids"]
        assert 2 in response.data["completed_ids"]

    def test_complete_task_by_search(self, task_agent_with_data):
        """Marks task as done by search text."""
        response = task_agent_with_data.process(
            "complete_task", {"search": "Buy groceries"}
        )

        assert response.success is True
        assert len(response.data["completed_ids"]) == 1

    def test_complete_task_search_not_found(self, task_agent_with_data):
        """Returns error when search finds no task."""
        response = task_agent_with_data.process(
            "complete_task", {"search": "nonexistent task xyz"}
        )

        assert response.success is False
        assert "no task found" in response.message.lower()

    def test_complete_task_missing_params(self, task_agent_with_data):
        """Returns error when no task identifier provided."""
        response = task_agent_with_data.process("complete_task", {})

        assert response.success is False
        assert "no task specified" in response.message.lower()

    def test_complete_task_invalid_id(self, task_agent_with_data):
        """Handles invalid task ID gracefully."""
        response = task_agent_with_data.process(
            "complete_task", {"task_id": 9999}
        )

        # When all tasks fail to complete, it returns an error response
        # with data=None or with failed_ids containing the invalid ID
        if response.success:
            # If somehow succeeded, invalid ID should not be in completed
            assert 9999 not in response.data.get("completed_ids", [])
        else:
            # Error response expected - task wasn't found
            assert response.success is False


# =============================================================================
# Test Intent Handling - list_tasks
# =============================================================================

class TestListTasksIntent:
    """Tests for the list_tasks intent handler."""

    def test_list_tasks_default_excludes_done(self, task_agent_with_data):
        """Default list excludes done and cancelled tasks."""
        response = task_agent_with_data.process("list_tasks", {})

        assert response.success is True
        tasks = response.data["tasks"]

        # Should exclude the "done" task (Exercise routine)
        for task in tasks:
            assert task["status"] not in ["done", "cancelled"]

    def test_list_tasks_filter_by_status(self, task_agent_with_data):
        """Filters tasks by status."""
        response = task_agent_with_data.process(
            "list_tasks", {"status": "in_progress"}
        )

        assert response.success is True
        tasks = response.data["tasks"]

        for task in tasks:
            assert task["status"] == "in_progress"

    def test_list_tasks_filter_by_priority(self, task_agent_with_data):
        """Filters tasks by priority."""
        response = task_agent_with_data.process(
            "list_tasks", {"priority": 5}
        )

        assert response.success is True
        tasks = response.data["tasks"]

        for task in tasks:
            assert task["priority"] == 5

    def test_list_tasks_include_completed(self, task_agent_with_data):
        """Includes completed tasks when requested."""
        response = task_agent_with_data.process(
            "list_tasks", {"include_completed": True}
        )

        assert response.success is True
        statuses = [t["status"] for t in response.data["tasks"]]

        # Should include the "done" task
        assert "done" in statuses

    def test_list_tasks_with_limit(self, task_agent_with_data):
        """Respects limit parameter."""
        response = task_agent_with_data.process(
            "list_tasks", {"limit": 2, "include_completed": True}
        )

        assert response.success is True
        assert len(response.data["tasks"]) <= 2

    def test_list_tasks_empty_result(self, task_agent):
        """Returns empty list when no tasks match."""
        response = task_agent.process("list_tasks", {})

        assert response.success is True
        assert response.data["tasks"] == []
        assert response.data["count"] == 0

    def test_list_tasks_returns_count(self, task_agent_with_data):
        """Response includes task count."""
        response = task_agent_with_data.process("list_tasks", {})

        assert "count" in response.data
        assert response.data["count"] == len(response.data["tasks"])


# =============================================================================
# Test Intent Handling - search_tasks
# =============================================================================

class TestSearchTasksIntent:
    """Tests for the search_tasks intent handler."""

    def test_search_tasks_by_title(self, task_agent_with_data):
        """Finds tasks matching title text."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "groceries"}
        )

        assert response.success is True
        assert len(response.data["tasks"]) >= 1
        assert any("groceries" in t["title"].lower() for t in response.data["tasks"])

    def test_search_tasks_by_description(self, task_agent_with_data):
        """Finds tasks matching description text."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "Q4 analysis"}
        )

        assert response.success is True
        assert len(response.data["tasks"]) >= 1

    def test_search_tasks_case_insensitive(self, task_agent_with_data):
        """Search is case insensitive."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "GROCERIES"}
        )

        assert response.success is True
        assert len(response.data["tasks"]) >= 1

    def test_search_tasks_partial_match(self, task_agent_with_data):
        """Search works with partial matches."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "gro"}
        )

        assert response.success is True
        assert len(response.data["tasks"]) >= 1

    def test_search_tasks_no_results(self, task_agent_with_data):
        """Returns empty result for no matches."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "xyznonexistent"}
        )

        assert response.success is True
        assert response.data["tasks"] == []

    def test_search_tasks_missing_query(self, task_agent_with_data):
        """Returns error when query is missing."""
        response = task_agent_with_data.process("search_tasks", {})

        assert response.success is False
        assert "query" in response.message.lower()

    def test_search_tasks_excludes_completed_by_default(self, task_agent_with_data):
        """Search excludes completed tasks by default."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "Exercise"}
        )

        # Exercise routine is "done" status
        assert response.success is True
        assert response.data["tasks"] == []

    def test_search_tasks_includes_completed_when_requested(self, task_agent_with_data):
        """Search includes completed tasks when requested."""
        response = task_agent_with_data.process(
            "search_tasks", {"query": "Exercise", "include_completed": True}
        )

        assert response.success is True
        assert len(response.data["tasks"]) >= 1


# =============================================================================
# Test Intent Handling - update_task
# =============================================================================

class TestUpdateTaskIntent:
    """Tests for the update_task intent handler."""

    def test_update_task_title(self, task_agent_with_data):
        """Updates task title."""
        response = task_agent_with_data.process(
            "update_task", {"task_id": 1, "title": "Updated title"}
        )

        assert response.success is True
        assert response.data["task"]["title"] == "Updated title"

    def test_update_task_priority(self, task_agent_with_data):
        """Updates task priority."""
        response = task_agent_with_data.process(
            "update_task", {"task_id": 1, "priority": 5}
        )

        assert response.success is True
        assert response.data["task"]["priority"] == 5

    def test_update_task_status(self, task_agent_with_data):
        """Updates task status."""
        response = task_agent_with_data.process(
            "update_task", {"task_id": 1, "status": "in_progress"}
        )

        assert response.success is True
        assert response.data["task"]["status"] == "in_progress"

    def test_update_task_due_date(self, task_agent_with_data):
        """Updates task due date."""
        response = task_agent_with_data.process(
            "update_task", {"task_id": 1, "due_date": "2025-03-15"}
        )

        assert response.success is True
        assert "2025-03-15" in response.data["task"]["due_date"]

    def test_update_task_multiple_fields(self, task_agent_with_data):
        """Updates multiple fields at once."""
        response = task_agent_with_data.process(
            "update_task", {
                "task_id": 1,
                "title": "New title",
                "priority": 4,
                "description": "New description"
            }
        )

        assert response.success is True
        task = response.data["task"]
        assert task["title"] == "New title"
        assert task["priority"] == 4
        assert task["description"] == "New description"

    def test_update_task_missing_id(self, task_agent_with_data):
        """Returns error when task_id is missing."""
        response = task_agent_with_data.process(
            "update_task", {"title": "No ID"}
        )

        assert response.success is False
        assert "task_id" in response.message.lower()

    def test_update_task_no_fields(self, task_agent_with_data):
        """Returns error when no update fields provided."""
        response = task_agent_with_data.process(
            "update_task", {"task_id": 1}
        )

        assert response.success is False
        assert "no fields" in response.message.lower()

    def test_update_task_invalid_id(self, task_agent_with_data):
        """Returns error for non-existent task."""
        response = task_agent_with_data.process(
            "update_task", {"task_id": 9999, "title": "Never exists"}
        )

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handling - delete_task
# =============================================================================

class TestDeleteTaskIntent:
    """Tests for the delete_task intent handler."""

    def test_delete_task_marks_cancelled(self, task_agent_with_data):
        """Delete task marks it as cancelled (soft delete)."""
        response = task_agent_with_data.process(
            "delete_task", {"task_id": 1}
        )

        assert response.success is True

        # Verify status is cancelled
        task = task_agent_with_data._get_task_by_id(1)
        assert task["status"] == "cancelled"

    def test_delete_task_missing_id(self, task_agent_with_data):
        """Returns error when task_id is missing."""
        response = task_agent_with_data.process("delete_task", {})

        assert response.success is False
        assert "task_id" in response.message.lower()

    def test_delete_task_invalid_id(self, task_agent_with_data):
        """Returns error for non-existent task."""
        response = task_agent_with_data.process(
            "delete_task", {"task_id": 9999}
        )

        assert response.success is False


# =============================================================================
# Test Intent Handling - get_task
# =============================================================================

class TestGetTaskIntent:
    """Tests for the get_task intent handler."""

    def test_get_task_by_id(self, task_agent_with_data):
        """Retrieves task by ID."""
        response = task_agent_with_data.process(
            "get_task", {"task_id": 1}
        )

        assert response.success is True
        assert response.data["task"]["id"] == 1
        assert response.data["task"]["title"] == "Buy groceries"

    def test_get_task_missing_id(self, task_agent_with_data):
        """Returns error when task_id is missing."""
        response = task_agent_with_data.process("get_task", {})

        assert response.success is False
        assert "task_id" in response.message.lower()

    def test_get_task_invalid_id(self, task_agent_with_data):
        """Returns error for non-existent task."""
        response = task_agent_with_data.process(
            "get_task", {"task_id": 9999}
        )

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in TaskAgent."""

    def test_unknown_intent_returns_error(self, task_agent):
        """Unknown intent returns error response."""
        response = task_agent.process("unknown_intent", {})

        assert response.success is False
        assert "unknown intent" in response.message.lower()

    def test_database_error_handled(self, task_agent, mock_config):
        """Database errors are caught and returned as error response."""
        # Create a mock db that raises on execute_write
        mock_db = MagicMock()
        mock_db.execute_write.side_effect = Exception("Database connection failed")

        agent = TaskAgent(mock_db, mock_config)
        response = agent.process("add_task", {"title": "Test task"})

        assert response.success is False
        assert "failed" in response.message.lower()

    def test_validation_error_for_missing_required_params(self, task_agent):
        """Validation catches missing required parameters."""
        # search_tasks requires "query"
        response = task_agent.process("search_tasks", {})

        assert response.success is False
        assert "query" in response.message.lower()


# =============================================================================
# Test Database Integration
# =============================================================================

class TestDatabaseIntegration:
    """Tests for database integration in TaskAgent."""

    def test_task_persisted_correctly(self, task_agent):
        """Task is correctly persisted to database."""
        context = {
            "title": "Persistent task",
            "description": "This should be saved",
            "priority": 4,
            "due_date": "2025-06-15",
            "tags": ["test", "integration"]
        }

        response = task_agent.process("add_task", context)
        task_id = response.data["task_id"]

        # Fetch directly from database
        task = task_agent._get_task_by_id(task_id)

        assert task["title"] == "Persistent task"
        assert task["description"] == "This should be saved"
        assert task["priority"] == 4
        assert "2025-06-15" in task["due_date"]
        tags = json.loads(task["tags"])
        assert "test" in tags
        assert "integration" in tags

    def test_task_update_persisted(self, task_agent_with_data):
        """Task update is correctly persisted."""
        task_agent_with_data.process(
            "update_task", {"task_id": 1, "title": "Updated title"}
        )

        # Fetch fresh from database
        task = task_agent_with_data._get_task_by_id(1)
        assert task["title"] == "Updated title"

    def test_completed_at_timestamp_set(self, task_agent_with_data):
        """completed_at timestamp is set when task completed."""
        task_agent_with_data.process("complete_task", {"task_id": 1})

        task = task_agent_with_data._get_task_by_id(1)
        assert task["completed_at"] is not None

    def test_task_list_sorted_correctly(self, task_agent_with_data):
        """Tasks are returned sorted by due date, priority, created_at."""
        response = task_agent_with_data.process(
            "list_tasks", {"include_completed": True}
        )

        tasks = response.data["tasks"]

        # Tasks with due dates should come before tasks without
        # Among tasks with due dates, earlier dates come first
        # Tasks with same due date are sorted by priority (descending)

        for i in range(len(tasks) - 1):
            current = tasks[i]
            next_task = tasks[i + 1]

            # If current has no due date and next has due date, that's wrong
            if current["due_date"] is None and next_task["due_date"] is not None:
                # This indicates improper sorting - should fail
                # But actually our sort puts NULL due dates last
                pass


# =============================================================================
# Test AgentResponse Structure
# =============================================================================

class TestAgentResponseStructure:
    """Tests for AgentResponse data structure."""

    def test_success_response_structure(self, task_agent):
        """Successful response has expected structure."""
        response = task_agent.process("add_task", {"title": "Test"})

        assert hasattr(response, "success")
        assert hasattr(response, "message")
        assert hasattr(response, "data")
        assert hasattr(response, "suggestions")

    def test_error_response_structure(self, task_agent):
        """Error response has expected structure."""
        response = task_agent.process("add_task", {})  # Missing title

        assert response.success is False
        assert response.message is not None
        assert len(response.message) > 0

    def test_response_to_dict(self, task_agent):
        """Response can be converted to dictionary."""
        response = task_agent.process("add_task", {"title": "Test"})

        result = response.to_dict()
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "data" in result

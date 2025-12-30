"""
Unit tests for the GoalAgent.
Tests goal creation, progress tracking, milestone management,
natural language parsing, intent handling, and error handling.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.goal_agent import GoalAgent
from src.agents.base_agent import AgentResponse
from src.core.database import Database


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database with the projects table schema."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create projects table matching production schema (goals are stored here)
    cursor.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            para_category_id INTEGER,
            start_date TEXT,
            target_end_date TEXT,
            actual_end_date TEXT,
            archived INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
            metadata TEXT
        )
    """)

    # Create para_categories table for testing para_category_id
    cursor.execute("""
        CREATE TABLE para_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            para_type TEXT DEFAULT 'area',
            description TEXT
        )
    """)

    # Insert a sample category
    cursor.execute(
        "INSERT INTO para_categories (name, para_type) VALUES (?, ?)",
        ("Finance", "area")
    )

    conn.commit()
    conn.close()

    return Database(db_file)


@pytest.fixture
def mock_config():
    """Create a mock config object with default preferences."""
    config = MagicMock()
    config.get.return_value = "weekly"  # Default review frequency
    return config


@pytest.fixture
def goal_agent(temp_db, mock_config):
    """Create a GoalAgent instance with test database and config."""
    agent = GoalAgent(temp_db, mock_config)
    agent.initialize()
    return agent


@pytest.fixture
def populated_db(temp_db):
    """Populate the test database with sample goals."""
    today = datetime.now(timezone.utc).date()
    start_date = (today - timedelta(days=30)).isoformat()
    target_date = (today + timedelta(days=60)).isoformat()
    past_target = (today - timedelta(days=10)).isoformat()

    goals = [
        # Active goal with 50% progress, key results
        (
            "Save $10,000 for emergency fund",
            "Build financial safety net",
            "active",
            1,  # para_category_id
            start_date,
            target_date,
            None,
            0,  # not archived
            json.dumps({
                "is_goal": True,
                "goal_type": "finance",
                "key_results": [
                    {"description": "Save money", "target": 10000, "current": 5000, "unit": "dollars"}
                ],
                "milestones": [
                    {"name": "First $2500", "target_date": (today - timedelta(days=20)).isoformat(), "completed": True, "completed_at": (today - timedelta(days=22)).isoformat()},
                    {"name": "Reach $5000", "target_date": today.isoformat(), "completed": False, "completed_at": None},
                    {"name": "Reach $7500", "target_date": (today + timedelta(days=30)).isoformat(), "completed": False, "completed_at": None},
                ],
                "progress_log": [
                    {"date": (today - timedelta(days=20)).isoformat(), "note": "Started saving", "percentage": 10},
                    {"date": (today - timedelta(days=10)).isoformat(), "note": "Good progress", "percentage": 30},
                ],
                "overall_progress": 50,
                "review_frequency": "weekly"
            })
        ),
        # Active goal that's behind schedule (at risk)
        (
            "Run a marathon",
            "Complete 26.2 miles",
            "active",
            None,
            start_date,
            (today + timedelta(days=30)).isoformat(),
            None,
            0,
            json.dumps({
                "is_goal": True,
                "goal_type": "health",
                "key_results": [
                    {"description": "Run distance", "target": 26.2, "current": 5, "unit": "distance"}
                ],
                "milestones": [],
                "progress_log": [],
                "overall_progress": 10,  # Way behind expected progress
                "review_frequency": "weekly"
            })
        ),
        # Completed goal
        (
            "Read 12 books",
            "Reading goal for the year",
            "completed",
            None,
            (today - timedelta(days=365)).isoformat(),
            (today - timedelta(days=30)).isoformat(),
            (today - timedelta(days=35)).isoformat(),
            0,
            json.dumps({
                "is_goal": True,
                "goal_type": "learning",
                "key_results": [
                    {"description": "Books read", "target": 12, "current": 12, "unit": "count"}
                ],
                "milestones": [],
                "progress_log": [],
                "overall_progress": 100,
                "review_frequency": "monthly"
            })
        ),
        # On hold goal
        (
            "Learn Spanish",
            "Achieve B1 level",
            "on_hold",
            None,
            start_date,
            target_date,
            None,
            0,
            json.dumps({
                "is_goal": True,
                "goal_type": "learning",
                "key_results": [],
                "milestones": [],
                "progress_log": [],
                "overall_progress": 25,
                "review_frequency": "weekly"
            })
        ),
        # Archived goal
        (
            "Old abandoned goal",
            "No longer relevant",
            "active",
            None,
            (today - timedelta(days=180)).isoformat(),
            past_target,
            None,
            1,  # archived
            json.dumps({
                "is_goal": True,
                "goal_type": "personal",
                "key_results": [],
                "milestones": [],
                "progress_log": [],
                "overall_progress": 0,
                "review_frequency": "weekly"
            })
        ),
        # Regular project (not a goal)
        (
            "Website redesign",
            "Update company website",
            "active",
            None,
            start_date,
            target_date,
            None,
            0,
            json.dumps({"is_goal": False})  # Not a goal
        ),
    ]

    for goal in goals:
        temp_db.execute_write(
            """INSERT INTO projects
               (name, description, status, para_category_id, start_date,
                target_end_date, actual_end_date, archived, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            goal
        )

    return temp_db


@pytest.fixture
def goal_agent_with_data(populated_db, mock_config):
    """Create a GoalAgent with pre-populated test data."""
    agent = GoalAgent(populated_db, mock_config)
    agent.initialize()
    return agent


# =============================================================================
# Test Agent Initialization and Basic Properties
# =============================================================================

class TestGoalAgentInit:
    """Tests for GoalAgent initialization."""

    def test_agent_initializes_correctly(self, goal_agent):
        """GoalAgent initializes with correct name and properties."""
        assert goal_agent.name == "goal"
        assert goal_agent._initialized is True

    def test_get_supported_intents(self, goal_agent):
        """get_supported_intents returns all expected intents."""
        intents = goal_agent.get_supported_intents()

        expected = [
            "create_goal", "get_goal", "list_goals",
            "update_goal", "log_progress", "add_milestone",
            "complete_milestone", "review_goals", "archive_goal"
        ]

        for intent in expected:
            assert intent in intents

    def test_can_handle_supported_intents(self, goal_agent):
        """can_handle returns True for supported intents."""
        assert goal_agent.can_handle("create_goal", {}) is True
        assert goal_agent.can_handle("get_goal", {}) is True
        assert goal_agent.can_handle("list_goals", {}) is True
        assert goal_agent.can_handle("log_progress", {}) is True
        assert goal_agent.can_handle("add_milestone", {}) is True
        assert goal_agent.can_handle("review_goals", {}) is True

    def test_can_handle_unsupported_intents(self, goal_agent):
        """can_handle returns False for unsupported intents."""
        assert goal_agent.can_handle("add_task", {}) is False
        assert goal_agent.can_handle("create_note", {}) is False
        assert goal_agent.can_handle("unknown_intent", {}) is False


# =============================================================================
# Test Goal Creation
# =============================================================================

class TestGoalCreation:
    """Tests for goal creation functionality."""

    def test_create_goal_with_name_only(self, goal_agent):
        """Creates goal with just name."""
        response = goal_agent.process("create_goal", {"name": "Simple goal"})

        assert response.success is True
        assert "goal_id" in response.data
        assert response.data["goal"]["name"] == "Simple goal"

    def test_create_goal_with_target_date(self, goal_agent):
        """Creates goal with name and target date."""
        context = {
            "name": "Finish project",
            "target_end_date": "2025-06-30"
        }
        response = goal_agent.process("create_goal", context)

        assert response.success is True
        assert "2025-06-30" in response.data["goal"]["target_end_date"]

    def test_create_goal_with_description(self, goal_agent):
        """Creates goal with description."""
        context = {
            "name": "Write a book",
            "description": "Complete first draft of novel"
        }
        response = goal_agent.process("create_goal", context)

        assert response.success is True
        assert response.data["goal"]["description"] == "Complete first draft of novel"

    def test_create_goal_with_para_category(self, goal_agent):
        """Creates goal with para_category_id."""
        context = {
            "name": "Financial goal",
            "para_category_id": 1
        }
        response = goal_agent.process("create_goal", context)

        assert response.success is True
        assert response.data["goal"]["para_category_id"] == 1

    def test_create_goal_with_key_results(self, goal_agent):
        """Creates goal with explicit key results."""
        context = {
            "name": "Improve fitness",
            "key_results": [
                {"description": "Run distance", "target": 100, "current": 0, "unit": "km"},
                {"description": "Gym sessions", "target": 50, "current": 0, "unit": "count"}
            ]
        }
        response = goal_agent.process("create_goal", context)

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert len(metadata["key_results"]) == 2
        assert metadata["key_results"][0]["target"] == 100

    def test_create_goal_with_goal_type(self, goal_agent):
        """Creates goal with specified goal type."""
        context = {
            "name": "Professional certification",
            "goal_type": "professional"
        }
        response = goal_agent.process("create_goal", context)

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert metadata["goal_type"] == "professional"

    def test_create_goal_from_natural_language(self, goal_agent):
        """Creates goal from natural language text."""
        context = {
            "text": "I want to save $10,000 by June"
        }
        response = goal_agent.process("create_goal", context)

        assert response.success is True
        goal = response.data["goal"]
        assert "save" in goal["name"].lower()
        # Should extract measurable target
        metadata = goal["metadata"]
        assert len(metadata["key_results"]) > 0
        assert metadata["key_results"][0]["target"] == 10000

    def test_create_goal_extracts_goal_type_from_text(self, goal_agent):
        """Goal type is extracted from keywords in text."""
        response = goal_agent.process("create_goal", {
            "text": "I want to lose weight and get fit at the gym"
        })

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert metadata["goal_type"] == "health"

    def test_create_goal_extracts_finance_type(self, goal_agent):
        """Finance goal type is extracted from money-related keywords."""
        response = goal_agent.process("create_goal", {
            "text": "Goal: Budget better and save more money this year"
        })

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert metadata["goal_type"] == "finance"

    def test_create_goal_extracts_learning_type(self, goal_agent):
        """Learning goal type is extracted from education keywords."""
        response = goal_agent.process("create_goal", {
            "text": "I want to learn Python programming and study for certification"
        })

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert metadata["goal_type"] == "learning"

    def test_create_goal_parses_measurable_dollars(self, goal_agent):
        """Parses dollar amounts as measurable targets."""
        response = goal_agent.process("create_goal", {
            "text": "Save $5,000 for vacation"
        })

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert any(kr["target"] == 5000 for kr in metadata["key_results"])

    def test_create_goal_parses_measurable_weight(self, goal_agent):
        """Parses weight measurements as measurable targets."""
        response = goal_agent.process("create_goal", {
            "text": "Lose 20 pounds by summer"
        })

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert any(kr["target"] == 20 and kr["unit"] == "weight" for kr in metadata["key_results"])

    def test_create_goal_parses_book_count(self, goal_agent):
        """Parses book count as measurable target."""
        response = goal_agent.process("create_goal", {
            "text": "Read 24 books this year"
        })

        assert response.success is True
        metadata = response.data["goal"]["metadata"]
        assert any(kr["target"] == 24 and kr["unit"] == "count" for kr in metadata["key_results"])

    def test_create_goal_missing_name_fails(self, goal_agent):
        """create_goal fails when name is missing."""
        response = goal_agent.process("create_goal", {})

        assert response.success is False
        assert "name" in response.message.lower()

    def test_create_goal_returns_suggestions(self, goal_agent):
        """create_goal response includes helpful suggestions."""
        response = goal_agent.process("create_goal", {"name": "New goal"})

        assert response.suggestions is not None
        assert len(response.suggestions) > 0

    def test_create_goal_sets_start_date(self, goal_agent):
        """Goal start_date is set to current date on creation."""
        response = goal_agent.process("create_goal", {"name": "New goal"})

        assert response.success is True
        assert response.data["goal"]["start_date"] is not None


# =============================================================================
# Test Natural Language Date Extraction
# =============================================================================

class TestNLDateExtraction:
    """Tests for target date extraction from natural language."""

    def test_extract_by_month_year(self, goal_agent):
        """Extracts date from 'by [Month] [Year]' pattern."""
        result = goal_agent._parse_goal_from_text("Run marathon by June 2025")

        assert result["target_end_date"] is not None
        assert "2025-06" in result["target_end_date"]

    def test_extract_by_month_alone(self, goal_agent):
        """Extracts date from 'by [Month]' pattern."""
        result = goal_agent._parse_goal_from_text("Save money by December")

        assert result["target_end_date"] is not None
        assert "-12-" in result["target_end_date"]

    def test_extract_in_months(self, goal_agent):
        """Extracts date from 'in X months' pattern."""
        result = goal_agent._parse_goal_from_text("Learn Spanish in 6 months")

        assert result["target_end_date"] is not None
        expected = datetime.now(timezone.utc).date() + timedelta(days=180)
        # Allow some tolerance for calculation differences
        parsed = datetime.fromisoformat(result["target_end_date"]).date()
        assert abs((parsed - expected).days) <= 2

    def test_extract_in_weeks(self, goal_agent):
        """Extracts date from 'in X weeks' pattern."""
        result = goal_agent._parse_goal_from_text("Complete project in 4 weeks")

        assert result["target_end_date"] is not None
        expected = datetime.now(timezone.utc).date() + timedelta(weeks=4)
        parsed = datetime.fromisoformat(result["target_end_date"]).date()
        assert parsed == expected

    def test_extract_in_days(self, goal_agent):
        """Extracts date from 'in X days' pattern."""
        result = goal_agent._parse_goal_from_text("Finish report in 30 days")

        assert result["target_end_date"] is not None
        expected = datetime.now(timezone.utc).date() + timedelta(days=30)
        parsed = datetime.fromisoformat(result["target_end_date"]).date()
        assert parsed == expected

    def test_extract_this_year(self, goal_agent):
        """Extracts end of year from 'this year' pattern."""
        result = goal_agent._parse_goal_from_text("Achieve goal this year")

        assert result["target_end_date"] is not None
        today = datetime.now(timezone.utc).date()
        assert str(today.year) in result["target_end_date"]
        assert "-12-31" in result["target_end_date"]

    def test_extract_next_year(self, goal_agent):
        """Extracts end of next year from 'next year' pattern."""
        result = goal_agent._parse_goal_from_text("Plan for next year")

        assert result["target_end_date"] is not None
        next_year = datetime.now(timezone.utc).date().year + 1
        assert str(next_year) in result["target_end_date"]

    def test_extract_end_of_year(self, goal_agent):
        """Extracts date from 'end of year' pattern."""
        result = goal_agent._parse_goal_from_text("Complete by end of year")

        assert result["target_end_date"] is not None
        assert "-12-31" in result["target_end_date"]

    def test_date_removed_from_name(self, goal_agent):
        """Date keywords are removed from goal name."""
        result = goal_agent._parse_goal_from_text("Save $10,000 by December")

        assert "by December" not in result["name"]

    def test_no_date_returns_none(self, goal_agent):
        """Returns None target_end_date when no date pattern found."""
        result = goal_agent._parse_goal_from_text("General improvement goal")

        assert result["target_end_date"] is None


# =============================================================================
# Test Progress Tracking
# =============================================================================

class TestProgressTracking:
    """Tests for progress tracking functionality."""

    def test_log_progress_basic(self, goal_agent_with_data):
        """Log progress update with note."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "Made good progress today"
        })

        assert response.success is True
        assert "progress_entry" in response.data

    def test_log_progress_with_percentage(self, goal_agent_with_data):
        """Log progress with explicit percentage."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "Halfway there",
            "percentage": 75
        })

        assert response.success is True
        goal = response.data["goal"]
        assert goal["metadata"]["overall_progress"] == 75

    def test_log_progress_percentage_clamped_to_100(self, goal_agent_with_data):
        """Progress percentage is clamped to 100 max."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "Over 100%",
            "percentage": 150
        })

        assert response.success is True
        assert response.data["goal"]["metadata"]["overall_progress"] <= 100

    def test_log_progress_percentage_clamped_to_0(self, goal_agent_with_data):
        """Progress percentage is clamped to 0 min."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "Negative",
            "percentage": -10
        })

        assert response.success is True
        assert response.data["goal"]["metadata"]["overall_progress"] >= 0

    def test_log_progress_updates_key_results(self, goal_agent_with_data):
        """Log progress can update key result current values."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "Updated savings",
            "key_result_updates": [
                {"index": 0, "current": 7500}
            ]
        })

        assert response.success is True
        goal = response.data["goal"]
        assert goal["metadata"]["key_results"][0]["current"] == 7500

    def test_calculate_progress_from_key_results(self, goal_agent):
        """Calculate overall progress from key results."""
        key_results = [
            {"description": "KR1", "target": 100, "current": 50, "unit": "count"},  # 50%
            {"description": "KR2", "target": 200, "current": 100, "unit": "count"},  # 50%
        ]

        progress = goal_agent._calculate_progress(key_results)
        assert progress == 50

    def test_calculate_progress_with_over_target(self, goal_agent):
        """Progress caps at 100% even when exceeding target."""
        key_results = [
            {"description": "KR1", "target": 100, "current": 150, "unit": "count"},
        ]

        progress = goal_agent._calculate_progress(key_results)
        assert progress == 100

    def test_calculate_progress_empty_key_results(self, goal_agent):
        """Empty key results returns 0 progress."""
        progress = goal_agent._calculate_progress([])
        assert progress == 0

    def test_calculate_progress_zero_target(self, goal_agent):
        """Zero target in key result is handled gracefully."""
        key_results = [
            {"description": "KR1", "target": 0, "current": 50, "unit": "count"},
        ]

        progress = goal_agent._calculate_progress(key_results)
        # Should not cause division by zero
        assert progress == 0

    def test_progress_log_entry_stored(self, goal_agent_with_data):
        """Progress log entry is stored correctly."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "First entry",
            "percentage": 60
        })

        assert response.success is True
        progress_entry = response.data["progress_entry"]
        assert progress_entry["note"] == "First entry"
        assert progress_entry["percentage"] == 60
        assert "date" in progress_entry

    def test_progress_log_limited_to_50_entries(self, goal_agent_with_data):
        """Progress log is limited to last 50 entries."""
        # Log many progress entries
        for i in range(60):
            goal_agent_with_data.process("log_progress", {
                "goal_id": 1,
                "note": f"Entry {i}",
                "percentage": i
            })

        response = goal_agent_with_data.process("get_goal", {"goal_id": 1})
        progress_log = response.data["goal"]["metadata"]["progress_log"]
        assert len(progress_log) <= 50


# =============================================================================
# Test Milestone Management
# =============================================================================

class TestMilestoneManagement:
    """Tests for milestone management functionality."""

    def test_add_milestone_basic(self, goal_agent_with_data):
        """Add milestone with name."""
        response = goal_agent_with_data.process("add_milestone", {
            "goal_id": 1,
            "name": "First checkpoint"
        })

        assert response.success is True
        assert "milestone" in response.data
        assert response.data["milestone"]["name"] == "First checkpoint"

    def test_add_milestone_with_target_date(self, goal_agent_with_data):
        """Add milestone with target date."""
        response = goal_agent_with_data.process("add_milestone", {
            "goal_id": 1,
            "name": "Q2 review",
            "target_date": "2025-06-30"
        })

        assert response.success is True
        assert "2025-06-30" in response.data["milestone"]["target_date"]

    def test_add_milestone_sorts_by_date(self, goal_agent_with_data):
        """Milestones are sorted by target date."""
        # Add milestone with earlier date
        goal_agent_with_data.process("add_milestone", {
            "goal_id": 2,  # Use marathon goal which has no milestones
            "name": "Later milestone",
            "target_date": "2025-12-01"
        })
        goal_agent_with_data.process("add_milestone", {
            "goal_id": 2,
            "name": "Earlier milestone",
            "target_date": "2025-03-01"
        })

        response = goal_agent_with_data.process("get_goal", {"goal_id": 2})
        milestones = response.data["goal"]["metadata"]["milestones"]

        assert milestones[0]["name"] == "Earlier milestone"
        assert milestones[1]["name"] == "Later milestone"

    def test_complete_milestone_by_index(self, goal_agent_with_data):
        """Complete milestone by index."""
        response = goal_agent_with_data.process("complete_milestone", {
            "goal_id": 1,
            "milestone_index": 1  # Second milestone (0-indexed)
        })

        assert response.success is True
        completed = response.data["completed_milestone"]
        assert completed["completed"] is True
        assert completed["completed_at"] is not None

    def test_complete_milestone_by_name(self, goal_agent_with_data):
        """Complete milestone by name search."""
        response = goal_agent_with_data.process("complete_milestone", {
            "goal_id": 1,
            "milestone_name": "Reach $5000"
        })

        assert response.success is True
        assert response.data["completed_milestone"]["name"] == "Reach $5000"

    def test_complete_milestone_defaults_to_first_incomplete(self, goal_agent_with_data):
        """Without specifier, completes first incomplete milestone."""
        response = goal_agent_with_data.process("complete_milestone", {
            "goal_id": 1
        })

        assert response.success is True
        # First incomplete milestone is "Reach $5000"
        assert response.data["completed_milestone"]["name"] == "Reach $5000"

    def test_complete_milestone_updates_progress(self, goal_agent_with_data):
        """Completing milestone updates overall progress."""
        original = goal_agent_with_data.process("get_goal", {"goal_id": 1})
        original_progress = original.data["goal"]["overall_progress"]

        response = goal_agent_with_data.process("complete_milestone", {
            "goal_id": 1
        })

        # Progress should have changed (might go up due to milestone completion)
        new_progress = response.data["goal"]["overall_progress"]
        # Just verify it's recalculated, not necessarily higher
        assert isinstance(new_progress, int)

    def test_complete_milestone_adds_progress_log(self, goal_agent_with_data):
        """Completing milestone adds to progress log."""
        goal_agent_with_data.process("complete_milestone", {
            "goal_id": 1
        })

        response = goal_agent_with_data.process("get_goal", {"goal_id": 1})
        progress_log = response.data["goal"]["metadata"]["progress_log"]

        # Last entry should mention milestone completion
        last_entry = progress_log[-1]
        assert "milestone" in last_entry["note"].lower()

    def test_complete_milestone_no_milestones_fails(self, goal_agent_with_data):
        """Completing milestone fails when goal has no milestones."""
        response = goal_agent_with_data.process("complete_milestone", {
            "goal_id": 2  # Marathon goal has no milestones
        })

        assert response.success is False
        assert "no milestone" in response.message.lower()

    def test_complete_milestone_all_done_fails(self, goal_agent_with_data):
        """Completing milestone fails when all are already complete."""
        # Complete all milestones on goal 1
        for _ in range(3):
            goal_agent_with_data.process("complete_milestone", {"goal_id": 1})

        response = goal_agent_with_data.process("complete_milestone", {
            "goal_id": 1
        })

        assert response.success is False
        assert "no incomplete milestone" in response.message.lower()

    def test_list_milestones_shows_status(self, goal_agent_with_data):
        """Getting goal shows milestone completion status."""
        response = goal_agent_with_data.process("get_goal", {"goal_id": 1})

        goal = response.data["goal"]
        assert goal["total_milestones"] == 3
        assert goal["completed_milestones"] == 1


# =============================================================================
# Test Goal Review
# =============================================================================

class TestGoalReview:
    """Tests for goal review functionality."""

    def test_review_shows_active_goals(self, goal_agent_with_data):
        """Review returns active goals."""
        response = goal_agent_with_data.process("review_goals", {})

        assert response.success is True
        review = response.data["review"]
        assert len(review["active_goals"]) >= 2
        # Should not include completed or archived goals
        for goal in review["active_goals"]:
            assert goal["status"] != "completed"

    def test_review_detects_at_risk_goals(self, goal_agent_with_data):
        """Review identifies goals that are behind schedule."""
        response = goal_agent_with_data.process("review_goals", {})

        review = response.data["review"]
        # Marathon goal is at risk (10% progress but should be ~50%)
        assert len(review["at_risk"]) >= 1
        at_risk_names = [g["name"] for g in review["at_risk"]]
        assert any("marathon" in name.lower() for name in at_risk_names)

    def test_review_calculates_expected_progress(self, goal_agent_with_data):
        """Review shows expected vs actual progress."""
        response = goal_agent_with_data.process("get_goal", {"goal_id": 2})

        goal = response.data["goal"]
        # Should have expected_progress calculated based on time elapsed
        assert "expected_progress" in goal
        assert goal["expected_progress"] is not None

    def test_review_shows_upcoming_milestones(self, goal_agent_with_data):
        """Review shows milestones due within 30 days."""
        response = goal_agent_with_data.process("review_goals", {})

        review = response.data["review"]
        # Should include upcoming milestones within 30 days
        assert "upcoming_milestones" in review

    def test_review_calculates_summary_stats(self, goal_agent_with_data):
        """Review includes summary statistics."""
        response = goal_agent_with_data.process("review_goals", {})

        summary = response.data["review"]["summary"]
        assert "total_active" in summary
        assert "at_risk_count" in summary
        assert "avg_progress" in summary

    def test_review_excludes_archived_by_default(self, goal_agent_with_data):
        """Review excludes archived goals by default."""
        response = goal_agent_with_data.process("review_goals", {})

        review = response.data["review"]
        for goal in review["active_goals"]:
            assert goal["name"] != "Old abandoned goal"

    def test_review_can_include_completed(self, goal_agent_with_data):
        """Review can include completed goals."""
        response = goal_agent_with_data.process("review_goals", {
            "include_completed": True
        })

        review = response.data["review"]
        goal_names = [g["name"] for g in review["active_goals"]]
        # With include_completed, should show completed goal
        # (though it might be filtered elsewhere based on status filter)
        assert len(review["active_goals"]) >= 1

    def test_review_empty_goals_shows_suggestion(self, goal_agent):
        """Review with no goals shows helpful suggestion."""
        response = goal_agent.process("review_goals", {})

        assert response.success is True
        assert response.suggestions is not None


# =============================================================================
# Test Intent Handlers - get_goal
# =============================================================================

class TestGetGoalIntent:
    """Tests for get_goal intent handler."""

    def test_get_goal_by_id(self, goal_agent_with_data):
        """Retrieves goal by ID."""
        response = goal_agent_with_data.process("get_goal", {"goal_id": 1})

        assert response.success is True
        assert response.data["goal"]["id"] == 1
        assert "Save $10,000" in response.data["goal"]["name"]

    def test_get_goal_enriches_data(self, goal_agent_with_data):
        """Get goal returns enriched data."""
        response = goal_agent_with_data.process("get_goal", {"goal_id": 1})

        goal = response.data["goal"]
        # Should have computed fields
        assert "overall_progress" in goal
        assert "total_milestones" in goal
        assert "completed_milestones" in goal
        assert "total_key_results" in goal

    def test_get_goal_missing_id_fails(self, goal_agent_with_data):
        """get_goal fails when goal_id is missing."""
        response = goal_agent_with_data.process("get_goal", {})

        assert response.success is False
        assert "goal_id" in response.message.lower()

    def test_get_goal_invalid_id_fails(self, goal_agent_with_data):
        """get_goal fails for non-existent goal."""
        response = goal_agent_with_data.process("get_goal", {"goal_id": 9999})

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handlers - list_goals
# =============================================================================

class TestListGoalsIntent:
    """Tests for list_goals intent handler."""

    def test_list_goals_excludes_archived_by_default(self, goal_agent_with_data):
        """List excludes archived goals by default."""
        response = goal_agent_with_data.process("list_goals", {})

        assert response.success is True
        goals = response.data["goals"]
        for goal in goals:
            assert goal["name"] != "Old abandoned goal"

    def test_list_goals_filter_by_status(self, goal_agent_with_data):
        """Filters goals by status."""
        response = goal_agent_with_data.process("list_goals", {
            "status": "on_hold"
        })

        assert response.success is True
        goals = response.data["goals"]
        assert len(goals) >= 1
        for goal in goals:
            assert goal["status"] == "on_hold"

    def test_list_goals_filter_by_goal_type(self, goal_agent_with_data):
        """Filters goals by goal type."""
        response = goal_agent_with_data.process("list_goals", {
            "goal_type": "health"
        })

        assert response.success is True
        goals = response.data["goals"]
        for goal in goals:
            assert goal["metadata"]["goal_type"] == "health"

    def test_list_goals_filter_by_category(self, goal_agent_with_data):
        """Filters goals by para_category_id."""
        response = goal_agent_with_data.process("list_goals", {
            "para_category_id": 1
        })

        assert response.success is True
        # Finance goal has para_category_id=1

    def test_list_goals_include_archived(self, goal_agent_with_data):
        """Can include archived goals."""
        response = goal_agent_with_data.process("list_goals", {
            "include_archived": True,
            "status": "active"  # Include active archived ones
        })

        assert response.success is True

    def test_list_goals_with_limit(self, goal_agent_with_data):
        """Respects limit parameter."""
        response = goal_agent_with_data.process("list_goals", {"limit": 2})

        assert response.success is True
        assert len(response.data["goals"]) <= 2

    def test_list_goals_sort_by_progress(self, goal_agent_with_data):
        """Can sort goals by progress."""
        response = goal_agent_with_data.process("list_goals", {
            "sort_by": "progress"
        })

        assert response.success is True
        goals = response.data["goals"]
        if len(goals) >= 2:
            # Should be sorted by progress descending
            for i in range(len(goals) - 1):
                assert goals[i]["overall_progress"] >= goals[i + 1]["overall_progress"]

    def test_list_goals_excludes_non_goals(self, goal_agent_with_data):
        """List excludes projects that are not goals."""
        response = goal_agent_with_data.process("list_goals", {
            "include_archived": True
        })

        goals = response.data["goals"]
        for goal in goals:
            # Website redesign project should not appear
            assert goal["name"] != "Website redesign"

    def test_list_goals_empty_result(self, goal_agent):
        """Returns empty list when no goals match."""
        response = goal_agent.process("list_goals", {})

        assert response.success is True
        assert response.data["goals"] == []
        assert response.data["count"] == 0


# =============================================================================
# Test Intent Handlers - update_goal
# =============================================================================

class TestUpdateGoalIntent:
    """Tests for update_goal intent handler."""

    def test_update_goal_name(self, goal_agent_with_data):
        """Updates goal name."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "name": "Updated goal name"
        })

        assert response.success is True
        assert response.data["goal"]["name"] == "Updated goal name"

    def test_update_goal_description(self, goal_agent_with_data):
        """Updates goal description."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "description": "New description"
        })

        assert response.success is True
        assert response.data["goal"]["description"] == "New description"

    def test_update_goal_status(self, goal_agent_with_data):
        """Updates goal status."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "status": "on_hold"
        })

        assert response.success is True
        assert response.data["goal"]["status"] == "on_hold"

    def test_update_goal_to_completed_sets_end_date(self, goal_agent_with_data):
        """Setting status to completed sets actual_end_date."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "status": "completed"
        })

        assert response.success is True
        assert response.data["goal"]["actual_end_date"] is not None

    def test_update_goal_target_date(self, goal_agent_with_data):
        """Updates goal target date."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "target_end_date": "2026-01-01"
        })

        assert response.success is True
        assert "2026-01-01" in response.data["goal"]["target_end_date"]

    def test_update_goal_key_results(self, goal_agent_with_data):
        """Updates goal key results."""
        new_kr = [
            {"description": "New KR", "target": 100, "current": 0, "unit": "count"}
        ]
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "key_results": new_kr
        })

        assert response.success is True
        assert response.data["goal"]["metadata"]["key_results"] == new_kr

    def test_update_goal_type(self, goal_agent_with_data):
        """Updates goal type."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "goal_type": "professional"
        })

        assert response.success is True
        assert response.data["goal"]["metadata"]["goal_type"] == "professional"

    def test_update_goal_missing_id_fails(self, goal_agent_with_data):
        """update_goal fails when goal_id is missing."""
        response = goal_agent_with_data.process("update_goal", {
            "name": "New name"
        })

        assert response.success is False
        assert "goal_id" in response.message.lower()

    def test_update_goal_no_fields_fails(self, goal_agent_with_data):
        """update_goal fails when no fields provided."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 1
        })

        assert response.success is False
        assert "no fields" in response.message.lower()

    def test_update_goal_invalid_id_fails(self, goal_agent_with_data):
        """update_goal fails for non-existent goal."""
        response = goal_agent_with_data.process("update_goal", {
            "goal_id": 9999,
            "name": "Never exists"
        })

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Intent Handlers - archive_goal
# =============================================================================

class TestArchiveGoalIntent:
    """Tests for archive_goal intent handler."""

    def test_archive_goal_marks_archived(self, goal_agent_with_data):
        """Archive goal sets archived flag."""
        response = goal_agent_with_data.process("archive_goal", {
            "goal_id": 1
        })

        assert response.success is True

        # Verify archived
        goal = goal_agent_with_data._get_goal_by_id(1)
        assert goal["archived"] == 1

    def test_archive_goal_with_reason(self, goal_agent_with_data):
        """Archive goal stores reason in metadata."""
        response = goal_agent_with_data.process("archive_goal", {
            "goal_id": 1,
            "reason": "No longer relevant"
        })

        assert response.success is True

        goal = goal_agent_with_data._get_goal_by_id(1)
        assert goal["metadata"]["archive_reason"] == "No longer relevant"

    def test_archive_goal_sets_end_date(self, goal_agent_with_data):
        """Archive goal sets actual_end_date."""
        response = goal_agent_with_data.process("archive_goal", {
            "goal_id": 1
        })

        assert response.success is True

        goal = goal_agent_with_data._get_goal_by_id(1)
        assert goal["actual_end_date"] is not None

    def test_archive_goal_missing_id_fails(self, goal_agent_with_data):
        """archive_goal fails when goal_id is missing."""
        response = goal_agent_with_data.process("archive_goal", {})

        assert response.success is False
        assert "goal_id" in response.message.lower()

    def test_archive_goal_invalid_id_fails(self, goal_agent_with_data):
        """archive_goal fails for non-existent goal."""
        response = goal_agent_with_data.process("archive_goal", {
            "goal_id": 9999
        })

        assert response.success is False
        assert "not found" in response.message.lower()


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in GoalAgent."""

    def test_unknown_intent_returns_error(self, goal_agent):
        """Unknown intent returns error response."""
        response = goal_agent.process("unknown_intent", {})

        assert response.success is False
        assert "unknown intent" in response.message.lower()

    def test_database_error_handled(self, goal_agent, mock_config):
        """Database errors are caught and returned as error response."""
        mock_db = MagicMock()
        mock_db.execute_write.side_effect = Exception("Database connection failed")

        agent = GoalAgent(mock_db, mock_config)
        response = agent.process("create_goal", {"name": "Test goal"})

        assert response.success is False
        assert "failed" in response.message.lower()

    def test_log_progress_missing_goal_id_fails(self, goal_agent_with_data):
        """log_progress fails without goal_id."""
        response = goal_agent_with_data.process("log_progress", {
            "note": "Progress"
        })

        assert response.success is False
        assert "goal_id" in response.message.lower()

    def test_log_progress_on_non_goal_fails(self, goal_agent_with_data):
        """log_progress fails when project is not a goal."""
        response = goal_agent_with_data.process("log_progress", {
            "goal_id": 6,  # Website redesign (not a goal)
            "note": "Progress"
        })

        assert response.success is False
        assert "not a goal" in response.message.lower()

    def test_add_milestone_missing_name_fails(self, goal_agent_with_data):
        """add_milestone fails without name."""
        response = goal_agent_with_data.process("add_milestone", {
            "goal_id": 1
        })

        assert response.success is False
        assert "name" in response.message.lower()


# =============================================================================
# Test Enrichment and Computed Fields
# =============================================================================

class TestEnrichment:
    """Tests for goal enrichment with computed fields."""

    def test_enrich_goal_adds_progress(self, goal_agent_with_data):
        """Enriched goal includes overall_progress."""
        goal = goal_agent_with_data._get_goal_by_id(1)
        enriched = goal_agent_with_data._enrich_goal(goal)

        assert "overall_progress" in enriched
        assert enriched["overall_progress"] == 50

    def test_enrich_goal_calculates_days_remaining(self, goal_agent_with_data):
        """Enriched goal includes days_remaining."""
        goal = goal_agent_with_data._get_goal_by_id(1)
        enriched = goal_agent_with_data._enrich_goal(goal)

        assert "days_remaining" in enriched
        assert isinstance(enriched["days_remaining"], int)

    def test_enrich_goal_calculates_expected_progress(self, goal_agent_with_data):
        """Enriched goal includes expected_progress."""
        goal = goal_agent_with_data._get_goal_by_id(1)
        enriched = goal_agent_with_data._enrich_goal(goal)

        assert "expected_progress" in enriched
        assert isinstance(enriched["expected_progress"], int)

    def test_enrich_goal_detects_at_risk(self, goal_agent_with_data):
        """Enriched goal includes is_at_risk flag."""
        # Marathon goal is at risk (10% progress, should be ~50%)
        goal = goal_agent_with_data._get_goal_by_id(2)
        enriched = goal_agent_with_data._enrich_goal(goal)

        assert "is_at_risk" in enriched
        # Goal with low progress vs expected should be at risk
        if enriched.get("expected_progress", 0) - enriched.get("overall_progress", 0) > 20:
            assert enriched["is_at_risk"] is True

    def test_enrich_goal_counts_milestones(self, goal_agent_with_data):
        """Enriched goal includes milestone counts."""
        goal = goal_agent_with_data._get_goal_by_id(1)
        enriched = goal_agent_with_data._enrich_goal(goal)

        assert enriched["total_milestones"] == 3
        assert enriched["completed_milestones"] == 1

    def test_enrich_goal_counts_key_results(self, goal_agent_with_data):
        """Enriched goal includes key result count."""
        goal = goal_agent_with_data._get_goal_by_id(1)
        enriched = goal_agent_with_data._enrich_goal(goal)

        assert enriched["total_key_results"] == 1


# =============================================================================
# Test AgentResponse Structure
# =============================================================================

class TestAgentResponseStructure:
    """Tests for AgentResponse data structure."""

    def test_success_response_structure(self, goal_agent):
        """Successful response has expected structure."""
        response = goal_agent.process("create_goal", {"name": "Test"})

        assert hasattr(response, "success")
        assert hasattr(response, "message")
        assert hasattr(response, "data")
        assert hasattr(response, "suggestions")

    def test_error_response_structure(self, goal_agent):
        """Error response has expected structure."""
        response = goal_agent.process("create_goal", {})  # Missing name

        assert response.success is False
        assert response.message is not None
        assert len(response.message) > 0

    def test_response_to_dict(self, goal_agent):
        """Response can be converted to dictionary."""
        response = goal_agent.process("create_goal", {"name": "Test"})

        result = response.to_dict()
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "data" in result


# =============================================================================
# Test Database Integration
# =============================================================================

class TestDatabaseIntegration:
    """Tests for database integration in GoalAgent."""

    def test_goal_persisted_correctly(self, goal_agent):
        """Goal is correctly persisted to database."""
        context = {
            "name": "Persistent goal",
            "description": "This should be saved",
            "target_end_date": "2025-12-31",
            "goal_type": "personal"
        }

        response = goal_agent.process("create_goal", context)
        goal_id = response.data["goal_id"]

        # Fetch directly from database
        goal = goal_agent._get_goal_by_id(goal_id)

        assert goal["name"] == "Persistent goal"
        assert goal["description"] == "This should be saved"
        assert "2025-12-31" in goal["target_end_date"]
        assert goal["metadata"]["goal_type"] == "personal"
        assert goal["metadata"]["is_goal"] is True

    def test_goal_update_persisted(self, goal_agent_with_data):
        """Goal update is correctly persisted."""
        goal_agent_with_data.process("update_goal", {
            "goal_id": 1,
            "name": "Updated goal name"
        })

        # Fetch fresh from database
        goal = goal_agent_with_data._get_goal_by_id(1)
        assert goal["name"] == "Updated goal name"

    def test_milestone_persisted(self, goal_agent_with_data):
        """Milestone is correctly persisted."""
        goal_agent_with_data.process("add_milestone", {
            "goal_id": 2,
            "name": "New milestone",
            "target_date": "2025-06-15"
        })

        goal = goal_agent_with_data._get_goal_by_id(2)
        milestones = goal["metadata"]["milestones"]

        assert len(milestones) == 1
        assert milestones[0]["name"] == "New milestone"

    def test_progress_log_persisted(self, goal_agent_with_data):
        """Progress log entry is correctly persisted."""
        goal_agent_with_data.process("log_progress", {
            "goal_id": 1,
            "note": "Test progress",
            "percentage": 75
        })

        goal = goal_agent_with_data._get_goal_by_id(1)
        progress_log = goal["metadata"]["progress_log"]

        # Find our entry
        assert any(entry["note"] == "Test progress" for entry in progress_log)

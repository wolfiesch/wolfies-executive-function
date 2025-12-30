"""
Goal Agent for AI Life Planner
Manages goals using the projects table with goal-specific metadata.

Goals are essentially projects enhanced with:
- Measurable targets (OKR-style key results)
- Progress tracking with history
- Milestones with target dates
- Review reminders and at-risk detection

Design Decision: Goals are stored in the projects table rather than a separate table.
This allows goals to leverage the existing project infrastructure (tasks, PARA categories)
while adding goal-specific behavior through metadata and specialized agent logic.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from .base_agent import BaseAgent, AgentResponse
from ..core.models import Project


class GoalAgent(BaseAgent):
    """
    Specialized agent for goal management.

    Goals are stored in the projects table with goal-specific metadata in the
    'metadata' JSON field. This agent provides OKR-style goal tracking with
    measurable key results, milestones, and progress logging.

    Handles intents:
    - create_goal: Create a new goal with key results
    - get_goal: Retrieve goal details including progress
    - list_goals: List goals with filters (status, category, date range)
    - update_goal: Modify goal properties
    - log_progress: Record progress entry with notes
    - add_milestone: Add a milestone with target date
    - complete_milestone: Mark a milestone as done
    - review_goals: Generate goal review summary
    - archive_goal: Archive a completed or abandoned goal

    Metadata Structure:
        {
            "is_goal": true,
            "goal_type": "personal|professional|health|etc",
            "key_results": [
                {"description": "...", "target": 100, "current": 25, "unit": "..."}
            ],
            "milestones": [
                {"name": "...", "target_date": "YYYY-MM-DD", "completed": false, "completed_at": null}
            ],
            "progress_log": [
                {"date": "YYYY-MM-DD", "note": "...", "percentage": 25}
            ],
            "overall_progress": 25,
            "review_frequency": "weekly"
        }
    """

    # Supported intents for this agent
    INTENTS = [
        "create_goal",
        "get_goal",
        "list_goals",
        "update_goal",
        "log_progress",
        "add_milestone",
        "complete_milestone",
        "review_goals",
        "archive_goal",
    ]

    # Goal type keywords for NL parsing
    GOAL_TYPE_KEYWORDS = {
        "personal": ["personal", "self", "life", "lifestyle", "hobby"],
        "professional": ["work", "career", "job", "professional", "business"],
        "health": ["health", "fitness", "exercise", "weight", "diet", "gym", "run", "marathon"],
        "finance": ["save", "saving", "money", "financial", "invest", "budget", "debt"],
        "learning": ["learn", "study", "course", "skill", "read", "book", "education"],
        "relationships": ["family", "friend", "relationship", "social", "network"],
    }

    # Keywords that indicate measurable targets
    MEASURABLE_PATTERNS = [
        (r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', 'dollars'),  # $10,000
        (r'(\d+)\s*(?:kg|kilos?|pounds?|lbs?)', 'weight'),  # 10 kg, 20 pounds
        (r'(\d+)\s*(?:km|kilometers?|miles?)', 'distance'),  # 5km, 10 miles
        (r'(\d+)\s*(?:minutes?|mins?|hours?|hrs?)', 'time'),  # 30 minutes
        (r'(\d+)\s*(?:times?|sessions?)', 'frequency'),  # 3 times
        (r'(\d+)\s*(?:books?|articles?|courses?)', 'count'),  # 12 books
        (r'(\d+)%', 'percentage'),  # 100%
        (r'(\d+)\s*(?:days?|weeks?|months?)', 'duration'),  # 30 days
    ]

    def __init__(self, db, config):
        """Initialize the Goal Agent."""
        super().__init__(db, config, "goal")

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents."""
        return self.INTENTS

    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given intent."""
        return intent in self.INTENTS

    def process(self, intent: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process a goal-related intent.

        Routes to the appropriate handler based on intent type.

        Args:
            intent: One of the supported goal intents
            context: Request context with parameters

        Returns:
            AgentResponse with operation result
        """
        self.log_action(f"processing_{intent}", {"context_keys": list(context.keys())})

        handlers = {
            "create_goal": self._handle_create_goal,
            "get_goal": self._handle_get_goal,
            "list_goals": self._handle_list_goals,
            "update_goal": self._handle_update_goal,
            "log_progress": self._handle_log_progress,
            "add_milestone": self._handle_add_milestone,
            "complete_milestone": self._handle_complete_milestone,
            "review_goals": self._handle_review_goals,
            "archive_goal": self._handle_archive_goal,
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

    def _handle_create_goal(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Handle goal creation.

        Supports two modes:
        1. Structured: name, description, target_end_date provided directly
        2. Natural language: text field parsed for goal details

        Context params:
            text (str): Natural language goal description
            OR
            name (str): Goal name
            description (str, optional): Goal description
            target_end_date (str, optional): Target completion date
            para_category_id (int, optional): Life area category
            key_results (list, optional): List of key result objects
            goal_type (str, optional): Type of goal (personal, professional, etc.)
        """
        # Check if we have natural language input
        if "text" in context and context["text"]:
            parsed = self._parse_goal_from_text(context["text"])
            # Merge parsed values with any explicit overrides from context
            for key, value in parsed.items():
                if key not in context or context[key] is None:
                    context[key] = value

        # Validate required fields
        if not context.get("name"):
            return AgentResponse.error("Goal name is required")

        # Build goal metadata
        metadata = {
            "is_goal": True,
            "goal_type": context.get("goal_type", "personal"),
            "key_results": context.get("key_results", []),
            "milestones": context.get("milestones", []),
            "progress_log": [],
            "overall_progress": 0,
            "review_frequency": context.get("review_frequency", "weekly"),
        }

        # Build goal data (stored in projects table)
        goal_data = {
            "name": context["name"],
            "description": context.get("description"),
            "status": "active",
            "para_category_id": context.get("para_category_id"),
            "start_date": datetime.now(timezone.utc).date().isoformat(),
            "target_end_date": self._parse_date(context.get("target_end_date")),
            "metadata": json.dumps(metadata),
        }

        # Insert into database
        try:
            goal_id = self._insert_goal(goal_data)
            created_goal = self._get_goal_by_id(goal_id)

            return AgentResponse.ok(
                message=f"Goal created: '{goal_data['name']}'",
                data={
                    "goal_id": goal_id,
                    "goal": created_goal,
                },
                suggestions=[
                    f"Add a milestone: 'add milestone to goal {goal_id}'",
                    f"Log progress: 'log progress on goal {goal_id}'",
                    "Review all goals: 'show my goals'",
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to create goal: {e}")
            return AgentResponse.error(f"Failed to create goal: {str(e)}")

    def _handle_get_goal(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Get a single goal by ID with full details.

        Context params:
            goal_id (int): Goal ID to retrieve
        """
        validation = self.validate_required_params(context, ["goal_id"])
        if validation:
            return validation

        goal = self._get_goal_by_id(context["goal_id"])
        if goal:
            # Enhance with computed fields
            goal = self._enrich_goal(goal)
            return AgentResponse.ok(
                message=f"Goal: {goal['name']}",
                data={"goal": goal}
            )
        else:
            return AgentResponse.error(f"Goal {context['goal_id']} not found")

    def _handle_list_goals(self, context: Dict[str, Any]) -> AgentResponse:
        """
        List goals with optional filters.

        Context params:
            status (str or list): Filter by status (active, on_hold, completed)
            para_category_id (int): Filter by life area
            goal_type (str): Filter by goal type
            due_before (str): Goals due before date
            due_after (str): Goals due after date
            include_archived (bool): Include archived goals (default False)
            limit (int): Max goals to return (default 20)
            sort_by (str): Sort field (target_end_date, progress, created_at)
        """
        filters = {"is_goal": True}

        # Status filter
        if "status" in context:
            filters["status"] = context["status"]
        elif not context.get("include_archived", False):
            filters["exclude_archived"] = True

        # Other filters
        if "para_category_id" in context:
            filters["para_category_id"] = context["para_category_id"]
        if "goal_type" in context:
            filters["goal_type"] = context["goal_type"]
        if "due_before" in context:
            filters["due_before"] = self._parse_date(context["due_before"])
        if "due_after" in context:
            filters["due_after"] = self._parse_date(context["due_after"])

        limit = context.get("limit", 20)
        sort_by = context.get("sort_by", "target_end_date")

        goals = self._fetch_goals(filters, limit, sort_by)

        # Enrich each goal with computed fields
        goals = [self._enrich_goal(g) for g in goals]

        if not goals:
            return AgentResponse.ok(
                message="No goals found matching the criteria",
                data={"goals": [], "count": 0}
            )

        return AgentResponse.ok(
            message=f"Found {len(goals)} goal(s)",
            data={
                "goals": goals,
                "count": len(goals),
                "filters_applied": filters,
            }
        )

    def _handle_update_goal(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Update goal properties.

        Context params:
            goal_id (int): Goal to update
            name (str, optional): New name
            description (str, optional): New description
            status (str, optional): New status
            target_end_date (str, optional): New target date
            para_category_id (int, optional): New life area
            key_results (list, optional): Updated key results
            goal_type (str, optional): Updated goal type
        """
        validation = self.validate_required_params(context, ["goal_id"])
        if validation:
            return validation

        goal_id = context["goal_id"]

        # Get existing goal to merge metadata
        existing_goal = self._get_goal_by_id(goal_id)
        if not existing_goal:
            return AgentResponse.error(f"Goal {goal_id} not found")

        # Build update fields
        update_fields = {}
        if "name" in context:
            update_fields["name"] = context["name"]
        if "description" in context:
            update_fields["description"] = context["description"]
        if "status" in context:
            update_fields["status"] = context["status"]
            # If completing, set actual_end_date
            if context["status"] == "completed":
                update_fields["actual_end_date"] = datetime.now(timezone.utc).date().isoformat()
        if "target_end_date" in context:
            update_fields["target_end_date"] = self._parse_date(context["target_end_date"])
        if "para_category_id" in context:
            update_fields["para_category_id"] = context["para_category_id"]

        # Handle metadata updates
        existing_metadata = existing_goal.get("metadata", {}) or {}
        metadata_updated = False

        if "key_results" in context:
            existing_metadata["key_results"] = context["key_results"]
            metadata_updated = True
        if "goal_type" in context:
            existing_metadata["goal_type"] = context["goal_type"]
            metadata_updated = True
        if "review_frequency" in context:
            existing_metadata["review_frequency"] = context["review_frequency"]
            metadata_updated = True

        if metadata_updated:
            update_fields["metadata"] = json.dumps(existing_metadata)

        if not update_fields:
            return AgentResponse.error("No fields to update provided")

        try:
            success = self._update_goal(goal_id, update_fields)
            if success:
                updated_goal = self._get_goal_by_id(goal_id)
                updated_goal = self._enrich_goal(updated_goal)
                return AgentResponse.ok(
                    message=f"Goal {goal_id} updated",
                    data={"goal": updated_goal}
                )
            else:
                return AgentResponse.error(f"Goal {goal_id} not found")
        except Exception as e:
            return AgentResponse.error(f"Failed to update goal: {str(e)}")

    def _handle_log_progress(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Record progress on a goal.

        Context params:
            goal_id (int): Goal to log progress for
            note (str): Description of progress made
            percentage (int, optional): Overall progress percentage (0-100)
            key_result_updates (list, optional): Updates to specific key results
                [{"index": 0, "current": 50}, ...]
        """
        validation = self.validate_required_params(context, ["goal_id"])
        if validation:
            return validation

        goal_id = context["goal_id"]
        note = context.get("note", "Progress logged")

        # Get existing goal
        goal = self._get_goal_by_id(goal_id)
        if not goal:
            return AgentResponse.error(f"Goal {goal_id} not found")

        metadata = goal.get("metadata", {}) or {}
        if not metadata.get("is_goal"):
            return AgentResponse.error(f"Project {goal_id} is not a goal")

        # Create progress entry
        progress_entry = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "note": note,
        }

        # Update key results if provided
        if "key_result_updates" in context:
            key_results = metadata.get("key_results", [])
            for update in context["key_result_updates"]:
                idx = update.get("index")
                if idx is not None and 0 <= idx < len(key_results):
                    if "current" in update:
                        key_results[idx]["current"] = update["current"]
            metadata["key_results"] = key_results

        # Calculate overall progress
        if "percentage" in context:
            overall_progress = min(100, max(0, context["percentage"]))
        else:
            # Auto-calculate from key results
            overall_progress = self._calculate_progress(metadata.get("key_results", []))

        progress_entry["percentage"] = overall_progress
        metadata["overall_progress"] = overall_progress

        # Append to progress log (keep last 50 entries)
        progress_log = metadata.get("progress_log", [])
        progress_log.append(progress_entry)
        if len(progress_log) > 50:
            progress_log = progress_log[-50:]
        metadata["progress_log"] = progress_log

        # Save updated metadata
        try:
            self._update_goal(goal_id, {"metadata": json.dumps(metadata)})
            updated_goal = self._get_goal_by_id(goal_id)
            updated_goal = self._enrich_goal(updated_goal)

            return AgentResponse.ok(
                message=f"Progress logged for '{goal['name']}': {overall_progress}%",
                data={
                    "goal": updated_goal,
                    "progress_entry": progress_entry,
                },
                suggestions=[
                    f"View goal details: 'show goal {goal_id}'",
                    "Review all goals: 'review my goals'",
                ]
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to log progress: {str(e)}")

    def _handle_add_milestone(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Add a milestone to a goal.

        Context params:
            goal_id (int): Goal to add milestone to
            name (str): Milestone name
            target_date (str): Target completion date
        """
        validation = self.validate_required_params(context, ["goal_id", "name"])
        if validation:
            return validation

        goal_id = context["goal_id"]

        # Get existing goal
        goal = self._get_goal_by_id(goal_id)
        if not goal:
            return AgentResponse.error(f"Goal {goal_id} not found")

        metadata = goal.get("metadata", {}) or {}
        if not metadata.get("is_goal"):
            return AgentResponse.error(f"Project {goal_id} is not a goal")

        # Create milestone
        milestone = {
            "name": context["name"],
            "target_date": self._parse_date(context.get("target_date")),
            "completed": False,
            "completed_at": None,
        }

        # Add to milestones list
        milestones = metadata.get("milestones", [])
        milestones.append(milestone)
        # Sort milestones by target date
        milestones.sort(key=lambda m: m.get("target_date") or "9999-12-31")
        metadata["milestones"] = milestones

        # Save updated metadata
        try:
            self._update_goal(goal_id, {"metadata": json.dumps(metadata)})
            updated_goal = self._get_goal_by_id(goal_id)
            updated_goal = self._enrich_goal(updated_goal)

            return AgentResponse.ok(
                message=f"Milestone added to '{goal['name']}': {milestone['name']}",
                data={
                    "goal": updated_goal,
                    "milestone": milestone,
                },
                suggestions=[
                    f"Complete milestone: 'complete milestone on goal {goal_id}'",
                    f"Log progress: 'log progress on goal {goal_id}'",
                ]
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to add milestone: {str(e)}")

    def _handle_complete_milestone(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Mark a milestone as completed.

        Context params:
            goal_id (int): Goal containing the milestone
            milestone_index (int, optional): Index of milestone to complete
            milestone_name (str, optional): Name of milestone to complete
        """
        validation = self.validate_required_params(context, ["goal_id"])
        if validation:
            return validation

        goal_id = context["goal_id"]

        # Get existing goal
        goal = self._get_goal_by_id(goal_id)
        if not goal:
            return AgentResponse.error(f"Goal {goal_id} not found")

        metadata = goal.get("metadata", {}) or {}
        milestones = metadata.get("milestones", [])

        if not milestones:
            return AgentResponse.error(f"Goal {goal_id} has no milestones")

        # Find the milestone to complete
        milestone_idx = None
        if "milestone_index" in context:
            milestone_idx = context["milestone_index"]
        elif "milestone_name" in context:
            name_lower = context["milestone_name"].lower()
            for idx, m in enumerate(milestones):
                if name_lower in m.get("name", "").lower():
                    milestone_idx = idx
                    break

        # Default to first incomplete milestone
        if milestone_idx is None:
            for idx, m in enumerate(milestones):
                if not m.get("completed"):
                    milestone_idx = idx
                    break

        if milestone_idx is None or milestone_idx >= len(milestones):
            return AgentResponse.error("No incomplete milestone found")

        # Mark as completed
        milestones[milestone_idx]["completed"] = True
        milestones[milestone_idx]["completed_at"] = datetime.now(timezone.utc).isoformat()
        metadata["milestones"] = milestones

        # Auto-update progress based on milestone completion
        completed_count = sum(1 for m in milestones if m.get("completed"))
        milestone_progress = int((completed_count / len(milestones)) * 100)

        # Blend milestone progress with key result progress
        kr_progress = self._calculate_progress(metadata.get("key_results", []))
        if kr_progress > 0:
            overall_progress = int((milestone_progress + kr_progress) / 2)
        else:
            overall_progress = milestone_progress

        metadata["overall_progress"] = overall_progress

        # Add to progress log
        progress_log = metadata.get("progress_log", [])
        progress_log.append({
            "date": datetime.now(timezone.utc).date().isoformat(),
            "note": f"Completed milestone: {milestones[milestone_idx]['name']}",
            "percentage": overall_progress,
        })
        metadata["progress_log"] = progress_log

        # Save updated metadata
        try:
            self._update_goal(goal_id, {"metadata": json.dumps(metadata)})
            updated_goal = self._get_goal_by_id(goal_id)
            updated_goal = self._enrich_goal(updated_goal)

            completed_milestone = milestones[milestone_idx]
            return AgentResponse.ok(
                message=f"Milestone completed: '{completed_milestone['name']}' ({overall_progress}% overall)",
                data={
                    "goal": updated_goal,
                    "completed_milestone": completed_milestone,
                }
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to complete milestone: {str(e)}")

    def _handle_review_goals(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Generate a goal review summary.

        Context params:
            para_category_id (int, optional): Filter by life area
            include_completed (bool): Include completed goals (default False)

        Returns:
            Summary with:
            - Active goals with progress
            - Upcoming milestones
            - Goals at risk (behind schedule)
            - Recent progress
        """
        filters = {"is_goal": True}

        if "para_category_id" in context:
            filters["para_category_id"] = context["para_category_id"]

        if not context.get("include_completed", False):
            filters["exclude_archived"] = True
            filters["status"] = ["active", "on_hold"]

        # Fetch all matching goals
        goals = self._fetch_goals(filters, limit=100, sort_by="target_end_date")
        goals = [self._enrich_goal(g) for g in goals]

        if not goals:
            return AgentResponse.ok(
                message="No active goals found",
                data={"review": {"active_goals": [], "at_risk": [], "upcoming_milestones": []}},
                suggestions=["Create a goal: 'I want to [your goal]'"]
            )

        # Categorize goals
        today = datetime.now(timezone.utc).date()
        active_goals = []
        at_risk_goals = []
        upcoming_milestones = []

        for goal in goals:
            active_goals.append({
                "id": goal["id"],
                "name": goal["name"],
                "progress": goal.get("overall_progress", 0),
                "target_date": goal.get("target_end_date"),
                "status": goal.get("status"),
            })

            # Check if at risk (behind schedule)
            if goal.get("is_at_risk"):
                at_risk_goals.append({
                    "id": goal["id"],
                    "name": goal["name"],
                    "progress": goal.get("overall_progress", 0),
                    "target_date": goal.get("target_end_date"),
                    "expected_progress": goal.get("expected_progress", 0),
                })

            # Collect upcoming milestones
            metadata = goal.get("metadata", {}) or {}
            for milestone in metadata.get("milestones", []):
                if not milestone.get("completed") and milestone.get("target_date"):
                    target = milestone["target_date"]
                    if isinstance(target, str):
                        try:
                            target_date = datetime.fromisoformat(target).date()
                        except ValueError:
                            continue
                    else:
                        target_date = target

                    days_until = (target_date - today).days
                    if days_until <= 30:  # Within next 30 days
                        upcoming_milestones.append({
                            "goal_id": goal["id"],
                            "goal_name": goal["name"],
                            "milestone_name": milestone["name"],
                            "target_date": milestone["target_date"],
                            "days_until": days_until,
                        })

        # Sort upcoming milestones by date
        upcoming_milestones.sort(key=lambda m: m["days_until"])

        review = {
            "active_goals": active_goals,
            "at_risk": at_risk_goals,
            "upcoming_milestones": upcoming_milestones[:10],  # Top 10
            "summary": {
                "total_active": len(active_goals),
                "at_risk_count": len(at_risk_goals),
                "avg_progress": int(sum(g.get("progress", 0) for g in active_goals) / len(active_goals)) if active_goals else 0,
            }
        }

        return AgentResponse.ok(
            message=f"Goal Review: {len(active_goals)} active goals, {len(at_risk_goals)} at risk",
            data={"review": review},
            suggestions=[
                "Show goal details: 'show goal [id]'",
                "Log progress: 'log progress on goal [id]'",
            ]
        )

    def _handle_archive_goal(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Archive a completed or abandoned goal.

        Context params:
            goal_id (int): Goal to archive
            reason (str, optional): Reason for archiving
        """
        validation = self.validate_required_params(context, ["goal_id"])
        if validation:
            return validation

        goal_id = context["goal_id"]

        # Get existing goal
        goal = self._get_goal_by_id(goal_id)
        if not goal:
            return AgentResponse.error(f"Goal {goal_id} not found")

        # Update metadata with archive reason
        metadata = goal.get("metadata", {}) or {}
        if context.get("reason"):
            metadata["archive_reason"] = context["reason"]
        metadata["archived_at"] = datetime.now(timezone.utc).isoformat()

        # Archive the goal
        try:
            self._update_goal(goal_id, {
                "archived": 1,
                "status": "completed" if goal.get("status") == "active" else goal.get("status"),
                "actual_end_date": datetime.now(timezone.utc).date().isoformat(),
                "metadata": json.dumps(metadata),
            })

            return AgentResponse.ok(
                message=f"Goal archived: '{goal['name']}'",
                data={"goal_id": goal_id},
                suggestions=["Review active goals: 'show my goals'"]
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to archive goal: {str(e)}")

    # =========================================================================
    # Natural Language Parsing
    # =========================================================================

    def _parse_goal_from_text(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text to extract goal properties.

        Extracts:
        - Name (main goal description)
        - Target date (from relative/absolute dates)
        - Goal type (from keywords)
        - Measurable targets (from numbers and units)

        Examples:
        - "Goal: Run a marathon by June" -> name, target_date
        - "I want to save $10,000 this year" -> name, key_results
        - "Learn Spanish in 6 months" -> name, target_date

        Args:
            text: Natural language goal description

        Returns:
            Dictionary with parsed goal properties
        """
        result = {
            "name": text,
            "description": None,
            "target_end_date": None,
            "goal_type": "personal",
            "key_results": [],
        }

        working_text = text.lower()

        # Remove common prefixes
        prefixes = [
            r'^goal:\s*',
            r'^i want to\s*',
            r'^i\'d like to\s*',
            r'^my goal is to\s*',
            r'^i\'m going to\s*',
        ]
        for prefix in prefixes:
            result["name"] = re.sub(prefix, '', result["name"], flags=re.IGNORECASE).strip()

        # Detect goal type from keywords
        for goal_type, keywords in self.GOAL_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in working_text:
                    result["goal_type"] = goal_type
                    break

        # Extract target date
        target_date, cleaned_text = self._extract_target_date(result["name"])
        if target_date:
            result["target_end_date"] = target_date
            result["name"] = cleaned_text

        # Extract measurable targets as key results
        for pattern, unit_type in self.MEASURABLE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(",", "")
                try:
                    value = float(value_str)
                    # Create a key result from the measurable target
                    result["key_results"].append({
                        "description": f"Achieve target",
                        "target": value,
                        "current": 0,
                        "unit": unit_type,
                    })
                except ValueError:
                    continue

        # Clean up the name
        result["name"] = re.sub(r'\s+', ' ', result["name"]).strip()

        # If name is too long, truncate and move rest to description
        if len(result["name"]) > 100:
            result["description"] = result["name"]
            result["name"] = result["name"][:97] + "..."

        return result

    def _extract_target_date(self, text: str) -> Tuple[Optional[str], str]:
        """
        Extract target date from text and return cleaned text.

        Handles patterns like:
        - "by June", "by June 2025"
        - "in 6 months", "in 30 days"
        - "this year", "next year"
        - "by end of year"

        Args:
            text: Text that may contain date references

        Returns:
            Tuple of (ISO date string or None, cleaned text)
        """
        text_lower = text.lower()
        today = datetime.now(timezone.utc).date()

        # Check for "by [month]" or "by [month] [year]"
        month_names = ["january", "february", "march", "april", "may", "june",
                       "july", "august", "september", "october", "november", "december"]

        for idx, month in enumerate(month_names):
            # "by June 2025" pattern
            pattern = rf'\bby\s+{month}\s+(\d{{4}})\b'
            match = re.search(pattern, text_lower)
            if match:
                year = int(match.group(1))
                target_date = datetime(year, idx + 1, 28).date()  # End of month approximation
                cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                return target_date.isoformat(), cleaned

            # "by June" pattern (assumes current or next year)
            pattern = rf'\bby\s+{month}\b'
            if re.search(pattern, text_lower):
                year = today.year
                if idx + 1 < today.month:
                    year += 1  # Next year if month has passed
                target_date = datetime(year, idx + 1, 28).date()
                cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                return target_date.isoformat(), cleaned

        # "in X months/weeks/days/years"
        time_patterns = [
            (r'\bin\s+(\d+)\s+years?\b', lambda n: today.replace(year=today.year + n)),
            (r'\bin\s+(\d+)\s+months?\b', lambda n: today + timedelta(days=n * 30)),
            (r'\bin\s+(\d+)\s+weeks?\b', lambda n: today + timedelta(weeks=n)),
            (r'\bin\s+(\d+)\s+days?\b', lambda n: today + timedelta(days=n)),
        ]

        for pattern, date_fn in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                num = int(match.group(1))
                try:
                    target_date = date_fn(num)
                    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                    return target_date.isoformat(), cleaned
                except ValueError:
                    continue

        # "this year" / "end of year"
        if re.search(r'\b(this year|end of year|by year end)\b', text_lower):
            target_date = datetime(today.year, 12, 31).date()
            cleaned = re.sub(r'\b(this year|end of year|by year end)\b', '', text, flags=re.IGNORECASE).strip()
            return target_date.isoformat(), cleaned

        # "next year"
        if re.search(r'\bnext year\b', text_lower):
            target_date = datetime(today.year + 1, 12, 31).date()
            cleaned = re.sub(r'\bnext year\b', '', text, flags=re.IGNORECASE).strip()
            return target_date.isoformat(), cleaned

        return None, text

    def _parse_date(self, date_input: Any) -> Optional[str]:
        """
        Parse and normalize date input.

        Args:
            date_input: String date, datetime, or None

        Returns:
            ISO format date string or None
        """
        if date_input is None:
            return None
        if isinstance(date_input, datetime):
            return date_input.date().isoformat()
        if isinstance(date_input, str):
            # Already ISO format
            if len(date_input) >= 10 and date_input[4] == '-':
                return date_input[:10]
            # Try parsing
            extracted, _ = self._extract_target_date(date_input)
            return extracted
        return None

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _calculate_progress(self, key_results: List[Dict[str, Any]]) -> int:
        """
        Calculate overall progress from key results.

        Each key result contributes equally. Progress for each is
        (current / target) * 100, capped at 100%.

        Args:
            key_results: List of key result dictionaries

        Returns:
            Overall progress percentage (0-100)
        """
        if not key_results:
            return 0

        total_progress = 0
        for kr in key_results:
            target = kr.get("target", 0)
            current = kr.get("current", 0)
            if target > 0:
                kr_progress = min(100, (current / target) * 100)
                total_progress += kr_progress

        return int(total_progress / len(key_results))

    def _enrich_goal(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add computed fields to a goal dictionary.

        Adds:
        - overall_progress (from metadata or calculated)
        - is_at_risk (behind expected progress based on time elapsed)
        - expected_progress (based on elapsed time)
        - days_remaining (until target date)
        - completed_milestones / total_milestones

        Args:
            goal: Goal dictionary from database

        Returns:
            Enriched goal dictionary
        """
        metadata = goal.get("metadata", {}) or {}

        # Extract progress
        goal["overall_progress"] = metadata.get("overall_progress", 0)

        # Calculate expected progress and at-risk status
        today = datetime.now(timezone.utc).date()
        start_date = goal.get("start_date")
        target_date = goal.get("target_end_date")

        if start_date and target_date:
            try:
                if isinstance(start_date, str):
                    start = datetime.fromisoformat(start_date).date()
                else:
                    start = start_date

                if isinstance(target_date, str):
                    target = datetime.fromisoformat(target_date).date()
                else:
                    target = target_date

                total_days = (target - start).days
                elapsed_days = (today - start).days

                if total_days > 0:
                    expected_progress = min(100, int((elapsed_days / total_days) * 100))
                    goal["expected_progress"] = expected_progress
                    goal["days_remaining"] = (target - today).days

                    # At risk if actual progress is significantly behind expected
                    if expected_progress > 0:
                        progress_gap = expected_progress - goal["overall_progress"]
                        goal["is_at_risk"] = progress_gap > 20  # More than 20% behind
                    else:
                        goal["is_at_risk"] = False
                else:
                    goal["expected_progress"] = 100
                    goal["days_remaining"] = 0
                    goal["is_at_risk"] = goal["overall_progress"] < 100

            except (ValueError, TypeError):
                goal["expected_progress"] = None
                goal["days_remaining"] = None
                goal["is_at_risk"] = False
        else:
            goal["expected_progress"] = None
            goal["days_remaining"] = None
            goal["is_at_risk"] = False

        # Milestone counts
        milestones = metadata.get("milestones", [])
        goal["total_milestones"] = len(milestones)
        goal["completed_milestones"] = sum(1 for m in milestones if m.get("completed"))

        # Key result counts
        key_results = metadata.get("key_results", [])
        goal["total_key_results"] = len(key_results)

        return goal

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _insert_goal(self, goal_data: Dict[str, Any]) -> int:
        """Insert a new goal (as project) and return its ID."""
        query = """
            INSERT INTO projects (
                name, description, status, para_category_id,
                start_date, target_end_date, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            goal_data["name"],
            goal_data.get("description"),
            goal_data.get("status", "active"),
            goal_data.get("para_category_id"),
            goal_data.get("start_date"),
            goal_data.get("target_end_date"),
            goal_data.get("metadata"),
        )
        return self.db.execute_write(query, params)

    def _get_goal_by_id(self, goal_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single goal by ID."""
        query = "SELECT * FROM projects WHERE id = ?"
        row = self.db.execute_one(query, (goal_id,))
        result = self.db.row_to_dict(row)

        if result:
            # Parse metadata JSON
            if result.get("metadata"):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except (json.JSONDecodeError, TypeError):
                    result["metadata"] = {}

        return result

    def _update_goal(self, goal_id: int, fields: Dict[str, Any]) -> bool:
        """Update specified goal fields."""
        if not fields:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        query = f"UPDATE projects SET {set_clause} WHERE id = ?"
        params = tuple(fields.values()) + (goal_id,)

        result = self.db.execute_write(query, params)
        return result > 0

    def _fetch_goals(self, filters: Dict[str, Any], limit: int = 20,
                     sort_by: str = "target_end_date") -> List[Dict[str, Any]]:
        """
        Fetch goals (projects with is_goal metadata) with filters.

        Args:
            filters: Dictionary of filter conditions
            limit: Maximum number of results
            sort_by: Sort field (target_end_date, created_at)

        Returns:
            List of goal dictionaries
        """
        conditions = []
        params = []

        # Filter for goals only (metadata contains is_goal: true)
        if filters.get("is_goal"):
            conditions.append("json_extract(metadata, '$.is_goal') = 1")

        # Status filter
        if "status" in filters:
            if isinstance(filters["status"], list):
                placeholders = ",".join("?" * len(filters["status"]))
                conditions.append(f"status IN ({placeholders})")
                params.extend(filters["status"])
            else:
                conditions.append("status = ?")
                params.append(filters["status"])

        # Exclude archived
        if filters.get("exclude_archived"):
            conditions.append("(archived = 0 OR archived IS NULL)")

        # Category filter
        if "para_category_id" in filters:
            conditions.append("para_category_id = ?")
            params.append(filters["para_category_id"])

        # Goal type filter (from metadata)
        if "goal_type" in filters:
            conditions.append("json_extract(metadata, '$.goal_type') = ?")
            params.append(filters["goal_type"])

        # Date filters
        if "due_before" in filters:
            conditions.append("target_end_date <= ?")
            params.append(filters["due_before"])

        if "due_after" in filters:
            conditions.append("target_end_date >= ?")
            params.append(filters["due_after"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Sort order
        if sort_by == "progress":
            order_clause = "json_extract(metadata, '$.overall_progress') DESC"
        elif sort_by == "created_at":
            order_clause = "created_at DESC"
        else:
            order_clause = """
                CASE WHEN target_end_date IS NULL THEN 1 ELSE 0 END,
                target_end_date ASC
            """

        query = f"""
            SELECT * FROM projects
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT ?
        """
        params.append(limit)

        rows = self.db.execute(query, tuple(params))
        results = self.db.rows_to_dicts(rows)

        # Parse metadata JSON for each result
        for result in results:
            if result.get("metadata"):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except (json.JSONDecodeError, TypeError):
                    result["metadata"] = {}

        return results
